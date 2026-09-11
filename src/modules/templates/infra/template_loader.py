"""Загрузка шаблонов из assets/<id>/.

Если шаблон повреждён или отсутствует - возвращается запасной и
выставляется флаг fallback_used (требование п. 2.3 задания).
"""

from dataclasses import dataclass
from pathlib import Path

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
    # TL-07: contracts/template_format.md §2.7, шаг 3 - "выставляется
    # fallback_used = True и причина". Поля под саму причину не было -
    # добавил, application/renderer.py прокидывает его дальше в
    # RenderResult.template_fallback_reason для заголовка
    # X-Template-Fallback-Reason (contracts/api.md §4).
    fallback_reason: str | None = None


def list_templates() -> list[Template]:
    raise NotImplementedError("TODO(B2)")


def load(template_id: str) -> Template:
    raise NotImplementedError("TODO(B2)")
