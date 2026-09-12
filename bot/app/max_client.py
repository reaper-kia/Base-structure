from __future__ import annotations

import asyncio
import json
import logging
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePath
from time import monotonic
from typing import Any, Self
from urllib.parse import urlsplit

import httpx

from app.config import DOCX_MEDIA_TYPE, MAX_MESSAGE_LENGTH

logger = logging.getLogger(__name__)

_TRANSIENT_STATUSES = {408, 425, 429, 500, 502, 503, 504}
_ATTACHMENT_NOT_READY = "attachment.not.ready"


class MaxApiError(RuntimeError):
    """Base error for the MAX Bot API boundary."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code


class MaxAuthenticationError(MaxApiError):
    """The bot token is invalid or revoked."""


class MaxApiContractError(MaxApiError):
    """MAX returned a response outside the documented contract."""


@dataclass(frozen=True, slots=True)
class MaxRecipient:
    user_id: int | None = None
    chat_id: int | None = None

    def __post_init__(self) -> None:
        if (self.user_id is None) == (self.chat_id is None):
            raise ValueError("Exactly one of user_id or chat_id is required")

    @property
    def key(self) -> str:
        if self.user_id is not None:
            return f"user:{self.user_id}"
        return f"chat:{self.chat_id}"

    @property
    def query(self) -> dict[str, int]:
        if self.user_id is not None:
            return {"user_id": self.user_id}
        if self.chat_id is None:
            raise AssertionError("recipient is invalid")
        return {"chat_id": self.chat_id}


@dataclass(frozen=True, slots=True)
class UpdateBatch:
    updates: tuple[dict[str, Any], ...]
    marker: int | None


class InboundKind(StrEnum):
    MESSAGE = "message"
    BOT_STARTED = "bot_started"


@dataclass(frozen=True, slots=True)
class InboundEvent:
    kind: InboundKind
    chat_id: int
    recipient: MaxRecipient
    text: str | None = None


class MaxClient:
    """Small async MAX Bot API client with bounded retries and throttling."""

    def __init__(
        self,
        token: str,
        *,
        base_url: str = "https://platform-api2.max.ru",
        long_poll_timeout_seconds: int = 30,
        request_timeout_seconds: float = 15.0,
        max_attempts: int = 4,
        retry_backoff_seconds: float = 0.5,
        attachment_ready_attempts: int = 6,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._token = token
        self._base_url = base_url.rstrip("/")
        self._long_poll_timeout = long_poll_timeout_seconds
        self._request_timeout = request_timeout_seconds
        self._max_attempts = max_attempts
        self._retry_backoff = retry_backoff_seconds
        self._attachment_ready_attempts = attachment_ready_attempts
        self._client = client or httpx.AsyncClient(follow_redirects=False)
        self._owns_client = client is None
        self._send_locks: dict[str, asyncio.Lock] = {}
        self._last_send_at: dict[str, float] = {}
        self._minimum_message_interval = 0.55

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_args: object) -> None:
        await self.close()

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def get_updates(
        self,
        marker: int | None,
        *,
        timeout_seconds: int | None = None,
    ) -> UpdateBatch:
        poll_timeout = (
            self._long_poll_timeout if timeout_seconds is None else timeout_seconds
        )
        params: dict[str, str | int] = {
            "limit": 100,
            "timeout": poll_timeout,
            "types": "message_created,bot_started",
        }
        if marker is not None:
            params["marker"] = marker

        response = await self._api_request(
            "GET",
            "/updates",
            params=params,
            timeout=max(self._request_timeout, poll_timeout + 10.0),
        )
        payload = self._json_object(response, "GET /updates")
        raw_updates = payload.get("updates")
        if not isinstance(raw_updates, list):
            self._log_unexpected(response, "updates is not a list")
            raise MaxApiContractError("GET /updates: updates is not a list")

        updates: list[dict[str, Any]] = []
        for index, update in enumerate(raw_updates):
            if isinstance(update, dict):
                updates.append(update)
            else:
                logger.warning("Ignoring malformed MAX update at index %s", index)

        raw_marker = payload.get("marker")
        if raw_marker is None:
            next_marker = None
        elif isinstance(raw_marker, int) and not isinstance(raw_marker, bool):
            next_marker = raw_marker
        elif isinstance(raw_marker, str) and raw_marker.isdecimal():
            next_marker = int(raw_marker)
        else:
            self._log_unexpected(response, "marker has invalid type")
            raise MaxApiContractError("GET /updates: marker has invalid type")

        return UpdateBatch(updates=tuple(updates), marker=next_marker)

    async def send_text(self, recipient: MaxRecipient, text: str) -> None:
        for chunk in _split_text(text):
            await self._send_body(recipient, {"text": chunk})

    async def send_file(
        self,
        recipient: MaxRecipient,
        *,
        content: bytes,
        filename: str,
        text: str,
    ) -> None:
        if not content:
            raise ValueError("File content cannot be empty")
        safe_filename = _safe_filename(filename)
        token = await self._upload_file(
            content=content,
            filename=safe_filename,
        )

        chunks = _split_text(text) or ("",)
        for chunk in chunks[:-1]:
            await self._send_body(recipient, {"text": chunk})

        await asyncio.sleep(self._retry_backoff)
        await self._send_body(
            recipient,
            {
                "text": chunks[-1],
                "attachments": [{"type": "file", "payload": {"token": token}}],
            },
            wait_for_attachment=True,
        )

    async def _upload_file(self, *, content: bytes, filename: str) -> str:
        last_error: Exception | None = None
        for attempt in range(1, self._max_attempts + 1):
            try:
                endpoint_response = await self._api_request(
                    "POST",
                    "/uploads",
                    params={"type": "file"},
                    timeout=self._request_timeout,
                )
                endpoint = self._json_object(
                    endpoint_response,
                    "POST /uploads",
                )
                upload_url = endpoint.get("url")
                if not isinstance(upload_url, str) or not _is_safe_upload_url(
                    upload_url
                ):
                    self._log_unexpected(
                        endpoint_response,
                        "missing or unsafe upload URL",
                    )
                    raise MaxApiContractError(
                        "POST /uploads returned missing or unsafe URL"
                    )

                upload_response = await self._client.post(
                    upload_url,
                    files={
                        "data": (filename, content, DOCX_MEDIA_TYPE),
                    },
                    timeout=max(self._request_timeout, 60.0),
                )
                if not 200 <= upload_response.status_code < 300:
                    self._log_unexpected(
                        upload_response,
                        f"upload host returned HTTP {upload_response.status_code}",
                    )
                    raise MaxApiError(
                        "MAX upload host rejected file",
                        status_code=upload_response.status_code,
                    )
                upload_payload = self._json_object(
                    upload_response,
                    "MAX upload host",
                )
                token = _extract_upload_token(upload_payload)
                if token is None:
                    self._log_unexpected(
                        upload_response,
                        "upload response has no token",
                    )
                    raise MaxApiContractError(
                        "MAX upload response contains no file token"
                    )
                return token
            except asyncio.CancelledError:
                raise
            except (httpx.RequestError, MaxApiError) as exc:
                last_error = exc
                if isinstance(exc, MaxAuthenticationError):
                    raise
                if attempt >= self._max_attempts:
                    break
                await self._retry_sleep(attempt, operation="file upload")

        raise MaxApiError("Could not upload file to MAX") from last_error

    async def _send_body(
        self,
        recipient: MaxRecipient,
        body: dict[str, Any],
        *,
        wait_for_attachment: bool = False,
    ) -> None:
        attempts = (
            self._attachment_ready_attempts
            if wait_for_attachment
            else self._max_attempts
        )
        last_error: Exception | None = None

        for attempt in range(1, attempts + 1):
            try:
                response = await self._post_message_once(recipient, body)
            except asyncio.CancelledError:
                raise
            except httpx.RequestError as exc:
                last_error = exc
                if attempt >= attempts:
                    break
                await self._retry_sleep(attempt, operation="message send")
                continue

            if response.status_code == 200:
                return

            error = self._error_from_response(response, "POST /messages")
            last_error = error
            if isinstance(error, MaxAuthenticationError):
                raise error

            retryable = response.status_code in _TRANSIENT_STATUSES
            if wait_for_attachment and error.code == _ATTACHMENT_NOT_READY:
                retryable = True
            if retryable and attempt < attempts:
                await self._retry_sleep(
                    attempt,
                    operation="message send",
                    retry_after=response.headers.get("retry-after"),
                )
                continue
            raise error

        raise MaxApiError("Could not send message to MAX") from last_error

    async def _post_message_once(
        self,
        recipient: MaxRecipient,
        body: dict[str, Any],
    ) -> httpx.Response:
        lock = self._send_locks.setdefault(recipient.key, asyncio.Lock())
        async with lock:
            elapsed = monotonic() - self._last_send_at.get(recipient.key, 0.0)
            delay = self._minimum_message_interval - elapsed
            if delay > 0:
                await asyncio.sleep(delay)
            try:
                return await self._client.post(
                    f"{self._base_url}/messages",
                    params=recipient.query,
                    json=body,
                    headers=self._authorization_headers,
                    timeout=self._request_timeout,
                )
            finally:
                self._last_send_at[recipient.key] = monotonic()

    async def _api_request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, str | int],
        timeout: float,
    ) -> httpx.Response:
        for attempt in range(1, self._max_attempts + 1):
            try:
                response = await self._client.request(
                    method,
                    f"{self._base_url}{path}",
                    params=params,
                    headers=self._authorization_headers,
                    timeout=timeout,
                )
            except asyncio.CancelledError:
                raise
            except httpx.RequestError as exc:
                if attempt < self._max_attempts:
                    await self._retry_sleep(attempt, operation=path)
                    continue
                raise MaxApiError(f"MAX API {method} {path} transport error") from exc

            if response.status_code == 200:
                return response
            error = self._error_from_response(response, f"{method} {path}")
            if isinstance(error, MaxAuthenticationError):
                raise error
            if (
                response.status_code in _TRANSIENT_STATUSES
                and attempt < self._max_attempts
            ):
                await self._retry_sleep(
                    attempt,
                    operation=path,
                    retry_after=response.headers.get("retry-after"),
                )
                continue
            raise error

        raise AssertionError("unreachable")

    @property
    def _authorization_headers(self) -> dict[str, str]:
        return {"Authorization": self._token}

    async def _retry_sleep(
        self,
        attempt: int,
        *,
        operation: str,
        retry_after: str | None = None,
    ) -> None:
        delay = _retry_after_seconds(retry_after)
        if delay is None:
            delay = min(self._retry_backoff * (2 ** (attempt - 1)), 10.0)
        logger.warning(
            "MAX %s failed; retrying in %.2fs (attempt %s)",
            operation,
            delay,
            attempt,
        )
        await asyncio.sleep(delay)

    def _json_object(
        self,
        response: httpx.Response,
        context: str,
    ) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError as exc:
            self._log_unexpected(response, f"{context} returned invalid JSON")
            raise MaxApiContractError(f"{context} returned invalid JSON") from exc
        if not isinstance(payload, dict):
            self._log_unexpected(response, f"{context} returned non-object JSON")
            raise MaxApiContractError(f"{context} returned non-object JSON")
        return payload

    def _error_from_response(
        self,
        response: httpx.Response,
        context: str,
    ) -> MaxApiError:
        code: str | None = None
        message: str | None = None
        try:
            payload = response.json()
        except ValueError:
            payload = None
        if isinstance(payload, Mapping):
            raw_code = payload.get("code")
            raw_message = payload.get("message")
            code = raw_code if isinstance(raw_code, str) else None
            message = raw_message if isinstance(raw_message, str) else None

        self._log_unexpected(
            response,
            f"{context} failed with HTTP {response.status_code}",
        )
        error_text = f"{context} returned HTTP {response.status_code}"
        if code:
            error_text += f" ({code})"
        if message:
            error_text += f": {message[:300]}"
        error_type = (
            MaxAuthenticationError if response.status_code == 401 else MaxApiError
        )
        return error_type(
            error_text,
            status_code=response.status_code,
            code=code,
        )

    @staticmethod
    def _log_unexpected(response: httpx.Response, reason: str) -> None:
        logger.error(
            "Unexpected MAX response (%s): %s",
            reason,
            _safe_response_preview(response),
        )


def parse_inbound_update(update: Mapping[str, Any]) -> InboundEvent | None:
    update_type = update.get("update_type")
    if update_type == "bot_started":
        user = update.get("user")
        chat_id = _integer_id(update.get("chat_id"))
        user_id = _mapping_integer_id(user, "user_id")
        if chat_id is None or user_id is None:
            logger.warning("Ignoring malformed bot_started update")
            return None
        return InboundEvent(
            kind=InboundKind.BOT_STARTED,
            chat_id=chat_id,
            recipient=MaxRecipient(user_id=user_id),
        )

    if update_type != "message_created":
        return None

    message = update.get("message")
    if not isinstance(message, Mapping):
        logger.warning("Ignoring message_created update without message")
        return None
    sender = message.get("sender")
    if not isinstance(sender, Mapping) or sender.get("is_bot") is True:
        return None
    sender_id = _integer_id(sender.get("user_id"))
    if sender_id is None:
        logger.warning("Ignoring message without sender user_id")
        return None

    recipient_data = message.get("recipient")
    if not isinstance(recipient_data, Mapping):
        logger.warning("Ignoring message without recipient")
        return None
    chat_id = _integer_id(recipient_data.get("chat_id"))
    if chat_id is None:
        chat_id = _integer_id(update.get("chat_id")) or sender_id

    chat_type = recipient_data.get("chat_type")
    recipient = (
        MaxRecipient(chat_id=chat_id)
        if chat_type in {"chat", "channel"}
        else MaxRecipient(user_id=sender_id)
    )

    body = message.get("body")
    text = body.get("text") if isinstance(body, Mapping) else None
    if text is not None and not isinstance(text, str):
        text = None
    return InboundEvent(
        kind=InboundKind.MESSAGE,
        chat_id=chat_id,
        recipient=recipient,
        text=text,
    )


def _mapping_integer_id(value: object, key: str) -> int | None:
    if not isinstance(value, Mapping):
        return None
    return _integer_id(value.get(key))


def _integer_id(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _split_text(text: str) -> tuple[str, ...]:
    if not text:
        return ()
    chunks: list[str] = []
    remaining = text
    while len(remaining) > MAX_MESSAGE_LENGTH:
        boundary = remaining.rfind("\n", 0, MAX_MESSAGE_LENGTH + 1)
        if boundary < MAX_MESSAGE_LENGTH // 2:
            boundary = remaining.rfind(" ", 0, MAX_MESSAGE_LENGTH + 1)
        if boundary < MAX_MESSAGE_LENGTH // 2:
            boundary = MAX_MESSAGE_LENGTH
        chunk = remaining[:boundary].rstrip()
        if not chunk:
            chunk = remaining[:MAX_MESSAGE_LENGTH]
            boundary = MAX_MESSAGE_LENGTH
        chunks.append(chunk)
        remaining = remaining[boundary:].lstrip("\n ")
    if remaining:
        chunks.append(remaining)
    return tuple(chunks)


def _safe_filename(value: str) -> str:
    filename = PurePath(value.replace("\\", "/")).name
    filename = re.sub(r"[\x00-\x1f\x7f]+", "_", filename).strip(" .")
    if not filename:
        filename = "document.docx"
    if not filename.casefold().endswith(".docx"):
        filename += ".docx"
    return filename[:-5][:175] + ".docx"


def _is_safe_upload_url(value: str) -> bool:
    parsed = urlsplit(value)
    return (
        parsed.scheme == "https"
        and bool(parsed.hostname)
        and parsed.username is None
        and parsed.password is None
        and not parsed.fragment
    )


def _extract_upload_token(payload: Mapping[str, Any]) -> str | None:
    token = payload.get("token")
    if isinstance(token, str) and token:
        return token
    for key in ("payload", "retval", "data", "file"):
        nested = payload.get(key)
        if isinstance(nested, Mapping):
            token = nested.get("token")
            if isinstance(token, str) and token:
                return token
    return None


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


def _safe_response_preview(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        text = response.text[:1_000]
        text = re.sub(r"https://[^\s\"']+", "<redacted-url>", text)
        return re.sub(
            r'(?i)(token|access_token)(["\s:=]+)[^\s,}"\']+',
            r"\1\2<redacted>",
            text,
        )

    def redact(value: object) -> object:
        if isinstance(value, Mapping):
            return {
                str(key): (
                    "<redacted>"
                    if str(key).casefold() in {"token", "url", "access_token"}
                    else redact(item)
                )
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [redact(item) for item in value]
        return value

    return json.dumps(redact(payload), ensure_ascii=False)[:1_000]
