from collections.abc import Callable
from uuid import UUID

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.users.application.queries.get_user_by_id import GetUserByIdQuery
from src.modules.auth.api.actor import RequestActor
from src.core.config import settings
from src.modules.auth.application.commands.login_user import LoginUserCommand
from src.modules.auth.application.exceptions import InvalidTokenError
from src.modules.auth.application.handlers.login_user import LoginUserCommandHandler
from src.modules.auth.application.ports.auth_user_repository import AuthUserRepository
from src.modules.auth.application.ports.token_service import TokenService
from src.modules.auth.infra.jwt_token_service import JwtTokenService
from src.modules.auth.infra.repositories import SQLAlchemyAuthUserRepository
from src.modules.users.api.dependencies import (
    get_password_hasher,
)
from src.modules.users.api.dependencies import (
    get_mediator as get_users_mediator,
)
from src.modules.users.application.ports.password_hasher import PasswordHasher
from src.modules.users.domain.enums import Role
from src.shared.application.mediator import Mediator

from src.shared.infra.database.session import get_async_session


def get_auth_user_repository(
    session: AsyncSession = Depends(get_async_session),
) -> AuthUserRepository:
    return SQLAlchemyAuthUserRepository(session)


def get_token_service() -> TokenService:
    return JwtTokenService()


def get_login_user_handler(
    auth_user_repository: AuthUserRepository = Depends(get_auth_user_repository),
    password_hasher: PasswordHasher = Depends(get_password_hasher),
    token_service: TokenService = Depends(get_token_service),
) -> LoginUserCommandHandler:
    return LoginUserCommandHandler(
        auth_user_repository=auth_user_repository,
        password_hasher=password_hasher,
        token_service=token_service,
    )


def get_auth_mediator(
    login_user_handler: LoginUserCommandHandler = Depends(get_login_user_handler),
) -> Mediator:
    mediator = Mediator()
    mediator.register(LoginUserCommand, login_user_handler)
    return mediator


def get_current_user_id(
    access_token: str | None = Cookie(
        default=None,
        alias=settings.auth_access_cookie_name,
    ),
    token_service: TokenService = Depends(get_token_service),
) -> UUID:
    if access_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        return token_service.decode_access_token(access_token)
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc


async def get_current_actor(
    user_id: UUID = Depends(get_current_user_id),
    mediator: Mediator = Depends(get_users_mediator),
) -> RequestActor:
    user = await mediator.send(GetUserByIdQuery(id=user_id))
    return RequestActor(
        user_id=user.id,
        role=Role(user.role),
        name=user.name,
    )


def require_roles(*allowed: Role) -> Callable:
    """Фабрика зависимостей. Использование:

        @router.get("/x", dependencies=[Depends(require_roles(Role.NETWORK_ADMIN))])

    или, если нужен сам актор внутри обработчика:

        async def handler(actor: RequestActor = Depends(require_roles(Role.CLIENT))):
    """

    async def _check(
        actor: RequestActor = Depends(get_current_actor),
    ) -> RequestActor:
        if actor.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="ACCESS_DENIED",
            )
        return actor

    return _check
