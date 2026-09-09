from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from src.modules.auth.api.dependencies import get_current_user_id, require_roles
from src.modules.auth.api.rate_limit import limit_register_request
from src.modules.users.api.dependencies import get_mediator
from src.modules.users.api.schemas import (
    CreateManagerRequest,
    RegisterUserRequest,
    UserResponse,
)
from src.modules.users.application.commands.create_manager import CreateManagerCommand
from src.modules.users.application.commands.register_user import RegisterUserCommand
from src.modules.users.application.queries.get_user_by_id import GetUserByIdQuery
from src.modules.users.domain.enums import Role
from src.modules.users.domain.exceptions import (
    EmailAlreadyExistError,
    InvalidEmailError,
    InvalidUserNameError,
    UserNotFoundError,
    WeakPasswordError,
)
from src.shared.application.mediator import Mediator

router = APIRouter(prefix="/users", tags=["Users"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(limit_register_request)],
)
async def register_user(
    request: RegisterUserRequest,
    mediator: Mediator = Depends(get_mediator),
) -> UserResponse:
    cmd = RegisterUserCommand(
        name=request.name,
        email=str(request.email),
        password=request.password,
    )
    try:
        user = await mediator.send(cmd)
    except EmailAlreadyExistError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except (InvalidEmailError, InvalidUserNameError, WeakPasswordError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return UserResponse(
        id=user.id,
        name=user.name.value,
        email=user.email.value,
        role=user.role,
    )


@router.post(
    "/managers",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(Role.NETWORK_ADMIN))],
)
async def create_manager(
    request: CreateManagerRequest,
    mediator: Mediator = Depends(get_mediator),
) -> UserResponse:
    cmd = CreateManagerCommand(
        name=request.name,
        email=str(request.email),
        password=request.password,
    )
    try:
        user = await mediator.send(cmd)
    except EmailAlreadyExistError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except (InvalidEmailError, InvalidUserNameError, WeakPasswordError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return UserResponse(
        id=user.id,
        name=user.name.value,
        email=user.email.value,
        role=user.role,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
)
async def get_me(
    current_user_id: UUID = Depends(get_current_user_id),
    mediator: Mediator = Depends(get_mediator),
) -> UserResponse:
    query = GetUserByIdQuery(id=current_user_id)
    try:
        user = await mediator.send(query)
    except UserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
    )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(Role.NETWORK_ADMIN))],
)
async def get_user_by_id(
    user_id: UUID,
    mediator: Mediator = Depends(get_mediator),
) -> UserResponse:
    query = GetUserByIdQuery(id=user_id)
    try:
        user = await mediator.send(query)
    except UserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
    )
