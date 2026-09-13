import json
import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from ml_service.stt import load_model as load_stt_model, recognize as stt_recognize
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
    load_stt_model()
    yield

def build_strict_schema(keys: list[str]) -> dict:
    props = {"improved_text": {"type": "string"}}
    for k in keys:
        props[k] = {"type": ["string", "null"]}
        
    candidate_props = {k: {"type": ["string", "null"]} for k in keys}
    props["registry_candidates"] = {
        "type": "object",
        "properties": candidate_props,
        "additionalProperties": False
    }
    
    return {
        "type": "object",
        "properties": props,
        "required": ["improved_text"] + keys,
        "additionalProperties": False,
    }

def validate_llm_response(data: dict, expected_keys: list[str]) -> bool:
    if not isinstance(data, dict):
        return False
    if "improved_text" not in data or not isinstance(data["improved_text"], str):
        return False
    for k in expected_keys:
        if k not in data:
            return False
        if data[k] is not None and not isinstance(data[k], str):
            return False
            
    if "registry_candidates" in data:
        cands = data["registry_candidates"]
        if not isinstance(cands, dict):
            return False
        for k in cands:
            if k not in expected_keys:
                return False
            if cands[k] is not None and not isinstance(cands[k], str):
                return False

    allowed = set(["improved_text", "registry_candidates"] + expected_keys)
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

    @app.post("/stt")
    async def stt(audio: UploadFile = File(...)):
        audio_bytes = await audio.read()
        try:
            result = stt_recognize(audio_bytes)
            return result
        except RuntimeError as e:
            raise HTTPException(status_code=503, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

    @app.post("/api/v1/process", response_model=ProcessResponse)
    async def process_document(request: ProcessRequest):
        started = time.perf_counter()
        source_anchors = anchors.extract(request.draft)

        chunks_text = "Корпус пуст."
        if request.retrieved_chunks:
            chunks_text = "\n\n".join(
                [f"[{c.doc_id}] {c.section_title}\n{c.text}" for c in request.retrieved_chunks]
            )

        prompt_path = Path("src/ml_service/llm/prompts/process.txt")
        final_prompt = prompt_path.read_text(encoding="utf-8").format(
            doc_type_name=request.doc_type_name,
            structure_hint=request.structure_hint,
            terminology_context=request.terminology_context,
            chunks_context=chunks_text,
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
                    if resp.status_code != 200:
                        reason_code = "model_unavailable"
                        raise ValueError("Model API error")

                    try:
                        current_result_data = json.loads(resp.json()["response"])
                    except (ValueError, KeyError, TypeError):
                        reason_code = "schema_invalid"
                        logger.warning(f"JSON error (попытка {attempt + 1})")
                        continue

                    if not validate_llm_response(current_result_data, request.requisite_keys):
                        reason_code = "schema_invalid"
                        logger.warning(f"Schema error (попытка {attempt + 1})")
                        continue

                    current_improved_text = current_result_data["improved_text"]
                    result_anchors = anchors.extract(current_improved_text)
                    current_guard_result = fact_guard.check(source_anchors, result_anchors)

                    result_data = current_result_data
                    improved_text = current_improved_text

                    if current_guard_result.verdict == "blocked":
                        reason_code = "facts_unverified"
                        logger.warning(f"Fact Guard blocked (попытка {attempt + 1})")
                        continue

                    reason_code = None
                    break

                except Exception as e:
                    logger.error(f"Ошибка на попытке {attempt + 1}: {e}")
                    if not reason_code:
                        reason_code = "model_unavailable"
                    if attempt == max_attempts - 1:
                        is_fallback = True
                        break
            else:
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
                continue
                
            val = result_data.get(key)
            if val and str(val).lower() in draft_lower:
                clean_requisites[key] = {
                    "value": val,
                    "status": "found_in_draft",
                    "source_span": val
                }
                continue

            candidates = result_data.get("registry_candidates", {})
            candidate_val = candidates.get(key) if isinstance(candidates, dict) else None
            
            if candidate_val:
                source_chunk = None
                cand_lower = str(candidate_val).lower()
                for chunk in request.retrieved_chunks:
                    if cand_lower in chunk.text.lower():
                        source_chunk = chunk
                        break
                
                if source_chunk:
                    clean_requisites[key] = {
                        "value": candidate_val,
                        "status": "from_registry",
                        "source_span": source_chunk.text,
                        "source_doc_id": source_chunk.doc_id
                    }
                    continue
            
            clean_requisites[key] = None

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
