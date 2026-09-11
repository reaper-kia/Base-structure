from types import TracebackType
from typing import Any, Self
from unittest.mock import AsyncMock

from src.modules.documents.application.ports.docx_renderer import RenderResult
from src.modules.documents.domain.entities import Requisite
from src.modules.documents.application.ports.llm_client import LLMResult


class FakeUoW:
    """Small asynchronous unit-of-work double shared by unit tests."""

    def __init__(self, *, documents: Any, outbox: Any | None = None) -> None:
        self.documents = documents
        self.outbox = outbox
        self.commit = AsyncMock()
        self.rollback = AsyncMock()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()


class FakeUoWFactory:
    def __init__(self, uow: FakeUoW) -> None:
        self._uow = uow

    def __call__(self) -> FakeUoW:
        return self._uow


class FakeLLMClient:
    """Test double for LLMClient - скриптованный результат вместо ml_service.

    По умолчанию (без result/exception) отражает draft в improved_text -
    имитация "чистой" обработки без изменений, удобно, когда тест сверяет
    improved_text с исходным draft.
    """

    def __init__(
        self,
        *,
        result: LLMResult | None = None,
        exception: Exception | None = None,
    ) -> None:
        self.result = result
        self.exception = exception
        self.calls: list[dict[str, Any]] = []

    async def process(
        self,
        *,
        draft: str,
        doc_type: str,
        doc_type_name: str,
        structure_hint: str,
        requisite_keys: list[str],
    ) -> LLMResult:
        self.calls.append(
            {
                "draft": draft,
                "doc_type": doc_type,
                "doc_type_name": doc_type_name,
                "structure_hint": structure_hint,
                "requisite_keys": requisite_keys,
            }
        )

        if self.exception is not None:
            raise self.exception

        if self.result is not None:
            return self.result

        return LLMResult(
            improved_text=draft,
            requisites={},
            changes=[],
            fact_guard={"verdict": "clean", "preserved": [], "lost": [], "added": []},
            is_fallback=False,
        )


class FakeDocxRenderer:
    """Test double for DocxRenderer - TemplateDocxRenderer (B2) пока заглушка.

    По умолчанию возвращает валидный с виду .docx (сигнатура ZIP "PK") без
    fallback, без обращения к templates/rules.yaml/python-docx.
    """

    def __init__(
        self,
        *,
        content: bytes = b"PK\x03\x04-fake-docx-bytes",
        template_fallback_used: bool = False,
        template_fallback_reason: str | None = None,
        exception: Exception | None = None,
    ) -> None:
        self.content = content
        self.template_fallback_used = template_fallback_used
        self.template_fallback_reason = template_fallback_reason
        self.exception = exception
        self.calls: list[dict[str, Any]] = []

    def render(
        self,
        improved_text: str,
        requisites: list[Requisite],
        template_id: str,
    ) -> RenderResult:
        self.calls.append(
            {
                "improved_text": improved_text,
                "requisites": requisites,
                "template_id": template_id,
            }
        )

        if self.exception is not None:
            raise self.exception

        return RenderResult(
            content=self.content,
            template_fallback_used=self.template_fallback_used,
            template_fallback_reason=self.template_fallback_reason,
        )
