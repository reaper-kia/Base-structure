from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.modules.documents.domain.exceptions import DocTypeNotFound


class RequisiteSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    key: str = Field(min_length=1)
    label: str = Field(min_length=1)
    required: bool


class DocTypeSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    structure_hint: str = Field(min_length=1)
    # Печатать ли название типа отдельной строкой над заголовком.
    # Оформление берётся из шаблона, а вот сам факт наличия такой строки —
    # свойство типа документа: у письма её нет.
    show_type_title: bool = True
    requisites: list[RequisiteSpec] = Field(min_length=1)
    auto_fillable: dict[str, str] = Field(default_factory=dict)


_DOC_TYPE_ORDER = ("memo", "report", "reference", "letter")

_CONFIG_DIR = Path(__file__).resolve().parents[2] / "config" / "doc_types"


def _read_yaml(doc_type: str) -> dict[str, Any]:
    path = _CONFIG_DIR / f"{doc_type}.yaml"

    try:
        with path.open(encoding="utf-8") as file:
            payload = yaml.safe_load(file)
    except (OSError, yaml.YAMLError) as exc:
        raise RuntimeError(f"Не удалось прочитать конфиг {path}") from exc

    if not isinstance(payload, dict):
        raise TypeError(f"Конфиг {path} должен содержать YAML-объект")

    return payload


def _load_doc_types() -> list[DocTypeSpec]:
    specs: list[DocTypeSpec] = []

    for doc_type in _DOC_TYPE_ORDER:
        path = _CONFIG_DIR / f"{doc_type}.yaml"

        try:
            spec = DocTypeSpec.model_validate(
                {
                    "id": doc_type,
                    **_read_yaml(doc_type),
                }
            )
        except ValidationError as exc:
            raise RuntimeError(f"Некорректный конфиг типа документа: {path}") from exc

        specs.append(spec)

    return specs


# YAML читаются сразу при импорте приложения.
# Если какой-то конфиг неправильный, приложение не запустится.
_DOC_TYPES = _load_doc_types()

_DOC_TYPES_BY_ID = {spec.id: spec for spec in _DOC_TYPES}


def list_doc_types() -> list[DocTypeSpec]:
    return list(_DOC_TYPES)


def get_doc_type(doc_type: str) -> DocTypeSpec:
    try:
        return _DOC_TYPES_BY_ID[doc_type]
    except KeyError as exc:
        raise DocTypeNotFound(doc_type) from exc
