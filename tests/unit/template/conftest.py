from __future__ import annotations

import shutil
from pathlib import Path

import pytest

ASSETS = Path("src/modules/templates/assets")


@pytest.fixture(autouse=True)
def cleanup_uploaded_templates():
    """Убирает шаблоны, созданные тестами (и в assets/, и в каталоге загрузок)."""
    from src.modules.templates.api import router as router_module

    watched = (router_module.ASSETS_DIR, router_module.UPLOADED_DIR)
    snapshot = {
        (directory, entry.name)
        for directory in watched
        if directory.exists()
        for entry in directory.iterdir()
        if entry.is_dir()
    }
    yield
    for directory in watched:
        if not directory.exists():
            continue
        for entry in directory.iterdir():
            if entry.is_dir() and (directory, entry.name) not in snapshot:
                shutil.rmtree(entry, ignore_errors=True)
