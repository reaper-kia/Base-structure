"""Гейт качества модели — contracts/llm_contract.md §4.

Прогоняет черновики через ЖИВУЮ модель и считает долю ответов, которые
разобрались как валидный JSON без repair-прохода:

    ≥90%    — идём по плану
    70-90%  — repair обязателен, всё равно идём по плану
    <70%    — план Б: размеченный текст вместо JSON

Запуск (Ollama должна быть поднята и модель скачана):

    docker compose exec ml_service python scripts/gate.py
    # или локально:
    OLLAMA_URL=http://localhost:11434 python scripts/gate.py

Это не тест: в CI модели нет, и гейт туда не входит.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ml_service.guard import anchors, fact_guard  # noqa: E402
from ml_service.llm import schema as llm_schema  # noqa: E402
from ml_service.llm.ollama import (  # noqa: E402
    OllamaClient,
    OllamaUnavailableError,
    build_process_prompt,
)

DRAFTS_DIR = Path(__file__).resolve().parents[1] / "tests" / "drafts"
DEMO_DIR = Path(__file__).resolve().parents[2] / "data" / "demo-drafts"

REQUISITE_KEYS = [
    "addressee",
    "author",
    "position",
    "doc_date",
    "reg_number",
    "subject",
    "signature",
]


def collect_drafts() -> list[tuple[str, str]]:
    drafts = [
        (path.stem, path.read_text(encoding="utf-8"))
        for path in sorted(DRAFTS_DIR.glob("*.txt"))
    ]
    drafts += [
        (path.stem, path.read_text(encoding="utf-8"))
        for path in sorted(DEMO_DIR.glob("*.txt"))
    ]
    return drafts


async def main() -> int:
    client = OllamaClient()
    loaded, detail = await client.health()

    if not loaded:
        print(f"Модель недоступна: {detail}")
        return 2

    drafts = collect_drafts()
    schema = llm_schema.build_response_schema(REQUISITE_KEYS)

    valid_json = 0
    clean_guard = 0
    latencies: list[float] = []

    for name, draft in drafts:
        prompt = build_process_prompt(
            draft=draft,
            doc_type_name="Служебная записка",
            structure_hint="кому -> от кого -> суть -> просьба -> подпись",
            requisite_keys=REQUISITE_KEYS,
        )

        started = time.perf_counter()
        try:
            raw = await client.generate(prompt, schema)
        except OllamaUnavailableError as exc:
            print(f"{name:24} ОШИБКА  {exc}")
            continue
        latency = time.perf_counter() - started
        latencies.append(latency)

        parsed = llm_schema.extract_json(raw)
        is_valid = parsed is not None and llm_schema.validate_llm_response(
            parsed, REQUISITE_KEYS
        )

        verdict = "-"
        if is_valid:
            valid_json += 1
            normalized = llm_schema.normalize_llm_response(parsed, REQUISITE_KEYS)
            result_text = "\n".join(
                [
                    normalized["improved_text"],
                    *[v for v in normalized["requisites"].values() if v],
                ]
            )
            guard = fact_guard.check(
                anchors.extract(draft), anchors.extract(result_text), draft
            )
            verdict = guard.verdict
            if verdict == "clean":
                clean_guard += 1

        print(
            f"{name:24} json={'OK ' if is_valid else 'BAD'} "
            f"guard={verdict:8} {latency:5.1f}s"
        )

    total = len(drafts)
    rate = valid_json / total * 100 if total else 0.0
    average = sum(latencies) / len(latencies) if latencies else 0.0

    print()
    print(json.dumps(
        {
            "drafts": total,
            "valid_json_rate": round(rate, 1),
            "clean_guard_rate": round(clean_guard / total * 100, 1) if total else 0.0,
            "avg_latency_seconds": round(average, 2),
            "model": client.model,
        },
        ensure_ascii=False,
        indent=2,
    ))

    if rate >= 90:
        print("\n>= 90%: идём по плану.")
        return 0
    if rate >= 70:
        print("\n70-90%: repair-проход обязателен, идём по плану.")
        return 0

    print("\n< 70%: переходим на план Б (размеченный текст вместо JSON).")
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
