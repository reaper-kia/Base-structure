import json
import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ml_service.config import settings
from ml_service.registry import registry
from ml_service.schemas import (
    FactGuardResult,
    ModelHealth,
    PredictRequest,
    PredictResponse,
    ProcessRequest,
    ProcessResponse,
)
from ml_service.guard import anchors, fact_guard

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    registry.load()
    yield


def build_strict_schema(keys: list[str]) -> dict:
    """ML-04: Строит схему только под ожидаемые ключи."""
    props = {"improved_text": {"type": "string"}}
    for k in keys:
        props[k] = {"type": ["string", "null"]}
    return {
        "type": "object",
        "properties": props,
        "required": ["improved_text"] + keys,
        "additionalProperties": False,
    }


def validate_llm_response(data: dict, expected_keys: list[str]) -> bool:
    """ML-04: Жесткая проверка типов (отсекает массивы и лишние ключи)."""
    if not isinstance(data, dict):
        return False
    if "improved_text" not in data or not isinstance(data["improved_text"], str):
        return False
    for k in expected_keys:
        if k not in data:
            return False
        if data[k] is not None and not isinstance(data[k], str):
            return False
    # Проверка на лишние ключи (additionalProperties = False)
    allowed = set(["improved_text"] + expected_keys)
    if any(k not in allowed for k in data.keys()):
        return False
    return True


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
    )

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/health/model", response_model=ModelHealth)
    async def model_health():
        return ModelHealth(
            model_loaded=registry.is_loaded,
            model_version=registry.version,
            fallback_enabled=settings.fallback_enabled,
            supported_tasks=registry.supported_tasks,
        )

    @app.post("/api/v1/process", response_model=ProcessResponse)
    async def process_document(request: ProcessRequest):
        started = time.perf_counter()
        source_anchors = anchors.extract(request.draft)

        prompt_path = Path("src/ml_service/llm/prompts/process.txt")
        final_prompt = prompt_path.read_text(encoding="utf-8").format(
            doc_type_name=request.doc_type_name,
            structure_hint=request.structure_hint,
            draft=request.draft,
        )

        llm_schema = build_strict_schema(request.requisite_keys)
        payload = {
            "model": settings.ollama_model,
            "prompt": final_prompt,
            "format": llm_schema,
            "stream": False,
            "options": {"temperature": 0.2},
        }
        ollama_endpoint = f"{settings.ollama_url.rstrip('/')}/api/generate"

        max_attempts = 2
        is_fallback = False
        reason_code = None

        result_data = {}
        improved_text = ""
        current_guard_result = None

        async with httpx.AsyncClient() as client:
            for attempt in range(max_attempts):
                try:
                    resp = await client.post(
                        ollama_endpoint,
                        json=payload,
                        timeout=settings.ollama_timeout_seconds,
                    )
                    # Если сервис отвалился (500)
                    if resp.status_code != 200:
                        reason_code = "model_unavailable"
                        raise ValueError("Model API error")

                    # Невалидный (нераспарсиваемый) JSON — это ошибка СХЕМЫ, а не
                    # недоступность модели (ML-06: коды должны различаться).
                    try:
                        current_result_data = json.loads(resp.json()["response"])
                    except (ValueError, KeyError, TypeError):
                        reason_code = "schema_invalid"
                        logger.warning(
                            f"Ответ модели не разобрался как JSON (попытка {attempt + 1})"
                        )
                        continue

                    # ML-04: Строгая валидация JSON
                    if not validate_llm_response(
                        current_result_data, request.requisite_keys
                    ):
                        reason_code = "schema_invalid"
                        logger.warning(f"Ошибка схемы (попытка {attempt + 1})")
                        continue

                    current_improved_text = current_result_data["improved_text"]
                    result_anchors = anchors.extract(current_improved_text)
                    current_guard_result = fact_guard.check(
                        source_anchors, result_anchors
                    )

                    result_data = current_result_data
                    improved_text = current_improved_text

                    if current_guard_result.verdict == "blocked":
                        reason_code = "facts_unverified"
                        logger.warning(
                            f"Fact Guard заблокировал ответ (попытка {attempt + 1})"
                        )
                        continue

                    reason_code = None  # Всё ок
                    break

                except Exception as e:
                    logger.error(f"Ошибка на попытке {attempt + 1}: {e}")
                    if not reason_code:
                        reason_code = "model_unavailable"
                    if attempt == max_attempts - 1:
                        is_fallback = True
                        break
            else:
                # Цикл завершился без break (исчерпаны попытки)
                is_fallback = True

        if is_fallback:
            improved_text = request.draft
            result_data = {}
            current_guard_result = fact_guard.GuardResult(
                verdict="clean",
                source_count=sum(len(v) for v in source_anchors.values()),
                preserved_count=sum(len(v) for v in source_anchors.values()),
            )

        clean_requisites = {}
        draft_lower = request.draft.lower()
        for key in request.requisite_keys:
            if is_fallback:
                clean_requisites[key] = None
            else:
                val = result_data.get(key)
                if not val or str(val).lower() not in draft_lower:
                    clean_requisites[key] = None
                else:
                    clean_requisites[key] = val

        return ProcessResponse(
            request_id=request.request_id,
            improved_text=improved_text,
            requisites=clean_requisites,
            fact_guard=FactGuardResult(**current_guard_result.as_dict()),
            is_fallback=is_fallback,
            reason_code=reason_code,
        )

    @app.post("/api/v1/predict", response_model=PredictResponse)
    async def predict(request: PredictRequest):
        predictions, fallback_used = await registry.predict(request)
        return PredictResponse(
            request_id=request.request_id,
            task=request.task,
            predictions=predictions,
            model_version=registry.version if not fallback_used else "fallback-1.0.0",
            is_fallback=fallback_used,
            latency_ms=0.0,
        )

    return app


app = create_app()
