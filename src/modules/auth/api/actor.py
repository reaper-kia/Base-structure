from dataclasses import dataclass
from uuid import UUID

from src.modules.users.domain.enums import Role


@dataclass(frozen=True)
class RequestActor:
    user_id: UUID
    role: Role
    name: str

    @property
    def is_network_admin(self) -> bool:
        return self.role is Role.NETWORK_ADMIN

    @property
    def is_club_manager(self) -> bool:
        return self.role is Role.CLUB_MANAGER

    @property
    def is_client(self) -> bool:
        return self.role is Role.CLIENT
