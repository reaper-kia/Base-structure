"""Пересобирает демонстрационные черновики фронта из стартового пакета.

Один источник правды на всё: `data/demo-drafts/*.txt` — это файлы
организаторов из `docs/organizer-materials/Черновики/`, они же используются
в тестах. Кнопки на экране ввода собираются отсюда, а не копируются руками,
иначе демо и тесты неизбежно разъезжаются.

    python scripts/sync_demo_drafts.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRAFTS_DIR = ROOT / "data" / "demo-drafts"
TARGET = ROOT / "frontend" / "src" / "shared" / "api" / "demoDrafts.ts"

# Подборка охватывает все четыре типа документов и все обязательные
# сценарии проверки: чистый вход, ошибки и просторечия, пропущенный
# реквизит, свободная форма с фактами.
PICKS: tuple[tuple[str, str, str, str], ...] = (
    (
        "memo_1",
        "memo",
        "Чистый черновик",
        "Служебная записка со всеми реквизитами — базовый путь до DOCX",
    ),
    (
        "memo_2",
        "memo",
        "С ошибками и просторечиями",
        "Тот же документ, но «Здрасьте», «компы» и «вообщем» — сценарий 2",
    ),
    (
        "memo_3",
        "memo",
        "Без адресата",
        "Обязательный реквизит пропущен — сценарий 3",
    ),
    (
        "memo_4",
        "memo",
        "Свободная форма",
        "Сплошной текст без меток: суммы, даты и условия должны уцелеть — сценарий 4",
    ),
    (
        "report_1",
        "report",
        "Докладная записка",
        "Другой тип документа со своим набором реквизитов",
    ),
    (
        "reference_1",
        "reference",
        "Информационная справка",
        "У справки нет адресата и номера — структура отличается",
    ),
    (
        "letter_4",
        "letter",
        "Письмо",
        "Свободная форма, тип с темой и обращением",
    ),
)

HEADER = """// Демонстрационные черновики.
//
// Взяты без изменений из стартового пакета организаторов:
// docs/organizer-materials/Черновики/. Те же файлы лежат в data/demo-drafts/
// и используются в тестах — один источник для демо и для проверок.
//
// Файл сгенерирован скриптом scripts/sync_demo_drafts.py, править руками не нужно.

export interface DemoDraft {
  id: string;
  label: string;
  hint: string;
  docType: string;
  text: string;
}

export const DEMO_DRAFTS: DemoDraft[] = [
"""


def main() -> None:
    lines = [HEADER.rstrip("\n")]

    for name, doc_type, label, hint in PICKS:
        text = (DRAFTS_DIR / f"{name}.txt").read_text(encoding="utf-8").rstrip()
        lines.append("  {")
        lines.append(f"    id: {json.dumps(name)},")
        lines.append(f"    label: {json.dumps(label, ensure_ascii=False)},")
        lines.append(f"    hint: {json.dumps(hint, ensure_ascii=False)},")
        lines.append(f"    docType: {json.dumps(doc_type)},")
        lines.append(f"    text: {json.dumps(text, ensure_ascii=False)},")
        lines.append("  },")

    lines.append("];")
    lines.append("")

    TARGET.write_text("\n".join(lines), encoding="utf-8")
    print(f"Обновлено: {TARGET.relative_to(ROOT)} ({len(PICKS)} черновиков)")


if __name__ == "__main__":
    main()
