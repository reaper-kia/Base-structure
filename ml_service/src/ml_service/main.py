from __future__ import annotations

import json
import logging
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from ml_service.config import settings
from ml_service.guard import anchors, fact_guard
from ml_service.schemas import (
    FactGuardResult,
    ModelHealth,
    ProcessRequest,
    ProcessResponse,
)


logging.basicConfig(
    level=logging.DEBUG if settings.app_debug else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger(__name__)

PACKAGE_DIR = Path(__file__).resolve().parent
PROMPT_PATH = PACKAGE_DIR / "llm" / "prompts" / "process.txt"

MAX_GENERATION_ATTEMPTS = 2
ALLOWED_CHANGE_TYPES = {
    "spelling",
    "punctuation",
    "style",
    "structure",
}


@lru_cache
def load_prompt_template() -> str:
    """Загружает версионируемый промпт один раз."""

    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Не удалось прочитать промпт: {PROMPT_PATH}") from exc


@lru_cache
def load_llm_schema() -> dict[str, Any]:
    """Ищет contracts/llm_schema.json при локальном и Docker-запуске."""

    current_file = Path(__file__).resolve()

    for parent in current_file.parents:
        schema_path = parent / "contracts" / "llm_schema.json"

        if not schema_path.is_file():
            continue

        try:
            payload = json.loads(schema_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(
                f"Не удалось загрузить JSON Schema: {schema_path}"
            ) from exc

        if not isinstance(payload, dict):
            raise RuntimeError(f"JSON Schema должна быть объектом: {schema_path}")

        return payload

    raise RuntimeError(
        "Не найден contracts/llm_schema.json. "
        "Проверь Dockerfile и build context ml_service."
    )


def build_prompt(request: ProcessRequest, *, retry: bool = False) -> str:
    """Строит промпт с динамическим набором реквизитов."""

    requisites_skeleton = json.dumps(
        {key: None for key in request.requisite_keys},
        ensure_ascii=False,
    )

    template = load_prompt_template()

    prompt = template.format(
        doc_type_name=request.doc_type_name,
        structure_hint=request.structure_hint,
        requisite_keys=json.dumps(
            request.requisite_keys,
            ensure_ascii=False,
        ),
        requisites_skeleton=requisites_skeleton,
        draft=request.draft,
    )

    # Этот блок добавляется независимо от содержимого process.txt.
    # Поэтому старый промпт с плоскими реквизитами не сломает контракт.
    prompt += f"""

ОБЯЗАТЕЛЬНЫЙ ФОРМАТ ОТВЕТА:

{{
  "improved_text": "непустой обработанный текст",
  "requisites": {requisites_skeleton},
  "changes": [
    {{
      "type": "spelling | punctuation | style | structure",
      "from": "исходный фрагмент",
      "to": "исправленный фрагмент"
    }}
  ]
}}

Объект requisites должен содержать ровно перечисленные ключи.
Если реквизит отсутствует в черновике — верни null.
Не возвращай реквизиты на верхнем уровне JSON.
Не добавляй markdown и пояснения.
"""

    if retry:
        prompt += """

ПРЕДЫДУЩИЙ ОТВЕТ БЫЛ ОТКЛОНЁН.
Особенно внимательно проверь, что:
1. ответ является валидным JSON;
2. improved_text не пустой;
3. все факты присутствовали в исходном черновике;
4. requisites является вложенным объектом;
5. никакие даты, ФИО, номера, суммы и организации не выдуманы.
"""

    return prompt


def extract_json(raw_response: str) -> dict[str, Any]:
    """Дешёвый repair: убирает markdown и мусор вокруг JSON."""

    text = raw_response.strip()

    if text.startswith("```"):
        lines = text.splitlines()

        if lines:
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        text = "\n".join(lines).strip()

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end < start:
        raise ValueError("В ответе модели не найден JSON-объект")

    payload = json.loads(text[start : end + 1])

    if not isinstance(payload, dict):
        raise ValueError("Ответ модели должен быть JSON-объектом")

    return payload


def normalize_changes(payload: Any) -> list[dict[str, str]]:
    """Отбрасывает некорректные элементы changes без падения запроса."""

    if not isinstance(payload, list):
        return []

    result: list[dict[str, str]] = []

    for item in payload:
        if not isinstance(item, dict):
            continue

        change_type = item.get("type")
        from_value = item.get("from")
        to_value = item.get("to")

        if change_type not in ALLOWED_CHANGE_TYPES:
            continue

        if not isinstance(from_value, str):
            continue

        if not isinstance(to_value, str):
            continue

        result.append(
            {
                "type": change_type,
                "from": from_value,
                "to": to_value,
            }
        )

    return result


def normalize_model_result(
    payload: dict[str, Any],
    requisite_keys: list[str],
) -> tuple[str, dict[str, str | None], list[dict[str, str]]]:
    """Проверяет обязательные поля ответа модели."""

    improved_text = payload.get("improved_text")

    if not isinstance(improved_text, str) or not improved_text.strip():
        raise ValueError("Модель вернула пустой improved_text")

    improved_text = improved_text.strip()

    raw_requisites = payload.get("requisites")

    if not isinstance(raw_requisites, dict):
        raise ValueError("Модель не вернула объект requisites")

    clean_requisites: dict[str, str | None] = {}

    for key in requisite_keys:
        value = raw_requisites.get(key)

        if isinstance(value, str):
            value = value.strip() or None
        elif value is not None:
            # Контракт разрешает только string | null.
            value = None

        clean_requisites[key] = value

    changes = normalize_changes(payload.get("changes"))

    return improved_text, clean_requisites, changes


async def call_ollama(
    client: httpx.AsyncClient,
    *,
    prompt: str,
    schema: dict[str, Any],
) -> str:
    """Выполняет один запрос к Ollama."""

    response = await client.post(
        f"{settings.ollama_url.rstrip('/')}/api/generate",
        json={
            "model": settings.ollama_model,
            "prompt": prompt,
            "format": schema,
            "stream": False,
            "options": {
                "temperature": 0.2,
            },
        },
    )

    response.raise_for_status()

    payload = response.json()
    raw_response = payload.get("response")

    if not isinstance(raw_response, str) or not raw_response.strip():
        raise ValueError("Ollama вернула пустое поле response")

    return raw_response


async def repair_response(
    client: httpx.AsyncClient,
    *,
    raw_response: str,
    schema: dict[str, Any],
    requisite_keys: list[str],
) -> dict[str, Any]:
    """Просит модель исправить невалидный JSON один раз."""

    requisites_skeleton = json.dumps(
        {key: None for key in requisite_keys},
        ensure_ascii=False,
    )

    repair_prompt = f"""
Исправь приведённый ниже ответ и верни только валидный JSON.
Не добавляй markdown и пояснения.
Не придумывай новые значения.

Требуемая структура:

{{
  "improved_text": "непустая строка",
  "requisites": {requisites_skeleton},
  "changes": []
}}

Повреждённый ответ:

{raw_response}
"""

    repaired_raw = await call_ollama(
        client,
        prompt=repair_prompt,
        schema=schema,
    )

    return extract_json(repaired_raw)


async def generate_result(
    client: httpx.AsyncClient,
    *,
    request: ProcessRequest,
    schema: dict[str, Any],
    retry: bool,
) -> tuple[str, dict[str, str | None], list[dict[str, str]]]:
    """Генерация, дешёвый JSON repair и один модельный repair."""

    raw_response = await call_ollama(
        client,
        prompt=build_prompt(request, retry=retry),
        schema=schema,
    )

    try:
        payload = extract_json(raw_response)
        return normalize_model_result(
            payload,
            request.requisite_keys,
        )
    except (json.JSONDecodeError, ValueError) as first_error:
        logger.warning(
            "Ответ модели нарушил контракт, запускаем repair: %s",
            first_error,
        )

    repaired_payload = await repair_response(
        client,
        raw_response=raw_response,
        schema=schema,
        requisite_keys=request.requisite_keys,
    )

    return normalize_model_result(
        repaired_payload,
        request.requisite_keys,
    )


def build_guard_text(
    improved_text: str,
    requisites: dict[str, str | None],
) -> str:
    """Fact Guard обязан проверять и текст, и извлечённые реквизиты."""

    requisite_values = [
        value for value in requisites.values() if isinstance(value, str) and value
    ]

    return "\n".join([improved_text, *requisite_values])


def build_fallback_guard(
    source_anchors: dict[str, list[str]],
) -> fact_guard.GuardResult:
    """Исходный текст относительно самого себя всегда проходит Fact Guard."""

    return fact_guard.check(source_anchors, source_anchors)


def create_process_response(
    *,
    request_id: str,
    improved_text: str,
    requisites: dict[str, str | None],
    changes: list[dict[str, str]],
    guard_result: fact_guard.GuardResult,
    is_fallback: bool,
    model_version: str,
    latency_ms: float,
) -> ProcessResponse:
    """Единая точка формирования HTTP-ответа."""

    # request_id оставлен в конструкторе для совместимости со старой схемой.
    # В исправленной ProcessResponse лишнее поле будет проигнорировано.
    return ProcessResponse(
        request_id=request_id,
        improved_text=improved_text,
        requisites=requisites,
        changes=changes,
        fact_guard=FactGuardResult(**guard_result.as_dict()),
        is_fallback=is_fallback,
        model_version=model_version,
        latency_ms=round(latency_ms, 2),
    )


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        docs_url="/docs",
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
        # Сервис считается живым даже без Ollama:
        # в таком состоянии он способен вернуть fallback.
        return {"status": "ok"}

    @app.get(
        "/health/model",
        response_model=ModelHealth,
        tags=["health"],
    )
    async def model_health() -> ModelHealth:
        model_loaded = False

        try:
            async with httpx.AsyncClient(
                timeout=2.0,
                trust_env=False,
            ) as client:
                response = await client.get(
                    f"{settings.ollama_url.rstrip('/')}/api/tags"
                )
                response.raise_for_status()
                payload = response.json()

            model_names = {
                str(item.get("name") or item.get("model"))
                for item in payload.get("models", [])
                if isinstance(item, dict)
            }

            model_loaded = settings.ollama_model in model_names
        except Exception as exc:  # noqa: BLE001
            logger.warning("Ollama healthcheck не прошёл: %s", exc)

        return ModelHealth(
            model_loaded=model_loaded,
            model_version=settings.ollama_model,
            fallback_enabled=settings.fallback_enabled,
            supported_tasks=["process"],
        )

    @app.post(
        "/api/v1/process",
        response_model=ProcessResponse,
        tags=["ml"],
    )
    async def process_document(
        request: ProcessRequest,
    ) -> ProcessResponse:
        started = time.perf_counter()
        request_id = request.request_id

        source_anchors = anchors.extract(request.draft)

        try:
            schema = load_llm_schema()
        except RuntimeError as exc:
            logger.exception("Ошибка конфигурации ML-сервиса")

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(exc),
            ) from exc

        last_error: Exception | None = None

        async with httpx.AsyncClient(
            timeout=settings.ollama_timeout_seconds,
            trust_env=False,
        ) as client:
            for attempt in range(MAX_GENERATION_ATTEMPTS):
                try:
                    improved_text, requisites, changes = await generate_result(
                        client,
                        request=request,
                        schema=schema,
                        retry=attempt > 0,
                    )

                    result_anchors = anchors.extract(
                        build_guard_text(
                            improved_text,
                            requisites,
                        )
                    )

                    guard_result = fact_guard.check(
                        source_anchors,
                        result_anchors,
                    )

                    if guard_result.verdict == "blocked":
                        last_error = ValueError(
                            "Fact Guard обнаружил добавленные факты: "
                            + ", ".join(guard_result.added)
                        )

                        logger.warning(
                            "Fact Guard заблокировал ответ %s " "(попытка %s/%s): %s",
                            request_id,
                            attempt + 1,
                            MAX_GENERATION_ATTEMPTS,
                            guard_result.added,
                        )

                        continue

                    latency_ms = (time.perf_counter() - started) * 1000

                    logger.info(
                        "Запрос %s обработан за %.1f мс",
                        request_id,
                        latency_ms,
                    )

                    return create_process_response(
                        request_id=request_id,
                        improved_text=improved_text,
                        requisites=requisites,
                        changes=changes,
                        guard_result=guard_result,
                        is_fallback=False,
                        model_version=settings.ollama_model,
                        latency_ms=latency_ms,
                    )

                except Exception as exc:  # noqa: BLE001
                    last_error = exc

                    logger.warning(
                        "Ошибка обработки запроса %s " "(попытка %s/%s): %s",
                        request_id,
                        attempt + 1,
                        MAX_GENERATION_ATTEMPTS,
                        exc,
                    )

        if not settings.fallback_enabled:
            logger.error(
                "Запрос %s завершился ошибкой, fallback отключён: %s",
                request_id,
                last_error,
            )

            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Модель недоступна и fallback отключён",
            )

        logger.warning(
            "Для запроса %s активирован fallback: %s",
            request_id,
            last_error,
        )

        fallback_guard = build_fallback_guard(source_anchors)
        latency_ms = (time.perf_counter() - started) * 1000

        return create_process_response(
            request_id=request_id,
            improved_text=request.draft,
            requisites={key: None for key in request.requisite_keys},
            changes=[],
            guard_result=fallback_guard,
            is_fallback=True,
            model_version="fallback-1.0.0",
            latency_ms=latency_ms,
        )

    return app


app = create_app()
