"""Контракт модели и слой его починки — contracts/llm_contract.md §3 и §4.

Схема строится под конкретный список `requisite_keys` из запроса: сервис
ничего не знает про типы документов, но обязан гарантировать бэкенду, что в
`requisites` окажутся ровно эти ключи — ни больше, ни меньше (§2).
"""

from __future__ import annotations

import json
import re
from typing import Any

CHANGE_TYPES = ("spelling", "punctuation", "style", "structure")

# Срезаем markdown-ограждение и всё до первой «{» / после последней «}».
_FENCE_PATTERN = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)


def build_response_schema(requisite_keys: list[str]) -> dict[str, Any]:
    """JSON Schema для Ollama `format` — машиночитаемая версия §3."""
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "improved_text": {"type": "string", "minLength": 1},
            "requisites": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    key: {"type": ["string", "null"]} for key in requisite_keys
                },
                "required": list(requisite_keys),
            },
            "changes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "type": {"type": "string", "enum": list(CHANGE_TYPES)},
                        "from": {"type": "string"},
                        "to": {"type": "string"},
                    },
                    "required": ["type", "from", "to"],
                },
            },
        },
        "required": ["improved_text", "requisites"],
    }


def extract_json(raw: str) -> dict[str, Any] | None:
    """Дешёвая починка регуляркой — шаг перед вызовом модели (§4, шаг 2).

    Чаще всего модель просто обернула ответ в ```json ... ```: это ловится
    без второго похода в Ollama.
    """
    if not raw:
        return None

    candidate = _FENCE_PATTERN.sub("", raw.strip())

    try:
        parsed = json.loads(candidate)
    except (ValueError, TypeError):
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start == -1 or end <= start:
            return None
        try:
            parsed = json.loads(candidate[start : end + 1])
        except (ValueError, TypeError):
            return None

    return parsed if isinstance(parsed, dict) else None


def validate_llm_response(data: Any, expected_keys: list[str]) -> bool:
    """Жёсткая проверка формы ответа. Отсекает массивы вместо строк и мусор.

    Мягкие нарушения (лишний ключ, пропущенный ключ, пустая строка вместо
    null) здесь НЕ проверяются — их чинит `normalize_llm_response`
    (§3.2: это не повод уходить в fallback).
    """
    if not isinstance(data, dict):
        return False

    improved_text = data.get("improved_text")
    if not isinstance(improved_text, str) or not improved_text.strip():
        return False

    requisites = data.get("requisites")
    if not isinstance(requisites, dict):
        return False

    for key in expected_keys:
        if key in requisites:
            value = requisites[key]
            if value is not None and not isinstance(value, str):
                return False

    changes = data.get("changes", [])
    if changes is not None and not isinstance(changes, list):
        return False

    return True


def normalize_llm_response(
    data: dict[str, Any],
    expected_keys: list[str],
) -> dict[str, Any]:
    """Приводит ответ модели к гарантиям, которые сервис даёт бэкенду (§2).

    - в `requisites` ровно `expected_keys`: лишние выброшены, пропущенные
      добавлены со значением `null`;
    - пустая строка и строка из пробелов — это `null`, а не значение;
    - `changes` без нужных полей или с чужим `type` выбрасывается: это
      украшение, его потеря не ломает продукт (§3.2).
    """
    raw_requisites = data.get("requisites") or {}
    requisites: dict[str, str | None] = {}

    for key in expected_keys:
        value = raw_requisites.get(key) if isinstance(raw_requisites, dict) else None
        if isinstance(value, str):
            value = value.strip()
            # Модели любят отвечать «null»/«нет»/«-» строкой.
            if not value or value.lower() in {"null", "none", "нет", "-", "—"}:
                value = None
        elif value is not None:
            value = None
        requisites[key] = value

    changes: list[dict[str, str]] = []
    for item in data.get("changes") or []:
        if not isinstance(item, dict):
            continue
        change_type = item.get("type")
        if change_type not in CHANGE_TYPES:
            continue
        changes.append(
            {
                "type": change_type,
                "from": str(item.get("from", "")),
                "to": str(item.get("to", "")),
            }
        )

    return {
        "improved_text": str(data.get("improved_text", "")).strip(),
        "requisites": requisites,
        "changes": changes,
    }
