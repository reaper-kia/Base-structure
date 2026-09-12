"""HTTP-клиент в ml_service.

Любая сетевая проблема (включая кривой ответ без нужных ключей) превращается
в LLMUnavailable — выше по стеку её ловит хэндлер и включает деградацию
вместо падения фонового таска.
"""

from uuid import uuid4

import httpx

from src.core.config import settings
from src.modules.documents.application.ports.llm_client import LLMResult
from src.modules.documents.domain.exceptions import LLMUnavailable


class HttpLLMClient:
    def __init__(self, ai_force_failure: bool = False):
        # Флаг имитации отказа передаётся извне (из сессии эксперта),
        # а не читается из глобальных settings — см. TL-14.
        self._ai_force_failure = ai_force_failure

    async def process(
        self,
        *,
        draft: str,
        doc_type: str,
        doc_type_name: str,
        structure_hint: str,
        requisite_keys: list[str],
    ) -> LLMResult:
        if self._ai_force_failure or not settings.ml_service_url:
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
                model_version=payload.get("model_version", "unknown"),
                latency_ms=payload.get("latency_ms"),
                reason_code=payload.get("reason_code"),
            )
        except Exception as exc:  # noqa: BLE001
            raise LLMUnavailable(str(exc)) from exc
