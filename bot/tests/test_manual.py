from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from app.conversation import Choice, ConversationStore, RequiredRequisite
from app.doc_api import DocumentApiClient, DocumentApiError

DEFAULT_DRAFT = (
    "Прошу подготовить служебную записку о закупке двух ноутбуков "
    "для отдела разработки до 20 сентября 2026 года."
)


async def run() -> Path:
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
    draft = os.getenv("MANUAL_DRAFT", DEFAULT_DRAFT)
    output = Path(os.getenv("MANUAL_OUTPUT_PATH", "manual-result.docx"))

    async with DocumentApiClient(
        base_url,
        request_timeout_seconds=_float_env("API_REQUEST_TIMEOUT_SECONDS", 15.0),
        poll_interval_seconds=_float_env("DOCUMENT_POLL_INTERVAL_SECONDS", 1.5),
        processing_timeout_seconds=_float_env(
            "DOCUMENT_PROCESSING_TIMEOUT_SECONDS", 120.0
        ),
    ) as client:
        document_types = await client.get_document_types()
        templates = await client.get_templates()

        type_choices = tuple(
            Choice(
                id=item.id,
                label=item.name,
                required_requisites=tuple(
                    RequiredRequisite(key=req.key, label=req.label)
                    for req in item.requisites
                    if req.required
                ),
            )
            for item in document_types
        )
        template_choices = tuple(
            Choice(id=item.id, label=item.name) for item in templates
        )

        chat_id = 1
        store = ConversationStore()
        store.start(chat_id, draft, type_choices)
        doc_type = store.resolve_doc_type(
            chat_id,
            os.getenv("MANUAL_DOC_TYPE", type_choices[0].id),
        )
        store.select_doc_type(chat_id, doc_type, template_choices)
        template = store.resolve_template(
            chat_id,
            os.getenv("MANUAL_TEMPLATE_ID", template_choices[0].id),
        )
        request = store.begin_generation(chat_id, template)

        document_id = await client.create_document(
            draft=request.draft,
            doc_type=request.doc_type_id,
            template_id=request.template_id,
        )
        print(f"Создан документ {document_id}; ожидаю обработку…")
        snapshot = await client.poll_until_done(document_id)
        rendered = await client.render_document(document_id)

        missing = {item.key for item in snapshot.requisites if item.status == "missing"}
        missing_labels = [
            item.label for item in request.required_requisites if item.key in missing
        ]
        if missing_labels:
            print("Не найдены обязательные реквизиты: " + ", ".join(missing_labels))

        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(rendered.content)
        store.complete(chat_id, request.generation_id)
        print(
            f"Готово: status={snapshot.status}, bytes={len(rendered.content)}, "
            f"file={output.resolve()}"
        )
        return output


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    return default if raw is None else float(raw)


def main() -> int:
    try:
        asyncio.run(run())
    except (DocumentApiError, OSError, ValueError) as exc:
        print(f"Ручная проверка не пройдена: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
