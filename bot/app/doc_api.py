from __future__ import annotations

import asyncio
import logging
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from email.message import Message
from pathlib import PurePath
from time import monotonic
from typing import Any, Self
from uuid import UUID

import httpx

from app.config import DOCX_MEDIA_TYPE

logger = logging.getLogger(__name__)

_TRANSIENT_STATUSES = {408, 425, 429, 500, 502, 503, 504}
_SAFE_CONNECT_ERRORS = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.PoolTimeout,
)


class DocumentApiError(RuntimeError):
    """Base error for the document service boundary."""

    def __init__(self, message: str, *, public_message: str) -> None:
        super().__init__(message)
        self.public_message = public_message


class DocumentApiUnavailable(DocumentApiError):
    """The document service could not be reached or returned an HTTP error."""


class DocumentApiContractError(DocumentApiError):
    """The document service returned data outside its fixed contract."""


class DocumentRejected(DocumentApiError):
    """The document service rejected user input."""


class DocumentProcessingFailed(DocumentApiError):
    """Document processing reached the failed terminal state."""


class DocumentProcessingTimeout(DocumentApiError):
    """Document processing did not finish before the configured deadline."""


@dataclass(frozen=True, slots=True)
class RequisiteSpec:
    key: str
    label: str
    required: bool


@dataclass(frozen=True, slots=True)
class DocumentType:
    id: str
    name: str
    description: str
    requisites: tuple[RequisiteSpec, ...]


@dataclass(frozen=True, slots=True)
class Template:
    id: str
    name: str
    description: str


@dataclass(frozen=True, slots=True)
class Requisite:
    key: str
    label: str
    value: str | None
    status: str


@dataclass(frozen=True, slots=True)
class DocumentSnapshot:
    id: str
    status: str
    stage: str | None
    requisites: tuple[Requisite, ...]
    is_fallback: bool


@dataclass(frozen=True, slots=True)
class RenderedDocument:
    content: bytes
    filename: str
    media_type: str


class DocumentApiClient:
    """Typed, resilient adapter for the existing document HTTP API."""

    def __init__(
        self,
        base_url: str,
        *,
        request_timeout_seconds: float = 15.0,
        poll_interval_seconds: float = 1.5,
        processing_timeout_seconds: float = 120.0,
        max_attempts: int = 4,
        retry_backoff_seconds: float = 0.5,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._request_timeout = request_timeout_seconds
        self._poll_interval = poll_interval_seconds
        self._processing_timeout = processing_timeout_seconds
        self._max_attempts = max_attempts
        self._retry_backoff = retry_backoff_seconds
        self._client = client or httpx.AsyncClient()
        self._owns_client = client is None

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_args: object) -> None:
        await self.close()

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def get_document_types(self) -> tuple[DocumentType, ...]:
        response = await self._request("GET", "/api/doc-types", expected={200})
        payload = self._response_json(response, "GET /api/doc-types")
        if not isinstance(payload, list):
            raise self._contract_error("doc-types response is not a list")

        result: list[DocumentType] = []
        seen_ids: set[str] = set()
        for index, item in enumerate(payload):
            try:
                parsed = self._parse_document_type(item)
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning(
                    "Ignoring malformed doc type at index %s: %s", index, exc
                )
                continue
            if parsed.id in seen_ids:
                logger.warning("Ignoring duplicate document type id %s", parsed.id)
                continue
            seen_ids.add(parsed.id)
            result.append(parsed)

        if not result:
            raise self._contract_error("doc-types response has no valid entries")
        return tuple(result)

    async def get_templates(self) -> tuple[Template, ...]:
        response = await self._request("GET", "/api/templates", expected={200})
        payload = self._response_json(response, "GET /api/templates")
        if not isinstance(payload, Mapping) or not isinstance(
            payload.get("templates"), list
        ):
            raise self._contract_error("templates response has invalid shape")

        result: list[Template] = []
        seen_ids: set[str] = set()
        for index, item in enumerate(payload["templates"]):
            if not isinstance(item, Mapping) or item.get("available") is not True:
                continue
            try:
                template_id = _required_string(item, "id")
                name = _required_string(item, "name")
                description = _optional_string(item.get("description"))
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning(
                    "Ignoring malformed template at index %s: %s", index, exc
                )
                continue
            if template_id in seen_ids:
                logger.warning("Ignoring duplicate template id %s", template_id)
                continue
            seen_ids.add(template_id)
            result.append(Template(id=template_id, name=name, description=description))

        if not result:
            raise self._contract_error("templates response has no available entries")
        return tuple(result)

    async def create_document(
        self,
        *,
        draft: str,
        doc_type: str,
        template_id: str,
    ) -> str:
        response = await self._request(
            "POST",
            "/api/documents",
            expected={202},
            json_body={
                "draft": draft,
                "doc_type": doc_type,
                "template_id": template_id,
            },
            retry_ambiguous_errors=False,
        )
        payload = self._response_json(response, "POST /api/documents")
        if not isinstance(payload, Mapping):
            raise self._contract_error("create response is not an object")
        document_id = _required_string(payload, "id")
        try:
            UUID(document_id)
        except ValueError as exc:
            raise self._contract_error("create response contains invalid UUID") from exc
        return document_id

    async def get_document(self, document_id: str) -> DocumentSnapshot:
        response = await self._request(
            "GET",
            f"/api/documents/{document_id}",
            expected={200},
        )
        payload = self._response_json(response, "GET /api/documents/{id}")
        if not isinstance(payload, Mapping):
            raise self._contract_error("document response is not an object")

        returned_id = _required_string(payload, "id")
        if returned_id != document_id:
            raise self._contract_error("document response id does not match request")

        requisites_payload = payload.get("requisites", [])
        if not isinstance(requisites_payload, list):
            raise self._contract_error("document requisites are not a list")

        requisites: list[Requisite] = []
        for index, item in enumerate(requisites_payload):
            try:
                requisites.append(self._parse_requisite(item))
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning(
                    "Ignoring malformed requisite at index %s: %s", index, exc
                )

        stage_value = payload.get("stage")
        if stage_value is not None and not isinstance(stage_value, str):
            raise self._contract_error("document stage is not a string or null")

        return DocumentSnapshot(
            id=returned_id,
            status=_required_string(payload, "status"),
            stage=stage_value,
            requisites=tuple(requisites),
            is_fallback=payload.get("is_fallback") is True,
        )

    async def poll_until_done(self, document_id: str) -> DocumentSnapshot:
        deadline = monotonic() + self._processing_timeout
        while True:
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise _processing_timeout(document_id)
            try:
                async with asyncio.timeout(remaining):
                    snapshot = await self.get_document(document_id)
            except TimeoutError as exc:
                raise _processing_timeout(document_id) from exc
            if snapshot.status in {"processed", "degraded"}:
                return snapshot
            if snapshot.status == "failed":
                raise DocumentProcessingFailed(
                    f"Document {document_id} failed during processing",
                    public_message=(
                        "Не удалось обработать документ. "
                        "Проверьте черновик и попробуйте ещё раз."
                    ),
                )
            if snapshot.status != "processing":
                raise self._contract_error(
                    f"unknown document status: {snapshot.status}"
                )

            remaining = deadline - monotonic()
            await asyncio.sleep(min(self._poll_interval, max(0.0, remaining)))

    async def render_document(self, document_id: str) -> RenderedDocument:
        response = await self._request(
            "POST",
            f"/api/documents/{document_id}/render",
            expected={200},
            retry_ambiguous_errors=True,
        )
        content = response.content
        if not content or not content.startswith((b"PK\x03\x04", b"PK\x05\x06")):
            raise self._contract_error("render response is not a DOCX zip payload")

        media_type = response.headers.get("content-type", "").split(";", 1)[0]
        if media_type != DOCX_MEDIA_TYPE:
            logger.warning(
                "Unexpected render Content-Type: %s", media_type or "missing"
            )

        filename = _content_disposition_filename(
            response.headers.get("content-disposition")
        )
        filename = _safe_filename(filename or f"document-{document_id}.docx")
        return RenderedDocument(
            content=content,
            filename=filename,
            media_type=DOCX_MEDIA_TYPE,
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        expected: set[int],
        json_body: dict[str, Any] | None = None,
        retry_ambiguous_errors: bool = True,
    ) -> httpx.Response:
        url = f"{self._base_url}{path}"
        for attempt in range(1, self._max_attempts + 1):
            try:
                response = await self._client.request(
                    method,
                    url,
                    json=json_body,
                    timeout=self._request_timeout,
                )
            except asyncio.CancelledError:
                raise
            except httpx.RequestError as exc:
                safe_to_retry = retry_ambiguous_errors or isinstance(
                    exc, _SAFE_CONNECT_ERRORS
                )
                if safe_to_retry and attempt < self._max_attempts:
                    await self._retry_sleep(attempt, path=path)
                    continue
                raise DocumentApiUnavailable(
                    f"{method} {path} failed: {type(exc).__name__}",
                    public_message=(
                        "Сервис документов временно недоступен. "
                        "Попробуйте ещё раз позже."
                    ),
                ) from exc

            if response.status_code in expected:
                return response
            if (
                response.status_code in _TRANSIENT_STATUSES
                and retry_ambiguous_errors
                and attempt < self._max_attempts
            ):
                await self._retry_sleep(
                    attempt,
                    path=path,
                    retry_after=response.headers.get("retry-after"),
                )
                continue

            if response.status_code == 422:
                detail = _response_detail(response)
                raise DocumentRejected(
                    f"{method} {path} rejected: {detail}",
                    public_message=f"Сервис отклонил данные: {detail}",
                )
            raise DocumentApiUnavailable(
                f"{method} {path} returned HTTP {response.status_code}",
                public_message=(
                    "Сервис документов вернул ошибку. Попробуйте ещё раз позже."
                ),
            )

        raise AssertionError("unreachable")

    async def _retry_sleep(
        self,
        attempt: int,
        *,
        path: str,
        retry_after: str | None = None,
    ) -> None:
        delay = _retry_after_seconds(retry_after)
        if delay is None:
            delay = min(self._retry_backoff * (2 ** (attempt - 1)), 10.0)
        logger.warning(
            "Document API request %s failed; retrying in %.2fs (attempt %s/%s)",
            path,
            delay,
            attempt,
            self._max_attempts,
        )
        await asyncio.sleep(delay)

    def _response_json(self, response: httpx.Response, context: str) -> Any:
        try:
            return response.json()
        except ValueError as exc:
            raise self._contract_error(f"{context} returned invalid JSON") from exc

    def _parse_document_type(self, item: object) -> DocumentType:
        if not isinstance(item, Mapping):
            raise TypeError("entry is not an object")
        raw_requisites = item.get("requisites", [])
        if not isinstance(raw_requisites, list):
            raise TypeError("requisites is not a list")
        requisites: list[RequisiteSpec] = []
        for requisite in raw_requisites:
            if not isinstance(requisite, Mapping):
                raise TypeError("requisite is not an object")
            requisites.append(
                RequisiteSpec(
                    key=_required_string(requisite, "key"),
                    label=_required_string(requisite, "label"),
                    required=requisite.get("required") is True,
                )
            )
        return DocumentType(
            id=_required_string(item, "id"),
            name=_required_string(item, "name"),
            description=_optional_string(item.get("description")),
            requisites=tuple(requisites),
        )

    def _parse_requisite(self, item: object) -> Requisite:
        if not isinstance(item, Mapping):
            raise TypeError("entry is not an object")
        value = item.get("value")
        if value is not None and not isinstance(value, str):
            raise TypeError("value is not a string or null")
        return Requisite(
            key=_required_string(item, "key"),
            label=_required_string(item, "label"),
            value=value,
            status=_required_string(item, "status"),
        )

    @staticmethod
    def _contract_error(message: str) -> DocumentApiContractError:
        return DocumentApiContractError(
            message,
            public_message=(
                "Сервис документов вернул неожиданный ответ. Попробуйте ещё раз позже."
            ),
        )


def _required_string(payload: Mapping[str, object], key: str) -> str:
    value = payload[key]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-blank string")
    return value


def _optional_string(value: object) -> str:
    return value if isinstance(value, str) else ""


def _response_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return "некорректные данные"
    detail = payload.get("detail") if isinstance(payload, Mapping) else None
    if isinstance(detail, str) and detail.strip():
        return detail.strip()[:500]
    if isinstance(detail, list):
        messages: list[str] = []
        for item in detail:
            if not isinstance(item, Mapping):
                continue
            message = item.get("msg")
            if isinstance(message, str):
                messages.append(message)
        if messages:
            return "; ".join(messages)[:500]
    return "некорректные данные"


def _retry_after_seconds(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        delay = float(value)
    except ValueError:
        return None
    if not math.isfinite(delay):
        return None
    return min(max(delay, 0.0), 10.0)


def _processing_timeout(document_id: str) -> DocumentProcessingTimeout:
    return DocumentProcessingTimeout(
        f"Document {document_id} exceeded processing deadline",
        public_message=(
            "Обработка заняла больше ожидаемого времени. "
            "Попробуйте ещё раз немного позже."
        ),
    )


def _content_disposition_filename(value: str | None) -> str | None:
    if not value:
        return None
    message = Message()
    message["content-disposition"] = value
    filename = message.get_filename()
    return filename if isinstance(filename, str) else None


def _safe_filename(value: str) -> str:
    filename = PurePath(value.replace("\\", "/")).name
    filename = re.sub(r"[\x00-\x1f\x7f]+", "_", filename).strip(" .")
    if not filename:
        filename = "document.docx"
    if not filename.casefold().endswith(".docx"):
        filename += ".docx"
    return filename[:-5][:175] + ".docx"
