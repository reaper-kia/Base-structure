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

# Подключаем наши новые скрипты защиты
from ml_service.guard import anchors, fact_guard

logging.basicConfig(
    level=logging.DEBUG if settings.app_debug else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    registry.load()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        docs_url="/docs",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/model", response_model=ModelHealth, tags=["health"])
    async def model_health() -> ModelHealth:
        return ModelHealth(
            model_loaded=registry.is_loaded,
            model_version=registry.version,
            fallback_enabled=settings.fallback_enabled,
            supported_tasks=registry.supported_tasks,
        )

    @app.post("/api/v1/process", response_model=ProcessResponse, tags=["ml"])
    async def process_document(request: ProcessRequest) -> ProcessResponse:
        started = time.perf_counter()
        
        # 1. ДО ИИ: Вытаскиваем якоря из черновика
        source_anchors = anchors.extract(request.draft)
        
        prompt_path = Path("src/ml_service/llm/prompts/process.txt")
        prompt_template = prompt_path.read_text(encoding="utf-8")
        final_prompt = prompt_template.format(
            doc_type_name=request.doc_type_name,
            structure_hint=request.structure_hint,
            draft=request.draft
        )

        schema_path = Path("../../contracts/llm_schema.json")
        llm_schema = json.loads(schema_path.read_text(encoding="utf-8"))

        payload = {
            "model": "qwen2.5:7b-instruct",
            "prompt": final_prompt,
            "format": llm_schema,
            "stream": False,
            "options": {"temperature": 0.2}
        }

        max_attempts = 2  # Даем модели максимум 2 попытки
        is_fallback = False
        
        result_data = {}
        improved_text = ""
        current_guard_result = None

        async with httpx.AsyncClient() as client:
            for attempt in range(max_attempts):
                try:
                    resp = await client.post("http://localhost:11434/api/generate", json=payload, timeout=90.0)
                    resp.raise_for_status()
                    
                    current_result_data = json.loads(resp.json()["response"])
                    current_improved_text = current_result_data.get("improved_text", "")
                    if not current_improved_text:
                        current_improved_text = "Текст не удалось обработать."
                    
                    # 2. ПОСЛЕ ИИ: Вытаскиваем якоря из ответа и сверяем
                    result_anchors = anchors.extract(current_improved_text)
                    current_guard_result = fact_guard.check(source_anchors, result_anchors)
                    
                    result_data = current_result_data
                    improved_text = current_improved_text
                    
                    if current_guard_result.verdict == "blocked":
                        logger.warning(f"Fact Guard заблокировал ответ (попытка {attempt + 1}/{max_attempts})")
                        continue  # Уходим на второй круг (retry)
                    else:
                        break  # clean или warning — нас устраивает, выходим из цикла!
                        
                except Exception as e:
                    logger.error(f"Ошибка ИИ на попытке {attempt + 1}: {e}")
                    if attempt == max_attempts - 1:
                        is_fallback = True  # Если и вторая попытка упала (например, JSON порван)
                        break

        # ML-05: Если fallback активирован (сеть упала) или ИИ дважды выдал галлюцинацию
        if is_fallback or (current_guard_result and current_guard_result.verdict == "blocked"):
            logger.warning(f"Активирован Fallback режим для запроса {request.request_id}")
            is_fallback = True
            improved_text = request.draft  # Отдаем исходный текст как есть
            result_data = {}               # Реквизиты пустые
            
            # В fallback-режиме Fact Guard всегда "чистый", так как мы не меняли текст
            current_guard_result = fact_guard.GuardResult(
                verdict="clean",
                source_count=sum(len(v) for v in source_anchors.values()),
                preserved_count=sum(len(v) for v in source_anchors.values())
            )

        # Гарантии бэкенду по реквизитам
        clean_requisites = {}
        for key in request.requisite_keys:
            if is_fallback:
                clean_requisites[key] = None
            else:
                val = result_data.get(key)
                clean_requisites[key] = None if val == "" else val

        latency_ms = (time.perf_counter() - started) * 1000
        logger.info(f"Processed {request.request_id} in {latency_ms:.1f}ms (Fallback: {is_fallback})")

        return ProcessResponse(
            request_id=request.request_id,
            improved_text=improved_text,
            requisites=clean_requisites,
            fact_guard=FactGuardResult(**current_guard_result.as_dict()), 
            is_fallback=is_fallback
        )

    @app.post("/api/v1/predict", response_model=PredictResponse, tags=["ml"])
    async def predict(request: PredictRequest) -> PredictResponse:
        started = time.perf_counter()
        predictions, fallback_used = await registry.predict(request)
        latency_ms = (time.perf_counter() - started) * 1000

        logger.info(
            "predict request_id=%s task=%s subject=%s fallback=%s latency=%.1fms",
            request.request_id,
            request.task,
            request.subject_id,
            fallback_used,
            latency_ms,
        )

        return PredictResponse(
            request_id=request.request_id,
            task=request.task,
            predictions=predictions,
            model_version=registry.version if not fallback_used else "fallback-1.0.0",
            is_fallback=fallback_used,
            latency_ms=round(latency_ms, 2),
        )

    return app


app = create_app()