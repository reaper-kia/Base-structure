import argparse
import asyncio
import getpass
from collections.abc import Sequence

from src.modules.users.domain.enums import Role
from src.modules.users.domain.entities import User
from src.modules.users.domain.value_objects import Email, RawPassword, UserName
from src.modules.users.infra.password_hasher import BcryptPasswordHasher
from src.shared.infra.database.unit_of_work import SQLAlchemyUnitOfWork
from src.shared.infra.database.session import async_session_factory, engine


async def create_admin(
    *,
    email: str,
    name: str,
    password: str,
) -> int:
    email_vo = Email(email)
    name_vo = UserName(name)
    raw_password = RawPassword(password)

    password_hasher = BcryptPasswordHasher()

    async with SQLAlchemyUnitOfWork(async_session_factory) as uow:
        existing_user = await uow.users.get_by_email(email_vo)

        if existing_user is not None:
            if existing_user.role is Role.NETWORK_ADMIN:
                print(f"Admin already exists: {email_vo.value}")
                return 0

            print("User with this email already exists and is not admin")
            print("Refusing to promote existing user from bootstrap script.")
            return 1

        admin = User.register(
            name=name_vo,
            email=email_vo,
            password_hash=password_hasher.hash(raw_password.value),
            role=Role.NETWORK_ADMIN,
        )
        await uow.users.add(admin)
        await uow.commit()

    print(f"Admin created {email_vo.value}")
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create initial admon user.")

    parser.add_argument(
        "--email",
        required=True,
        help="Admin email.",
    )
    parser.add_argument(
        "--name",
        default="Admin",
        help="Admin display name.",
    )
    parser.add_argument(
        "--password",
        default=None,
        help=(
            "Admin password. "
            "Avoid passing it directly in production because it may stay in shell history."
        ),
    )

    return parser.parse_args(argv)


async def async_main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    password = args.password
    if password is None:
        password = getpass.getpass("Admin password: ")

    try:
        return await create_admin(
            email=args.email,
            name=args.name,
            password=password,
        )
    finally:
        await engine.dispose()


def main() -> int:
    return asyncio.run(async_main())


if __name__ == "__main__":
    raise SystemExit(main())
