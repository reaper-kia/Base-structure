from dataclasses import dataclass

from src.modules.users.application.commands.create_manager import CreateManagerCommand
from src.modules.users.application.ports.password_hasher import PasswordHasher
from src.modules.users.domain.entities import User
from src.modules.users.domain.enums import Role
from src.modules.users.domain.exceptions import EmailAlreadyExistError
from src.modules.users.domain.value_objects import Email, RawPassword, UserName
from src.shared.application.unit_of_work import UnitOfWorkFactory


@dataclass
class CreateManagerCommandHandler:
    uow_factory: UnitOfWorkFactory
    password_hasher: PasswordHasher

    async def handle(self, cmd: CreateManagerCommand) -> User:
        email = Email(cmd.email)
        name = UserName(cmd.name)
        raw_password = RawPassword(cmd.password)

        async with self.uow_factory() as uow:
            existing_user = await uow.users.get_by_email(email)
            if existing_user:
                raise EmailAlreadyExistError("Email already registered")

            password_hash = self.password_hasher.hash(raw_password.value)

            user = User.register(
                name=name,
                email=email,
                password_hash=password_hash,
                role=Role.CLUB_MANAGER,
            )

            await uow.users.add(user)
            await uow.commit()

        return user
