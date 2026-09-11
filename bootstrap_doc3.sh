#!/usr/bin/env bash
# Перестройка Base_monolit_stucture_clean под кейс "Документ за 3 шага".
# Запуск из корня репозитория:  bash bootstrap_doc3.sh
set -euo pipefail

[ -f src/main.py ] && [ -d frontend/src ] || { echo "Запускай из корня репозитория"; exit 1; }

if git rev-parse --git-dir >/dev/null 2>&1; then
  git checkout -b chore/doc3-structure 2>/dev/null || echo "-> ветка уже существует, продолжаю"
else
  echo "-> git не инициализирован, работаю без ветки"
fi

echo "== 1/7 удаляю ненужное =="
rm -rf src/modules/auth src/modules/users
rm -rf tests/unit/auth tests/unit/users
rm -rf frontend/src/pages/map frontend/src/pages/login frontend/src/pages/admin
rm -rf frontend/src/features/auth frontend/public/data data/geo
rm -f migrations/versions/0001_initial_initial_schema.py

echo "== 2/7 чиню общие файлы =="

cat > src/shared/application/unit_of_work.py <<'EOF'
from typing import Protocol, Self

from src.modules.documents.application.ports.document_repository import (
    DocumentRepository,
)
from src.shared.outbox.application.repositories import OutboxRepository


class UnitOfWork(Protocol):
    """Единая транзакционная граница.

    Новый модуль -> добавить сюда атрибут с типом порта репозитория,
    а в SQLAlchemyUnitOfWork.__aenter__ - его создание.
    """

    documents: DocumentRepository
    outbox: OutboxRepository

    async def __aenter__(self) -> Self: ...

    async def __aexit__(self, exc_type, exc_value, traceback): ...

    async def commit(self): ...

    async def rollback(self): ...


class UnitOfWorkFactory(Protocol):
    def __call__(self) -> UnitOfWork: ...
EOF

cat > src/shared/infra/database/unit_of_work.py <<'EOF'
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.documents.infra.repositories import SQLAlchemyDocumentRepository
from src.shared.application.unit_of_work import UnitOfWork
from src.shared.outbox.infra.repositories import SQLAlchemyOutboxRepository


class SQLAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def __aenter__(self) -> Self:
        self.session = self._session_factory()
        self.documents = SQLAlchemyDocumentRepository(self.session)
        self.outbox = SQLAlchemyOutboxRepository(self.session)

        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        if exc_type is not None:
            await self.rollback()
        await self.session.close()

    async def commit(self):
        await self.session.commit()

    async def rollback(self):
        await self.session.rollback()

    async def flush(self) -> None:
        await self.session.flush()
EOF

python3 - <<'EOF'
import re, pathlib
p = pathlib.Path("migrations/env.py")
s = p.read_text(encoding="utf-8")
s = s.replace(
    "from src.modules.users.infra.models import UserModel",
    "from src.modules.documents.infra.models import DocumentModel",
)
p.write_text(s, encoding="utf-8")

p = pathlib.Path("tests/fakes.py")
s = p.read_text(encoding="utf-8")
s = s.replace("users: Any", "documents: Any").replace(
    "self.users = users", "self.documents = documents"
)
p.write_text(s, encoding="utf-8")
EOF

# чистим хвосты в Makefile и тестах UoW
python3 - <<'PYEOF'
import pathlib, re
mk = pathlib.Path("Makefile")
s = mk.read_text(encoding="utf-8")
s = s.replace(" admin ml-test", " ml-test")
s = re.sub(r"\n# Создать первого администратора\nadmin:\n\t.*\n", "\n", s)
mk.write_text(s, encoding="utf-8")

t = pathlib.Path("tests/unit/infra/test_uow.py")
if t.exists():
    s = t.read_text(encoding="utf-8")
    s = s.replace("users", "documents").replace("User", "Document")
    t.write_text(s, encoding="utf-8")
PYEOF

rm -f compose.admin.yml

cat > src/main.py <<'EOF'
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

# Новый модуль -> добавить сюда одну строку и один include_router ниже.
from src.core.config import settings
from src.modules.documents.api.router import router as documents_router
from src.modules.templates.api.router import router as templates_router
from src.shared.infra.database.health import check_database_connection
from src.shared.infra.database.session import get_async_session
from src.shared.infra.redis.client import close_redis_client
from src.shared.infra.redis.dependencies import get_redis_client
from src.shared.infra.redis.health import check_redis_connection


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    await close_redis_client()


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    app.add_middleware(  # type: ignore[call-arg]
        CORSMiddleware,  # type: ignore[arg-type]
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(documents_router)
    app.include_router(templates_router)

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "success"}

    @app.get("/health/db")
    async def database_health_check(
        session: AsyncSession = Depends(get_async_session),
    ) -> dict[str, str]:
        is_connected = await check_database_connection(session)
        return {"database": "ok" if is_connected else "error"}

    @app.get("/health/redis")
    async def redis_health_check(
        redis: Redis = Depends(get_redis_client),
    ) -> dict[str, str]:
        is_connected = await check_redis_connection(redis)
        return {"redis": "ok" if is_connected else "error"}

    return app


app = create_app()
EOF

cat > src/core/config.py <<'EOF'
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "doc3"
    app_env: str = "local"
    app_debug: bool = True

    postgres_host: str
    postgres_port: str
    postgres_db: str
    postgres_user: str
    postgres_password: str
    database_url: str

    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    redis_url: str = "redis://redis:6379/0"
    redis_key_prefix: str = "doc3"

    # Кэш результатов ИИ-обработки по хэшу черновика.
    cache_ttl_seconds: int = 600

    kafka_bootstrap_servers: str = "kafka:9093"
    kafka_client_id: str = "app"
    kafka_events_consumer_group: str = "app.events"
    kafka_events_topic: str = "app.events.v1"
    kafka_events_dlq_topic: str = "app.events.dlq.v1"
    kafka_consumer_max_attempts: int = 3
    kafka_consumer_retry_delay_seconds: float = 1.0
    outbox_publisher_batch_size: int = 100
    outbox_publisher_poll_interval_seconds: float = 1.0

    # Пустая строка = ИИ отключён. Бэкенд обязан пережить это (сценарий 6).
    ml_service_url: str = "http://ml_service:8100"
    ml_request_timeout_seconds: float = 90.0

    # Тумблер для демонстрации отказа ИИ.
    ai_force_failure: bool = False

    templates_dir: str = "src/modules/templates/assets"
    default_template_id: str = "classic"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()  # type: ignore[call-arg]
EOF

python3 - <<'EOF'
import pathlib, re
p = pathlib.Path(".env.example")
if p.exists():
    s = p.read_text(encoding="utf-8")
    s = "\n".join(
        l for l in s.splitlines()
        if not re.match(r"^\s*(JWT_|AUTH_|ADMIN_|ACCESS_TOKEN)", l)
    )
    s += "\n\nML_SERVICE_URL=http://ml_service:8100\nML_REQUEST_TIMEOUT_SECONDS=90\nAI_FORCE_FAILURE=false\n"
    p.write_text(s, encoding="utf-8")
EOF

echo "== 3/7 модуль documents =="
mkdir -p src/modules/documents/{api,domain,infra,config/doc_types} \
         src/modules/documents/application/{commands,handlers,ports,services}

find src/modules/documents -type d -exec touch {}/__init__.py \;

cat > src/modules/documents/domain/enums.py <<'EOF'
from enum import StrEnum


class DocType(StrEnum):
    MEMO = "memo"                # служебная записка
    REPORT = "report"            # докладная записка
    REFERENCE = "reference"      # информационная справка
    LETTER = "letter"            # письмо


class RequisiteStatus(StrEnum):
    FOUND_IN_DRAFT = "found_in_draft"
    USER_PROVIDED = "user_provided"
    AUTO_FILLED = "auto_filled"
    MISSING = "missing"


class DocumentStatus(StrEnum):
    CREATED = "created"
    PROCESSED = "processed"
    DEGRADED = "degraded"        # ИИ упал, сработал fallback
    FAILED = "failed"
EOF

cat > src/modules/documents/domain/entities.py <<'EOF'
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from src.modules.documents.domain.enums import (
    DocType,
    DocumentStatus,
    RequisiteStatus,
)


@dataclass
class Requisite:
    key: str
    label: str
    value: str | None
    status: RequisiteStatus
    required: bool


@dataclass
class Document:
    """Черновик пользователя и всё, что с ним сделала система.

    draft не перезаписывается никогда: сценарий 6 требует, чтобы после
    ошибки ИИ исходный текст остался на месте.
    """

    id: UUID = field(default_factory=uuid4)
    draft: str = ""
    doc_type: DocType = DocType.MEMO
    template_id: str = "classic"
    status: DocumentStatus = DocumentStatus.CREATED
    improved_text: str | None = None
    changes: list[dict] = field(default_factory=list)
    requisites: list[Requisite] = field(default_factory=list)
    fact_guard: dict | None = None
    error: dict | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
EOF

cat > src/modules/documents/domain/exceptions.py <<'EOF'
class DocumentNotFound(Exception):
    pass


class LLMUnavailable(Exception):
    """ИИ-компонент недоступен. Ловится в хэндлере, наружу не летит."""
EOF

cat > src/modules/documents/application/ports/llm_client.py <<'EOF'
from dataclasses import dataclass
from typing import Protocol


@dataclass
class LLMResult:
    improved_text: str
    requisites: dict[str, str | None]
    changes: list[dict]
    fact_guard: dict
    is_fallback: bool


class LLMClient(Protocol):
    """Граница с ml_service. Бэкенд не знает, что внутри."""

    async def process(self, draft: str, doc_type: str) -> LLMResult: ...
EOF

cat > src/modules/documents/application/ports/docx_renderer.py <<'EOF'
from typing import Protocol

from src.modules.documents.domain.entities import Requisite


class DocxRenderer(Protocol):
    """Граница с модулем templates. Оформление применяется программно."""

    def render(
        self,
        improved_text: str,
        requisites: list[Requisite],
        template_id: str,
    ) -> bytes: ...
EOF

cat > src/modules/documents/application/ports/document_repository.py <<'EOF'
from typing import Protocol
from uuid import UUID

from src.modules.documents.domain.entities import Document


class DocumentRepository(Protocol):
    async def add(self, document: Document) -> None: ...

    async def get(self, document_id: UUID) -> Document | None: ...

    async def update(self, document: Document) -> None: ...
EOF

cat > src/modules/documents/application/services/requisites_validator.py <<'EOF'
"""Проверка обязательных реквизитов.

Ничего не выдумывает: если значения нет, реквизит уходит со статусом
MISSING и в документе будет помечен явно.
"""

from datetime import date
from pathlib import Path

import yaml

from src.modules.documents.domain.entities import Requisite
from src.modules.documents.domain.enums import RequisiteStatus

_CONFIG_DIR = Path(__file__).resolve().parents[2] / "config" / "doc_types"


def load_doc_type(doc_type: str) -> dict:
    with (_CONFIG_DIR / f"{doc_type}.yaml").open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def validate(doc_type: str, extracted: dict[str, str | None]) -> list[Requisite]:
    schema = load_doc_type(doc_type)
    auto = schema.get("auto_fillable", {}) or {}
    result: list[Requisite] = []

    for item in schema["requisites"]:
        key, label = item["key"], item["label"]
        value = (extracted or {}).get(key) or None

        if value:
            status = RequisiteStatus.FOUND_IN_DRAFT
        elif key in auto:
            value = _auto_value(auto[key])
            status = RequisiteStatus.AUTO_FILLED
        else:
            status = RequisiteStatus.MISSING

        result.append(
            Requisite(
                key=key,
                label=label,
                value=value,
                status=status,
                required=item.get("required", True),
            )
        )
    return result


def _auto_value(rule: str) -> str | None:
    """Разрешено подставлять только то, что система знает достоверно."""
    if rule == "today":
        return date.today().strftime("%d.%m.%Y")
    return None
EOF

cat > src/modules/documents/config/doc_types/memo.yaml <<'EOF'
name: "Служебная записка"
structure_hint: "кому -> от кого -> суть -> просьба -> подпись"
requisites:
  - {key: addressee, label: "Адресат", required: true}
  - {key: author,    label: "Автор",   required: true}
  - {key: position,  label: "Должность автора", required: true}
  - {key: subject,   label: "Заголовок к тексту", required: true}
  - {key: doc_date,  label: "Дата документа", required: true}
auto_fillable:
  doc_date: today
EOF

cat > src/modules/documents/config/doc_types/report.yaml <<'EOF'
name: "Докладная записка"
structure_hint: "кому -> от кого -> изложение факта -> выводы -> предложения -> подпись"
requisites:
  - {key: addressee, label: "Адресат", required: true}
  - {key: author,    label: "Автор",   required: true}
  - {key: position,  label: "Должность автора", required: true}
  - {key: subject,   label: "Заголовок к тексту", required: true}
  - {key: doc_date,  label: "Дата документа", required: true}
auto_fillable:
  doc_date: today
EOF

cat > src/modules/documents/config/doc_types/reference.yaml <<'EOF'
name: "Информационная справка"
structure_hint: "заголовок -> период/основание -> изложение сведений -> подпись"
requisites:
  - {key: subject,   label: "Заголовок к тексту", required: true}
  - {key: author,    label: "Составитель", required: true}
  - {key: position,  label: "Должность составителя", required: true}
  - {key: doc_date,  label: "Дата документа", required: true}
  - {key: reg_number, label: "Регистрационный номер", required: false}
auto_fillable:
  doc_date: today
EOF

cat > src/modules/documents/config/doc_types/letter.yaml <<'EOF'
name: "Письмо"
structure_hint: "адресат -> обращение -> суть -> просьба -> подпись"
requisites:
  - {key: addressee,  label: "Адресат", required: true}
  - {key: salutation, label: "Обращение", required: false}
  - {key: subject,    label: "Заголовок к тексту", required: true}
  - {key: author,     label: "Подписант", required: true}
  - {key: position,   label: "Должность подписанта", required: true}
  - {key: doc_date,   label: "Дата документа", required: true}
  - {key: reg_number, label: "Регистрационный номер", required: false}
auto_fillable:
  doc_date: today
EOF

cat > src/modules/documents/infra/models.py <<'EOF'
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infra.database.base import Base


class DocumentModel(Base):
    __tablename__ = "documents"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    draft: Mapped[str] = mapped_column(Text)
    doc_type: Mapped[str] = mapped_column(String(32))
    template_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))
    improved_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    changes: Mapped[list | None] = mapped_column(JSON, nullable=True)
    requisites: Mapped[list | None] = mapped_column(JSON, nullable=True)
    fact_guard: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
EOF

cat > src/modules/documents/infra/repositories.py <<'EOF'
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.documents.domain.entities import Document
from src.modules.documents.infra.models import DocumentModel


class SQLAlchemyDocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, document: Document) -> None:
        self._session.add(_to_model(document))

    async def get(self, document_id: UUID) -> Document | None:
        stmt = select(DocumentModel).where(DocumentModel.id == document_id)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_domain(row) if row else None

    async def update(self, document: Document) -> None:
        await self._session.merge(_to_model(document))


def _to_model(doc: Document) -> DocumentModel:
    raise NotImplementedError("TODO(TL): маппинг Document -> DocumentModel")


def _to_domain(row: DocumentModel) -> Document:
    raise NotImplementedError("TODO(TL): маппинг DocumentModel -> Document")
EOF

cat > src/modules/documents/infra/llm_http_client.py <<'EOF'
"""HTTP-клиент в ml_service.

Любая сетевая проблема превращается в LLMUnavailable - выше по стеку
её ловит хэндлер и включает деградацию вместо падения.
"""

import httpx

from src.core.config import settings
from src.modules.documents.application.ports.llm_client import LLMResult
from src.modules.documents.domain.exceptions import LLMUnavailable


class HttpLLMClient:
    async def process(self, draft: str, doc_type: str) -> LLMResult:
        if settings.ai_force_failure or not settings.ml_service_url:
            raise LLMUnavailable("ИИ-компонент отключён")

        try:
            async with httpx.AsyncClient(
                timeout=settings.ml_request_timeout_seconds
            ) as client:
                response = await client.post(
                    f"{settings.ml_service_url}/api/v1/process",
                    json={"draft": draft, "doc_type": doc_type},
                )
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:  # noqa: BLE001
            raise LLMUnavailable(str(exc)) from exc

        return LLMResult(
            improved_text=payload["improved_text"],
            requisites=payload["requisites"],
            changes=payload.get("changes", []),
            fact_guard=payload.get("fact_guard", {}),
            is_fallback=payload.get("is_fallback", False),
        )
EOF

cat > src/modules/documents/infra/trace_store.py <<'EOF'
"""Журнал обработки для GET /api/trace/{id}.

Эксперту должно быть видно: что ушло в ИИ, что вернулось, что решил
Fact Guard, что решил валидатор. In-memory достаточно.
"""

from collections import defaultdict
from typing import Any
from uuid import UUID

_TRACES: dict[UUID, list[dict[str, Any]]] = defaultdict(list)


def record(document_id: UUID, stage: str, payload: Any) -> None:
    _TRACES[document_id].append({"stage": stage, "payload": payload})


def get(document_id: UUID) -> list[dict[str, Any]]:
    return _TRACES.get(document_id, [])
EOF

cat > src/modules/documents/api/schemas.py <<'EOF'
from uuid import UUID

from pydantic import BaseModel, Field


class CreateDocumentRequest(BaseModel):
    draft: str = Field(min_length=1, max_length=20000)
    doc_type: str
    template_id: str


class RequisiteSchema(BaseModel):
    key: str
    label: str
    value: str | None
    status: str
    required: bool


class DocumentResponse(BaseModel):
    id: UUID
    status: str
    draft: str
    improved_text: str | None = None
    changes: list[dict] = []
    requisites: list[RequisiteSchema] = []
    fact_guard: dict | None = None
    error: dict | None = None


class UpdateRequisitesRequest(BaseModel):
    values: dict[str, str | None]
EOF

cat > src/modules/documents/api/router.py <<'EOF'
from uuid import UUID

from fastapi import APIRouter

from src.modules.documents.api.schemas import (
    CreateDocumentRequest,
    DocumentResponse,
    UpdateRequisitesRequest,
)

router = APIRouter(prefix="/api", tags=["documents"])


@router.get("/doc-types")
async def list_doc_types() -> list[dict]:
    raise NotImplementedError("TODO(TL)")


@router.post("/documents", response_model=DocumentResponse)
async def create_document(payload: CreateDocumentRequest) -> DocumentResponse:
    raise NotImplementedError("TODO(TL)")


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: UUID) -> DocumentResponse:
    raise NotImplementedError("TODO(TL)")


@router.patch("/documents/{document_id}/requisites", response_model=DocumentResponse)
async def update_requisites(
    document_id: UUID, payload: UpdateRequisitesRequest
) -> DocumentResponse:
    raise NotImplementedError("TODO(TL)")


@router.post("/documents/{document_id}/render")
async def render_document(document_id: UUID):
    raise NotImplementedError("TODO(TL)")


@router.get("/trace/{document_id}")
async def get_trace(document_id: UUID) -> list[dict]:
    raise NotImplementedError("TODO(TL)")


@router.post("/dev/break-ai")
async def toggle_ai_failure(enabled: bool) -> dict:
    """Тумблер для сценария 6. Эксперт ломает ИИ своими руками."""
    raise NotImplementedError("TODO(TL)")
EOF

echo "== 4/7 модуль templates =="
mkdir -p src/modules/templates/{api,application,infra} \
         src/modules/templates/assets/{classic,modern}
find src/modules/templates -type d -not -path "*/assets*" -exec touch {}/__init__.py \;

cat > src/modules/templates/assets/classic/rules.yaml <<'EOF'
id: classic
name: "Классический"
description: "ГОСТ-подобное оформление для госорганизаций"
page: {top_mm: 20, bottom_mm: 20, left_mm: 30, right_mm: 15}
font: {family: "Times New Roman", size_pt: 14}
spacing: {line: 1.5, first_line_indent_cm: 1.25, space_after_pt: 0}
alignment: justify
header: {text: "", align: center}
footer: {page_numbers: true, align: center}
requisites_layout:
  - {key: addressee, position: top_right, bold: false}
  - {key: subject,   position: center,    bold: true}
  - {key: body,      position: body}
  - {key: position,  position: bottom_left}
  - {key: author,    position: bottom_right}
  - {key: doc_date,  position: bottom_left}
EOF

cat > src/modules/templates/assets/modern/rules.yaml <<'EOF'
id: modern
name: "Современный"
description: "Универсальное оформление, sans-serif, колонтитул с названием"
page: {top_mm: 15, bottom_mm: 15, left_mm: 25, right_mm: 20}
font: {family: "Arial", size_pt: 12}
spacing: {line: 1.15, first_line_indent_cm: 0, space_after_pt: 8}
alignment: left
header: {text: "ООО «Пример»", align: left}
footer: {page_numbers: true, align: right}
requisites_layout:
  - {key: subject,   position: top_left, bold: true}
  - {key: addressee, position: top_left, bold: false}
  - {key: body,      position: body}
  - {key: author,    position: bottom_left}
  - {key: position,  position: bottom_left}
  - {key: doc_date,  position: bottom_right}
EOF

cat > src/modules/templates/infra/template_loader.py <<'EOF'
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
EOF

cat > src/modules/templates/infra/docx_builder.py <<'EOF'
"""Программное оформление DOCX по правилам шаблона.

ИИ сюда не заглядывает: он отдал текст и реквизиты, дальше всё решает код.
"""

from docx.oxml.ns import qn
from docx.text.run import Run


def set_font(run: Run, family: str) -> None:
    """Кириллица в Word ломается, если шрифт прописан не во всех четырёх слотах."""
    run.font.name = family
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.get_or_add_rFonts()
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(attr), family)


def build(improved_text: str, requisites: list, rules: dict) -> bytes:
    raise NotImplementedError("TODO(B2)")
EOF

cat > src/modules/templates/application/renderer.py <<'EOF'
from src.modules.documents.domain.entities import Requisite


class TemplateDocxRenderer:
    """Реализация порта DocxRenderer из модуля documents."""

    def render(
        self,
        improved_text: str,
        requisites: list[Requisite],
        template_id: str,
    ) -> bytes:
        raise NotImplementedError("TODO(B2)")
EOF

cat > src/modules/templates/api/router.py <<'EOF'
from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["templates"])


@router.get("/templates")
async def list_templates() -> list[dict]:
    raise NotImplementedError("TODO(B2)")
EOF

echo "== 5/7 ml_service =="
mkdir -p ml_service/src/ml_service/{llm/prompts,guard}
find ml_service/src/ml_service/llm ml_service/src/ml_service/guard -type d -exec touch {}/__init__.py \;
rm -rf ml_service/training ml_service/src/ml_service/models
mkdir -p ml_service/tests/drafts

cat > ml_service/src/ml_service/llm/prompts/process.txt <<'EOF'
Ты — помощник делопроизводителя. Приводи текст к официально-деловому стилю.

ЗАПРЕЩЕНО добавлять сведения, которых нет в исходном тексте: даты, ФИО,
должности, номера, суммы, названия организаций. Если сведения нет —
ставь null. Выдумывать нельзя ни при каких условиях.

Тип документа: {doc_type_name}
Структура: {structure_hint}

Верни ТОЛЬКО JSON без пояснений и без markdown:
{{
  "improved_text": "...",
  "requisites": {{"addressee": null, "author": null, "position": null,
                  "subject": null, "doc_date": null}},
  "changes": [{{"type": "spelling|punctuation|style|structure",
                "from": "...", "to": "..."}}]
}}

Исходный текст:
{draft}
EOF

cat > ml_service/src/ml_service/guard/anchors.py <<'EOF'
"""Извлечение якорных сведений из черновика.

Регулярки дают 80% результата за 20% времени. NER (Natasha) можно
добавить сверху позже, если останется время.
"""

import re

PATTERNS: dict[str, str] = {
    "date": r"\b\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4}\b"
            r"|\b\d{1,2}\s+(?:январ|феврал|март|апрел|ма|июн|июл|"
            r"август|сентябр|октябр|ноябр|декабр)\w*\s*\d{0,4}",
    "amount": r"\b\d[\d\s]*(?:[.,]\d+)?\s*(?:руб|₽|тыс|млн|%|дней|"
              r"календарных|рабочих|часов|шт)\b",
    "fio": r"\b[А-ЯЁ][а-яё]+\s+[А-ЯЁ]\.\s?[А-ЯЁ]\.|"
           r"\b[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+(?:ович|евич|овна|евна|ична)\b",
    "number": r"№\s?\d+[\w/-]*",
    "org": r"«[^»]{2,60}»",
}


def extract(text: str) -> dict[str, list[str]]:
    return {
        kind: [m.group(0).strip() for m in re.finditer(pattern, text)]
        for kind, pattern in PATTERNS.items()
    }
EOF

cat > ml_service/src/ml_service/guard/fact_guard.py <<'EOF'
"""Детерминированная защита от галлюцинаций.

Сверяет якоря исходного текста с якорями результата. Промпт просит модель
не выдумывать, Fact Guard это проверяет.
"""

from dataclasses import dataclass, field


@dataclass
class GuardResult:
    preserved: list[str] = field(default_factory=list)
    lost: list[str] = field(default_factory=list)
    added: list[str] = field(default_factory=list)
    verdict: str = "clean"  # clean | warning | blocked

    def as_dict(self) -> dict:
        return {
            "preserved": self.preserved,
            "lost": self.lost,
            "added": self.added,
            "verdict": self.verdict,
        }


def check(source_anchors: dict, result_anchors: dict) -> GuardResult:
    raise NotImplementedError("TODO(ML)")
EOF

cat > ml_service/src/ml_service/schemas.py <<'EOF'
from pydantic import BaseModel, Field


class ProcessRequest(BaseModel):
    draft: str = Field(min_length=1, max_length=20000)
    doc_type: str


class ProcessResponse(BaseModel):
    improved_text: str
    requisites: dict[str, str | None]
    changes: list[dict] = []
    fact_guard: dict = {}
    is_fallback: bool = False
    model_version: str = "unknown"
    latency_ms: float = 0.0
EOF

echo "== 6/7 frontend =="
mkdir -p frontend/src/pages/wizard \
         frontend/src/features/{draft,doc-type,diff,requisites}

cat > frontend/src/app/router.tsx <<'EOF'
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { NotFoundPage } from '../pages/not-found/NotFoundPage';
import { WizardPage } from '../pages/wizard/WizardPage';
import { PublicLayout } from '../widgets/layout/PublicLayout';

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<PublicLayout />}>
          <Route path="/" element={<WizardPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
EOF

cat > frontend/src/pages/wizard/WizardPage.tsx <<'EOF'
export function WizardPage() {
  return <div>TODO(FE): мастер из четырёх шагов</div>;
}
EOF

cat > frontend/src/shared/api/documents.ts <<'EOF'
import { apiClient } from './client';

export type RequisiteStatus =
  | 'found_in_draft'
  | 'user_provided'
  | 'auto_filled'
  | 'missing';

export interface Requisite {
  key: string;
  label: string;
  value: string | null;
  status: RequisiteStatus;
  required: boolean;
}

export interface DocumentState {
  id: string;
  status: 'created' | 'processed' | 'degraded' | 'failed';
  draft: string;
  improved_text: string | null;
  changes: { type: string; from: string; to: string }[];
  requisites: Requisite[];
  fact_guard: { preserved: string[]; lost: string[]; added: string[]; verdict: string } | null;
  error: { code: string; message: string; recoverable: boolean } | null;
}

// Пока бэкенд не готов - переключить на моки одной строкой.
export const documentsApi = {
  docTypes: () => apiClient.get<{ id: string; name: string }[]>('/api/doc-types'),
  templates: () => apiClient.get<{ id: string; name: string; description: string }[]>('/api/templates'),
  create: (draft: string, docType: string, templateId: string) =>
    apiClient.post<DocumentState>('/api/documents', {
      draft,
      doc_type: docType,
      template_id: templateId,
    }),
  get: (id: string) => apiClient.get<DocumentState>(`/api/documents/${id}`),
  updateRequisites: (id: string, values: Record<string, string | null>) =>
    apiClient.patch<DocumentState>(`/api/documents/${id}/requisites`, { values }),
  renderUrl: (id: string) => `/api/documents/${id}/render`,
};
EOF

python3 - <<'EOF'
import json, pathlib
p = pathlib.Path("frontend/package.json")
pkg = json.loads(p.read_text(encoding="utf-8"))
for dep in ("maplibre-gl",):
    pkg.get("dependencies", {}).pop(dep, None)
pkg.get("devDependencies", {}).pop("@types/geojson", None)
p.write_text(json.dumps(pkg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
EOF

echo "== 7/7 зависимости и контракты =="
grep -q "python-docx" requirements.txt || cat >> requirements.txt <<'EOF'

# Генерация DOCX и чтение правил шаблона
python-docx==1.1.2
pyyaml==6.0.2
EOF

python3 - <<'EOF'
import re, pathlib
p = pathlib.Path("requirements.txt")
s = p.read_text(encoding="utf-8")
s = "\n".join(
    l for l in s.splitlines()
    if not re.match(r"^\s*(passlib|bcrypt|python-jose|email-validator)", l)
)
p.write_text(s.rstrip() + "\n", encoding="utf-8")
EOF

mkdir -p contracts
cat > contracts/README.md <<'EOF'
# Контракты

Правки только через тимлида. Пока файл не зафиксирован — логику по нему не пишем.

- `api.md` — REST-контракт бэкенда (TL + FE)
- `llm_schema.json` — что возвращает ml_service (ML + TL)
- `template_format.md` — формат rules.yaml (B2 + TL)

## Кто владеет чем

| Папка | Владелец |
|---|---|
| `src/modules/documents` | TL |
| `src/modules/templates` | B2 |
| `ml_service` | ML |
| `frontend/src` | FE |
| `frontend/src/app/styles` | UI -> FE |

Общие файлы (правит только TL): `src/main.py`, `src/core/config.py`,
`src/shared/**`, `migrations/env.py`, `docker-compose.yml`.
EOF

echo
echo "Готово. Дальше:"
echo "  1. make up"
echo "  2. make migration name=initial_documents && make migrate"
echo "  3. git add -A && git commit -m 'chore: структура под кейс Документ за 3 шага'"
