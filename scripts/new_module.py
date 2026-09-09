#!/usr/bin/env python3
"""Генератор скелета модуля.

Смотрит на src/modules/users как на образец соглашений (CQRS, dataclass-команды,
Protocol-порты, Mediator, _to_domain в репозитории) и создаёт новый модуль
в той же форме — с одним примерным command/handler на команду и на запрос,
чтобы новый файл сразу импортировался и было видно, куда дописывать реальную
логику.

Запуск:
    python scripts/new_module.py achievement
    # или через Makefile:
    make new-module NAME=achievement

После генерации СРУЧНО СДЕЛАТЬ РУКАМИ (скрипт не трогает эти файлы,
потому что они общие для всех модулей и конфликт правок дороже двух минут
ручной правки):

  1. src/main.py                                  -> app.include_router(...)
  2. src/shared/application/unit_of_work.py        -> добавить репозиторий в Protocol
  3. src/shared/infra/database/unit_of_work.py     -> создать репозиторий в __aenter__
  4. migrations/env.py                             -> импортировать новую ORM-модель
  5. make migration name=create_<module>_table && make migrate
"""

import sys
from pathlib import Path

TEMPLATES: dict[str, str] = {}


def register(path: str):
    def deco(fn):
        TEMPLATES[path] = fn()
        return fn
    return deco


def render(name: str, pascal: str) -> None:
    root = Path("src/modules") / name

    for rel, content in TEMPLATES.items():
        target = root / rel.format(name=name, pascal=pascal)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            print(f"  пропущено (уже есть): {target}")
            continue
        target.write_text(content.format(name=name, pascal=pascal))
        print(f"  создано: {target}")

    for pkg_dir in [
        root, root / "api", root / "application", root / "application/commands",
        root / "application/queries", root / "application/handlers",
        root / "application/ports", root / "domain", root / "infra",
    ]:
        init = pkg_dir / "__init__.py"
        if not init.exists():
            init.touch()


# ---------------------------------------------------------------------------
# domain

@register("domain/entities.py")
def _(): return '''from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass
class {pascal}:
    """TODO: замени поля на реальные атрибуты сущности."""

    name: str
    id: UUID = field(default_factory=uuid4)

    @classmethod
    def create(cls, name: str) -> "{pascal}":
        return cls(name=name)
'''

@register("domain/exceptions.py")
def _(): return '''class {pascal}NotFoundError(Exception):
    """Сущность {pascal} не найдена."""


class {pascal}AlreadyExistsError(Exception):
    """Нарушение уникальности при создании {pascal}."""
'''

@register("domain/value_objects.py")
def _(): return '''"""TODO: value objects модуля {name}.

Пример из users/domain/value_objects.py — Email, UserName, RawPassword:
неизменяемый dataclass с валидацией в __post_init__, бросает исключение
из domain/exceptions.py при нарушении инварианта.
"""
'''

# ---------------------------------------------------------------------------
# application: commands / queries / handlers / ports / read_models

@register("application/commands/create_{name}.py")
def _(): return '''from dataclasses import dataclass


@dataclass
class Create{pascal}Command:
    name: str
'''

@register("application/queries/get_{name}_by_id.py")
def _(): return '''from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class Get{pascal}ByIdQuery:
    id: UUID
'''

@register("application/read_models.py")
def _(): return '''from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class {pascal}ReadModel:
    id: UUID
    name: str
'''

@register("application/ports/{name}_repository.py")
def _(): return '''from typing import Protocol
from uuid import UUID

from src.modules.{name}.application.read_models import {pascal}ReadModel
from src.modules.{name}.domain.entities import {pascal}


class {pascal}Repository(Protocol):
    async def get_by_id(self, id: UUID) -> {pascal} | None: ...

    async def add(self, entity: {pascal}) -> None: ...


class {pascal}ReadRepository(Protocol):
    async def get_by_id(self, id: UUID) -> {pascal}ReadModel | None: ...
'''

@register("application/handlers/create_{name}.py")
def _(): return '''from dataclasses import dataclass

from src.modules.{name}.application.commands.create_{name} import Create{pascal}Command
from src.modules.{name}.domain.entities import {pascal}
from src.shared.application.unit_of_work import UnitOfWorkFactory


@dataclass
class Create{pascal}CommandHandler:
    uow_factory: UnitOfWorkFactory

    async def handle(self, cmd: Create{pascal}Command) -> {pascal}:
        entity = {pascal}.create(name=cmd.name)

        async with self.uow_factory() as uow:
            # TODO: заменить uow.{name} на реальное имя атрибута,
            # которое ты добавишь в UnitOfWork (см. подсказку после генерации)
            await uow.{name}.add(entity)
            await uow.commit()

        return entity
'''

@register("application/handlers/get_{name}_by_id.py")
def _(): return '''from dataclasses import dataclass

from src.modules.{name}.application.ports.{name}_repository import {pascal}ReadRepository
from src.modules.{name}.application.queries.get_{name}_by_id import Get{pascal}ByIdQuery
from src.modules.{name}.domain.exceptions import {pascal}NotFoundError


@dataclass
class Get{pascal}ByIdQueryHandler:
    {name}_read_repository: {pascal}ReadRepository

    async def handle(self, query: Get{pascal}ByIdQuery):
        result = await self.{name}_read_repository.get_by_id(query.id)

        if result is None:
            raise {pascal}NotFoundError(f"{pascal} {{query.id}} not found")

        return result
'''

# ---------------------------------------------------------------------------
# infra

@register("infra/models.py")
def _(): return '''import uuid

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infra.database.base import Base


class {pascal}Model(Base):
    __tablename__ = "{name}s"
    # TODO: если модуль живёт в отдельной схеме - __table_args__ = {{"schema": "..."}}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
'''

@register("infra/repositories.py")
def _(): return '''from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.{name}.application.ports.{name}_repository import (
    {pascal}ReadRepository,
    {pascal}Repository,
)
from src.modules.{name}.application.read_models import {pascal}ReadModel
from src.modules.{name}.domain.entities import {pascal}
from src.modules.{name}.infra.models import {pascal}Model


class SQLAlchemy{pascal}Repository({pascal}Repository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, id: UUID) -> {pascal} | None:
        stmt = select({pascal}Model).where({pascal}Model.id == id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def add(self, entity: {pascal}) -> None:
        self.session.add({pascal}Model(id=entity.id, name=entity.name))

    @staticmethod
    def _to_domain(model: {pascal}Model) -> {pascal}:
        return {pascal}(id=model.id, name=model.name)


class SQLAlchemy{pascal}ReadRepository({pascal}ReadRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, id: UUID) -> {pascal}ReadModel | None:
        stmt = select({pascal}Model.id, {pascal}Model.name).where({pascal}Model.id == id)
        result = await self.session.execute(stmt)
        row = result.one_or_none()
        return {pascal}ReadModel(id=row.id, name=row.name) if row else None
'''

# ---------------------------------------------------------------------------
# api

@register("api/schemas.py")
def _(): return '''from uuid import UUID

from pydantic import BaseModel, Field


class Create{pascal}Request(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class {pascal}Response(BaseModel):
    id: UUID
    name: str
'''

@register("api/dependencies.py")
def _(): return '''from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.{name}.application.commands.create_{name} import Create{pascal}Command
from src.modules.{name}.application.handlers.create_{name} import (
    Create{pascal}CommandHandler,
)
from src.modules.{name}.application.handlers.get_{name}_by_id import (
    Get{pascal}ByIdQueryHandler,
)
from src.modules.{name}.application.ports.{name}_repository import (
    {pascal}ReadRepository,
)
from src.modules.{name}.application.queries.get_{name}_by_id import Get{pascal}ByIdQuery
from src.modules.{name}.infra.repositories import SQLAlchemy{pascal}ReadRepository
from src.shared.api.dependencies import get_unit_of_work_factory
from src.shared.application.mediator import Mediator
from src.shared.application.unit_of_work import UnitOfWorkFactory
from src.shared.infra.database.session import get_async_session


def get_{name}_read_repository(
    session: AsyncSession = Depends(get_async_session),
) -> {pascal}ReadRepository:
    return SQLAlchemy{pascal}ReadRepository(session)


def get_create_{name}_handler(
    uow_factory: UnitOfWorkFactory = Depends(get_unit_of_work_factory),
) -> Create{pascal}CommandHandler:
    return Create{pascal}CommandHandler(uow_factory=uow_factory)


def get_{name}_by_id_handler(
    repo: {pascal}ReadRepository = Depends(get_{name}_read_repository),
) -> Get{pascal}ByIdQueryHandler:
    return Get{pascal}ByIdQueryHandler({name}_read_repository=repo)


def get_mediator(
    create_handler: Create{pascal}CommandHandler = Depends(get_create_{name}_handler),
    by_id_handler: Get{pascal}ByIdQueryHandler = Depends(get_{name}_by_id_handler),
) -> Mediator:
    mediator = Mediator()
    mediator.register(Create{pascal}Command, create_handler)
    mediator.register(Get{pascal}ByIdQuery, by_id_handler)
    return mediator
'''

@register("api/router.py")
def _(): return '''from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from src.modules.{name}.api.dependencies import get_mediator
from src.modules.{name}.api.schemas import Create{pascal}Request, {pascal}Response
from src.modules.{name}.application.commands.create_{name} import Create{pascal}Command
from src.modules.{name}.application.queries.get_{name}_by_id import Get{pascal}ByIdQuery
from src.modules.{name}.domain.exceptions import {pascal}NotFoundError
from src.shared.application.mediator import Mediator

router = APIRouter(prefix="/{name}s", tags=["{pascal}"])


@router.post("", response_model={pascal}Response, status_code=status.HTTP_201_CREATED)
async def create_{name}(
    request: Create{pascal}Request,
    mediator: Mediator = Depends(get_mediator),
) -> {pascal}Response:
    entity = await mediator.send(Create{pascal}Command(name=request.name))
    return {pascal}Response(id=entity.id, name=entity.name)


@router.get("/{{{name}_id}}", response_model={pascal}Response)
async def get_{name}(
    {name}_id: UUID,
    mediator: Mediator = Depends(get_mediator),
) -> {pascal}Response:
    try:
        result = await mediator.send(Get{pascal}ByIdQuery(id={name}_id))
    except {pascal}NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {pascal}Response(id=result.id, name=result.name)
'''


def main() -> None:
    if len(sys.argv) != 2:
        print("Использование: python scripts/new_module.py <name>")
        print("<name> — снейк-кейс, единственное число: achievement, retention_case")
        sys.exit(1)

    name = sys.argv[1].strip().lower()
    if not name.isidentifier():
        print(f"'{name}' — не валидное имя python-модуля")
        sys.exit(1)

    pascal = "".join(part.capitalize() for part in name.split("_"))

    print(f"Генерирую модуль '{name}' (сущность {pascal})...\n")
    render(name, pascal)

    print(f"""
Готово. Дальше руками:

  1. src/main.py:
       from src.modules.{name}.api.router import router as {name}_router
       app.include_router({name}_router)

  2. src/shared/application/unit_of_work.py — в Protocol UnitOfWork добавь:
       {name}: {pascal}Repository

  3. src/shared/infra/database/unit_of_work.py — в __aenter__ добавь:
       self.{name} = SQLAlchemy{pascal}Repository(self.session)

  4. migrations/env.py — допиши импорт:
       from src.modules.{name}.infra.models import {pascal}Model

  5. make migration name=create_{name}s_table
     make migrate
""")


if __name__ == "__main__":
    main()