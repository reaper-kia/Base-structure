from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class UserReadModel:
    id: UUID
    name: str
    email: str
    role: str
