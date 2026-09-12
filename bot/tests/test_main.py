from __future__ import annotations

import unittest
from uuid import uuid4

from app.config import DOCX_MEDIA_TYPE, Settings
from app.doc_api import (
    DocumentSnapshot,
    DocumentType,
    RenderedDocument,
    Requisite,
    RequisiteSpec,
    Template,
)
from app.main import BotApplication
from app.max_client import InboundEvent, InboundKind, MaxRecipient


class _FakeMaxClient:
    def __init__(self) -> None:
        self.texts: list[str] = []
        self.files: list[tuple[str, bytes, str]] = []

    async def send_text(self, _recipient: MaxRecipient, text: str) -> None:
        self.texts.append(text)

    async def send_file(
        self,
        _recipient: MaxRecipient,
        *,
        content: bytes,
        filename: str,
        text: str,
    ) -> None:
        self.files.append((filename, content, text))


class _FakeDocumentClient:
    def __init__(self) -> None:
        self.created_with: tuple[str, str, str] | None = None
        self.document_id = str(uuid4())

    async def get_document_types(self) -> tuple[DocumentType, ...]:
        return (
            DocumentType(
                id="memo",
                name="Служебная записка",
                description="",
                requisites=(
                    RequisiteSpec(key="doc_date", label="Дата", required=True),
                ),
            ),
        )

    async def get_templates(self) -> tuple[Template, ...]:
        return (Template(id="classic", name="Классический", description=""),)

    async def create_document(
        self,
        *,
        draft: str,
        doc_type: str,
        template_id: str,
    ) -> str:
        self.created_with = (draft, doc_type, template_id)
        return self.document_id

    async def poll_until_done(self, document_id: str) -> DocumentSnapshot:
        return DocumentSnapshot(
            id=document_id,
            status="degraded",
            stage=None,
            requisites=(
                Requisite(
                    key="doc_date",
                    label="Дата",
                    value=None,
                    status="missing",
                ),
            ),
            is_fallback=True,
        )

    async def render_document(self, _document_id: str) -> RenderedDocument:
        return RenderedDocument(
            content=b"PK\x03\x04docx",
            filename="memo.docx",
            media_type=DOCX_MEDIA_TYPE,
        )


class BotApplicationTests(unittest.IsolatedAsyncioTestCase):
    async def test_full_chat_flow_reports_missing_and_sends_docx(self) -> None:
        max_client = _FakeMaxClient()
        document_client = _FakeDocumentClient()
        application = BotApplication(
            settings=Settings(
                max_bot_token="secret",
                api_base_url="http://documents.test",
            ),
            max_client=max_client,  # type: ignore[arg-type]
            document_client=document_client,  # type: ignore[arg-type]
        )
        recipient = MaxRecipient(user_id=15)

        async def send(text: str) -> None:
            await application._handle_event(  # noqa: SLF001
                InboundEvent(
                    kind=InboundKind.MESSAGE,
                    chat_id=900,
                    recipient=recipient,
                    text=text,
                )
            )

        await send("Черновик документа")
        await send("1")
        await send("classic")
        _generation_id, task = application._jobs[900]  # noqa: SLF001
        await task

        self.assertEqual(
            document_client.created_with,
            ("Черновик документа", "memo", "classic"),
        )
        self.assertTrue(any("Дата" in text for text in max_client.texts))
        self.assertEqual(max_client.files[0][0], "memo.docx")
        self.assertIn("резервном режиме", max_client.files[0][2])


if __name__ == "__main__":
    unittest.main()
