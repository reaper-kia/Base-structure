from dataclasses import dataclass


@dataclass
class CreateManagerCommand:
    name: str
    email: str
    password: str
