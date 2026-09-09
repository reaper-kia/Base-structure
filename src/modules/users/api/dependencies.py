from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.users.application.commands.register_user import RegisterUserCommand
from src.modules.users.application.handlers.get_user_by_id import (
    GetUserByIdQueryHandler,
)

# к импортам
from src.modules.users.application.commands.create_manager import CreateManagerCommand
from src.modules.users.application.handlers.create_manager import (
    CreateManagerCommandHandler,
)
from src.modules.users.application.handlers.register_user import (
    RegisterUserCommandHandler,
)
from src.modules.users.application.ports.password_hasher import PasswordHasher
from src.modules.users.application.ports.user_repository import (
    UserReadRepository,
    UserRepository,
)
from src.modules.users.application.queries.get_user_by_id import GetUserByIdQuery
from src.modules.users.infra.password_hasher import BcryptPasswordHasher
from src.modules.users.infra.repositories import (
    SQLAlchemyUserReadRepository,
    SQLAlchemyUserRepository,
)
from src.shared.api.dependencies import get_unit_of_work_factory
from src.shared.application.mediator import Mediator
from src.shared.application.unit_of_work import UnitOfWorkFactory
from src.shared.infra.database.session import get_async_session


def get_password_hasher() -> PasswordHasher:
    return BcryptPasswordHasher()


def get_user_repository(
    session: AsyncSession = Depends(get_async_session),
) -> UserRepository:
    return SQLAlchemyUserRepository(session)


def get_user_read_repository(
    session: AsyncSession = Depends(get_async_session),
) -> UserReadRepository:
    return SQLAlchemyUserReadRepository(session)


def get_register_user_handler(
    uow_factory: UnitOfWorkFactory = Depends(get_unit_of_work_factory),
    password_hasher: PasswordHasher = Depends(get_password_hasher),
) -> RegisterUserCommandHandler:
    return RegisterUserCommandHandler(
        uow_factory=uow_factory,
        password_hasher=password_hasher,
    )


def get_create_manager_handler(
    uow_factory: UnitOfWorkFactory = Depends(get_unit_of_work_factory),
    password_hasher: PasswordHasher = Depends(get_password_hasher),
) -> CreateManagerCommandHandler:
    return CreateManagerCommandHandler(
        uow_factory=uow_factory,
        password_hasher=password_hasher,
    )


def get_user_by_id_handler(
    user_read_repository: UserReadRepository = Depends(get_user_read_repository),
) -> GetUserByIdQueryHandler:
    return GetUserByIdQueryHandler(
        user_read_repository=user_read_repository,
    )


def get_mediator(
    register_handler: RegisterUserCommandHandler = Depends(get_register_user_handler),
    create_manager_handler: CreateManagerCommandHandler = Depends(
        get_create_manager_handler
    ),
    user_by_id_handler: GetUserByIdQueryHandler = Depends(get_user_by_id_handler),
) -> Mediator:
    mediator = Mediator()

    mediator.register(RegisterUserCommand, register_handler)
    mediator.register(CreateManagerCommand, create_manager_handler)
    mediator.register(GetUserByIdQuery, user_by_id_handler)

    return mediator
