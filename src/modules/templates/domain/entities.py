from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Template:
    id: str
    name: str
    description: str
    rules: dict
    docx_path: Path | None
    available: bool = True
    fallback_used: bool = False
    fallback_reason: str | None = None
