from enum import StrEnum


class DocType(StrEnum):
    MEMO = "memo"                # служебная записка
    REPORT = "report"            # докладная записка
    REFERENCE = "reference"      # информационная справка
    LETTER = "letter"            # письмо


class RequisiteStatus(StrEnum):
    FOUND_IN_DRAFT = "found_in_draft"
    USER_PROVIDED = "user_provided"
    AUTO_FILLED = "auto_filled"
    MISSING = "missing"


class DocumentStatus(StrEnum):
    CREATED = "created"
    PROCESSED = "processed"
    DEGRADED = "degraded"        # ИИ упал, сработал fallback
    FAILED = "failed"
