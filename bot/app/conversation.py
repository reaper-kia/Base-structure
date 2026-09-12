from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import uuid4


class ConversationState(StrEnum):
    WAITING_DRAFT = "waiting_draft"
    WAITING_DOC_TYPE = "waiting_doc_type"
    WAITING_TEMPLATE = "waiting_template"
    PROCESSING = "processing"


class ConversationError(RuntimeError):
    """Base error for invalid user input or state transitions."""


class ChoiceNotFound(ConversationError):
    """Raised when text does not identify one of the offered choices."""


class InvalidTransition(ConversationError):
    """Raised when a transition does not match the current state."""


@dataclass(frozen=True, slots=True)
class RequiredRequisite:
    key: str
    label: str


@dataclass(frozen=True, slots=True)
class Choice:
    id: str
    label: str
    required_requisites: tuple[RequiredRequisite, ...] = ()


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    generation_id: str
    draft: str
    doc_type_id: str
    template_id: str
    required_requisites: tuple[RequiredRequisite, ...]


@dataclass(slots=True)
class _Conversation:
    state: ConversationState = ConversationState.WAITING_DRAFT
    draft: str | None = None
    doc_type_choices: tuple[Choice, ...] = ()
    selected_doc_type: Choice | None = None
    template_choices: tuple[Choice, ...] = ()
    generation_id: str | None = None


class ConversationStore:
    """In-memory finite-state machine keyed by MAX chat ID."""

    def __init__(self) -> None:
        self._items: dict[int, _Conversation] = {}

    def state(self, chat_id: int) -> ConversationState:
        conversation = self._items.get(chat_id)
        if conversation is None:
            return ConversationState.WAITING_DRAFT
        return conversation.state

    def reset(self, chat_id: int) -> str | None:
        conversation = self._items.pop(chat_id, None)
        return None if conversation is None else conversation.generation_id

    def start(
        self,
        chat_id: int,
        draft: str,
        doc_types: tuple[Choice, ...],
    ) -> None:
        if not draft.strip():
            raise ConversationError("Draft cannot be blank")
        if not doc_types:
            raise ConversationError("At least one document type is required")
        self._items[chat_id] = _Conversation(
            state=ConversationState.WAITING_DOC_TYPE,
            draft=draft,
            doc_type_choices=doc_types,
        )

    def doc_type_choices(self, chat_id: int) -> tuple[Choice, ...]:
        conversation = self._require(chat_id, ConversationState.WAITING_DOC_TYPE)
        return conversation.doc_type_choices

    def resolve_doc_type(self, chat_id: int, raw_value: str) -> Choice:
        return resolve_choice(self.doc_type_choices(chat_id), raw_value)

    def select_doc_type(
        self,
        chat_id: int,
        doc_type: Choice,
        templates: tuple[Choice, ...],
    ) -> None:
        conversation = self._require(chat_id, ConversationState.WAITING_DOC_TYPE)
        if doc_type not in conversation.doc_type_choices:
            raise ChoiceNotFound("Document type was not offered")
        if not templates:
            raise ConversationError("At least one template is required")
        conversation.selected_doc_type = doc_type
        conversation.template_choices = templates
        conversation.state = ConversationState.WAITING_TEMPLATE

    def template_choices(self, chat_id: int) -> tuple[Choice, ...]:
        conversation = self._require(chat_id, ConversationState.WAITING_TEMPLATE)
        return conversation.template_choices

    def resolve_template(self, chat_id: int, raw_value: str) -> Choice:
        return resolve_choice(self.template_choices(chat_id), raw_value)

    def begin_generation(
        self,
        chat_id: int,
        template: Choice,
    ) -> GenerationRequest:
        conversation = self._require(chat_id, ConversationState.WAITING_TEMPLATE)
        if template not in conversation.template_choices:
            raise ChoiceNotFound("Template was not offered")
        if conversation.draft is None or conversation.selected_doc_type is None:
            raise InvalidTransition("Conversation data is incomplete")

        generation_id = uuid4().hex
        conversation.generation_id = generation_id
        conversation.state = ConversationState.PROCESSING
        return GenerationRequest(
            generation_id=generation_id,
            draft=conversation.draft,
            doc_type_id=conversation.selected_doc_type.id,
            template_id=template.id,
            required_requisites=(conversation.selected_doc_type.required_requisites),
        )

    def complete(self, chat_id: int, generation_id: str) -> bool:
        conversation = self._items.get(chat_id)
        if conversation is None or conversation.generation_id != generation_id:
            return False
        self._items.pop(chat_id, None)
        return True

    def _require(
        self,
        chat_id: int,
        expected: ConversationState,
    ) -> _Conversation:
        conversation = self._items.get(chat_id)
        actual = (
            ConversationState.WAITING_DRAFT
            if conversation is None
            else conversation.state
        )
        if conversation is None or actual is not expected:
            raise InvalidTransition(
                f"Expected state {expected.value}, got {actual.value}"
            )
        return conversation


def resolve_choice(choices: tuple[Choice, ...], raw_value: str) -> Choice:
    value = raw_value.strip()
    if not value:
        raise ChoiceNotFound("Choice cannot be blank")

    if value.isdecimal():
        index = int(value) - 1
        if 0 <= index < len(choices):
            return choices[index]

    normalized = value.casefold()
    for choice in choices:
        if normalized in {choice.id.casefold(), choice.label.casefold()}:
            return choice
    raise ChoiceNotFound(f"Unknown choice: {value}")


def format_choices(choices: tuple[Choice, ...]) -> str:
    return "\n".join(
        f"{index}. {choice.label} [{choice.id}]"
        for index, choice in enumerate(choices, start=1)
    )
