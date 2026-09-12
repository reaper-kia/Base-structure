from __future__ import annotations

import shutil
from pathlib import Path

import pytest

ASSETS = Path("src/modules/templates/assets")


@pytest.fixture(autouse=True)
def cleanup_uploaded_templates():
    """Убирает шаблоны, созданные тестами upload-эндпоинта (id вида classic-1, classic-2, ...)."""
    snapshot = {p.name for p in ASSETS.iterdir() if p.is_dir()}
    yield
    for entry in ASSETS.iterdir():
        if entry.is_dir() and entry.name not in snapshot:
            shutil.rmtree(entry, ignore_errors=True)
