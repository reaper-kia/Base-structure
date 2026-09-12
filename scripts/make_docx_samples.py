"""Генерирует 8 эталонных DOCX (4 типа × 2 шаблона) в artifacts/ — демо для защиты."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml  # noqa: E402

from src.modules.documents.domain.entities import (  # noqa: E402
    Requisite,
    RequisiteStatus,
)
from src.modules.templates.infra.docx_renderer import TemplateDocxRenderer  # noqa: E402

DOC_TYPES_DIR = Path("src/modules/documents/config/doc_types")
ASSETS = Path("src/modules/templates/assets")

DEMO_VALUES = {
    "addressee": "Генеральному директору ООО «Вектор» Иванову И. И.",
    "doc_date": "13.09.2026",
    "reg_number": "№ 42-ИСХ",
    "salutation": "Уважаемый Иван Иванович!",
    "subject": "О проведении инвентаризации",
    "author": "Петрова А. А.",
    "position": "Главный бухгалтер",
    "signature": "________________",
    "executor": "Сидорова В. В., тел. 123",
}
DEMO_BODY = (
    "В связи с окончанием финансового года прошу провести полную инвентаризацию "
    "товарно-материальных ценностей на всех складах предприятия. Результаты "
    "оформить актом и передать в бухгалтерию до 31 декабря.\n\n"
    "Контроль за проведением оставляю за собой."
)


def generate_samples(out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    renderer = TemplateDocxRenderer(ASSETS)
    written: list[Path] = []

    for spec_path in sorted(DOC_TYPES_DIR.glob("*.yaml")):
        spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
        reqs = [
            Requisite(
                key=r["key"],
                label=r.get("label", r["key"]),
                value=DEMO_VALUES.get(
                    r["key"], f"Значение «{r.get('label', r['key'])}»"
                ),
                status=RequisiteStatus.USER_PROVIDED,
                required=bool(r.get("required")),
            )
            for r in spec.get("requisites", [])
        ]
        for template_id in ("classic", "modern"):
            data = renderer.render(DEMO_BODY, reqs, template_id)
            path = out_dir / f"{spec_path.stem}__{template_id}.docx"
            path.write_bytes(data)
            written.append(path)

    return written


if __name__ == "__main__":
    files = generate_samples(Path("artifacts"))
    print(f"Создано {len(files)} файлов:")
    for f in files:
        print(" -", f)
