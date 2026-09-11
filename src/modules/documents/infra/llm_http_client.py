"""HTTP-клиент в ml_service.

Любая сетевая проблема (включая кривой ответ без нужных ключей) превращается
в LLMUnavailable - выше по стеку её ловит хэндлер и включает деградацию
вместо падения фонового таска.
"""

from uuid import uuid4

import httpx

from src.core.config import settings
from src.modules.documents.application.ports.llm_client import LLMResult
from src.modules.documents.domain.exceptions import LLMUnavailable


class HttpLLMClient:
    async def process(
        self,
        *,
        draft: str,
        doc_type: str,
        doc_type_name: str,
        structure_hint: str,
        requisite_keys: list[str],
    ) -> LLMResult:
        if settings.ai_force_failure or not settings.ml_service_url:
            raise LLMUnavailable("ИИ-компонент отключён")

        try:
            async with httpx.AsyncClient(
                timeout=settings.ml_request_timeout_seconds
            ) as client:
                response = await client.post(
                    f"{settings.ml_service_url}/api/v1/process",
                    json={
                        "draft": draft,
                        "doc_type": doc_type,
                        "doc_type_name": doc_type_name,
                        "structure_hint": structure_hint,
                        "requisite_keys": requisite_keys,
                        "request_id": str(uuid4()),
                    },
                )
                response.raise_for_status()
                payload = response.json()

            return LLMResult(
                improved_text=payload["improved_text"],
                requisites=payload["requisites"],
                changes=payload.get("changes", []),
                fact_guard=payload.get("fact_guard", {}),
                is_fallback=payload.get("is_fallback", False),
            )
        except Exception as exc:  # noqa: BLE001
            # Сюда же попадает кривой JSON без "improved_text"/"requisites" -
            # раньше KeyError на сборке LLMResult вылетал уже за пределами
            # try/except и ронял фоновый таск вместо честного LLMUnavailable.
            raise LLMUnavailable(str(exc)) from exc
