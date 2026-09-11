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
