"""Тонкий клиент Ollama и сборка промптов.

Единственное место, которое знает, как именно вызывается модель. Замена
Ollama на внешний API — правка этого файла; HTTP-контракт из
contracts/llm_contract.md §2 при этом не меняется, и бэкенд ничего не
заметит. Ради этого ml_service и вынесен в отдельный контейнер (§1).
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

import httpx

from ml_service.config import settings

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
_PLACEHOLDER = re.compile(r"<<([A-Z_]+)>>")


class OllamaUnavailableError(RuntimeError):
    """Модель не ответила: сеть, таймаут или не-200."""


def _read_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


def _fill(template: str, **values: str) -> str:
    """Подстановка по <<ИМЯ>>.

    Намеренно не str.format: в промпте живут примеры JSON, и каждая фигурная
    скобка в них пришлось бы экранировать — ровно тот класс ошибок, который
    ломает промпт молча.
    """
    # Один проход важен для изоляции: текст из базы знаний, содержащий
    # строку вроде <<DRAFT>>, не должен запустить повторную подстановку.
    return _PLACEHOLDER.sub(
        lambda match: values.get(match.group(1), match.group(0)),
        template,
    )


def response_skeleton(requisite_keys: list[str]) -> str:
    """Скелет ответа с нужными ключами — блок 4 промпта (§3.1)."""
    return json.dumps(
        {
            "improved_text": "исправленный текст",
            "requisites": dict.fromkeys(requisite_keys),
            "changes": [{"type": "style", "from": "было", "to": "стало"}],
        },
        ensure_ascii=False,
    )


def _example_response(
    requisite_keys: list[str],
    *,
    include_addressee: bool,
) -> str:
    """Few-shot пример, согласованный с ключами конкретного документа."""

    requisites: dict[str, str | None] = dict.fromkeys(requisite_keys)

    if include_addressee and "addressee" in requisites:
        requisites["addressee"] = "Генеральному директору ООО «Ромашка» Иванову И.И."

    if "author" in requisites:
        requisites["author"] = (
            "Петров П.П."
            if "position" in requisites
            else "Начальник отдела аналитики Петров П.П."
        )
    if "position" in requisites:
        requisites["position"] = "Начальник отдела аналитики"

    return json.dumps(
        {
            "improved_text": (
                "Прошу рассмотреть возможность выделения средств на закупку "
                "трёх компьютеров стоимостью 180 000 рублей."
            ),
            "requisites": requisites,
            "changes": [],
        },
        ensure_ascii=False,
    )


def build_process_prompt(
    *,
    draft: str,
    doc_type_name: str,
    structure_hint: str,
    requisite_keys: list[str],
    knowledge_context: str = "",
) -> str:
    return _fill(
        _read_prompt("process.txt"),
        DOC_TYPE_NAME=doc_type_name,
        STRUCTURE_HINT=structure_hint,
        RESPONSE_SKELETON=response_skeleton(requisite_keys),
        EXAMPLE_WITH_ADDRESSEE=_example_response(
            requisite_keys,
            include_addressee=True,
        ),
        EXAMPLE_WITHOUT_ADDRESSEE=_example_response(
            requisite_keys,
            include_addressee=False,
        ),
        KNOWLEDGE_CONTEXT=(
            knowledge_context or "Релевантные справочные фрагменты не найдены."
        ),
        DRAFT=draft,
    )


def build_repair_prompt(broken: str, requisite_keys: list[str]) -> str:
    return _fill(
        _read_prompt("repair.txt"),
        RESPONSE_SKELETON=response_skeleton(requisite_keys),
        BROKEN=broken,
    )


class OllamaClient:
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self._base_url = (base_url or settings.ollama_url).rstrip("/")
        self._model = model or settings.ollama_model

    @property
    def model(self) -> str:
        return self._model

    async def generate(
        self,
        prompt: str,
        response_schema: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> str:
        """Один вызов модели. Возвращает сырой текст ответа."""
        payload: dict[str, Any] = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": settings.ollama_temperature},
        }
        if response_schema is not None:
            payload["format"] = response_schema

        try:
            async with httpx.AsyncClient(
                timeout=timeout or settings.ollama_timeout_seconds
            ) as client:
                response = await client.post(
                    f"{self._base_url}/api/generate", json=payload
                )
        except httpx.HTTPError as exc:
            raise OllamaUnavailableError(str(exc)) from exc

        if response.status_code != 200:
            raise OllamaUnavailableError(
                f"Ollama ответила {response.status_code}: {response.text[:200]}"
            )

        try:
            return str(response.json()["response"])
        except (ValueError, KeyError, TypeError) as exc:
            raise OllamaUnavailableError(f"Неожиданный ответ Ollama: {exc}") from exc

    async def list_models(self) -> list[str]:
        """Имена загруженных моделей. Пустой список = модели нет."""
        try:
            async with httpx.AsyncClient(
                timeout=settings.ollama_health_timeout_seconds
            ) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise OllamaUnavailableError(str(exc)) from exc

        return [str(item.get("name", "")) for item in payload.get("models", [])]

    async def health(self) -> tuple[bool, str | None]:
        """(модель готова, причина если нет) — для GET /health/model."""
        try:
            models = await self.list_models()
        except OllamaUnavailableError as exc:
            return False, f"Ollama недоступна: {exc}"

        # Ollama возвращает имя с тегом: qwen2.5:7b-instruct.
        # Совпадение по префиксу переживает «latest» и уточнённые теги.
        if any(name == self._model or name.startswith(self._model) for name in models):
            return True, None

        return False, (
            f"Модель «{self._model}» не загружена. "
            f"Доступны: {', '.join(models) or 'ничего'}. "
            f"Выполните: make pull-model"
        )
