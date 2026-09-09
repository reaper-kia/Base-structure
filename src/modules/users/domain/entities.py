from dataclasses import dataclass, field

from uuid import UUID, uuid4

from src.modules.users.domain.enums import Role
from src.modules.users.domain.value_objects import Email, UserName


@dataclass
class User:
    """Учётная запись. Владелец — Identity (модули auth + users).

    Здесь НЕТ клуба, абонемента, визитов, скидок и прогресса — только
    доказательство личности и роль. Связь с бизнес-профилем идёт в обратную
    сторону: Client.user_id UNIQUE.
    """

    name: UserName
    email: Email
    password_hash: str
    role: Role = Role.CLIENT
    id: UUID = field(default_factory=uuid4)

    @classmethod
    def register(
        cls,
        name: UserName,
        email: Email,
        password_hash: str,
        role: Role = Role.CLIENT,
    ) -> "User":
        return cls(
            name=name,
            email=email,
            password_hash=password_hash,
            role=role,
        )

    def change_role(self, new_role: Role) -> None:
        """Менять роль имеет право только Identity и только по команде
        NETWORK_ADMIN — проверка права происходит в application-слое."""
        self.role = new_role
