"""Загрузка шаблонов из assets/<id>/.

Если шаблон повреждён или отсутствует - возвращается запасной и
выставляется флаг fallback_used (требование п. 2.3 задания).
"""

from dataclasses import dataclass
from pathlib import Path

import yaml

from src.core.config import settings

ASSETS = Path(settings.templates_dir)


@dataclass
class Template:
    id: str
    name: str
    description: str
    rules: dict
    docx_path: Path | None
    fallback_used: bool = False


def list_templates() -> list[Template]:
    raise NotImplementedError("TODO(B2)")


def load(template_id: str) -> Template:
    raise NotImplementedError("TODO(B2)")
