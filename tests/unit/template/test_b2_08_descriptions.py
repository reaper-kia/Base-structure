from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from src.modules.templates.application.template_service import TemplateLoader

ASSETS = Path("src/modules/templates/assets")


@pytest.mark.parametrize("template_id", ["classic", "modern"])
def test_description_matches_rules(template_id: str) -> None:
    """Описание содержит фактические параметры из правил."""
    rules = yaml.safe_load((ASSETS / template_id / "rules.yaml").read_text(encoding="utf-8"))
    template = TemplateLoader(ASSETS).load(template_id)

    assert rules["font"]["family"] in template.description
    assert str(rules["font"]["size_pt"]) in template.description
    assert str(rules["page"]["left_mm"]) in template.description


def test_modern_description_mentions_table_classic_mentions_pages() -> None:
    """Modern упоминает таблицу-шапку, classic — нумерацию страниц."""
    modern = TemplateLoader(ASSETS).load("modern").description
    classic = TemplateLoader(ASSETS).load("classic").description

    assert "таблица-шапка" in modern
    assert "таблица-шапка" not in classic
    assert "нумерация страниц" in classic


def test_api_returns_honest_descriptions(monkeypatch) -> None:
    """API отдаёт честные описания, а не рукописные из rules.yaml."""
    from src.modules.templates.api import router as router_module
    monkeypatch.setattr(router_module, "_loader", TemplateLoader(ASSETS))
    from src.main import app

    entries = {t["id"]: t for t in TestClient(app).get("/api/templates").json()["templates"]}
    assert "Times New Roman" in entries["classic"]["description"]
    assert "Arial" in entries["modern"]["description"]