from enum import StrEnum


class DocType(StrEnum):
    MEMO = "memo"  # служебная записка
    REPORT = "report"  # докладная записка
    REFERENCE = "reference"  # информационная справка
    LETTER = "letter"  # письмо


class RequisiteStatus(StrEnum):
    FOUND_IN_DRAFT = "found_in_draft"  # ИИ нашёл значение в черновике
    USER_PROVIDED = "user_provided"  # пользователь вписал руками
    AUTO_FILLED = "auto_filled"  # система подставила достоверное (дата)
    MISSING = "missing"  # нет значения, и это проблема
    LEFT_BLANK = "left_blank"  # пользователь осознанно оставил пустым


class DocumentStatus(StrEnum):
    PROCESSING = "processing"  # пайплайн идёт, поле stage заполнено
    PROCESSED = "processed"  # готов, ИИ отработал штатно
    DEGRADED = "degraded"  # ИИ упал, сработал rule-based fallback
    FAILED = "failed"  # обработать не удалось, есть error


class ProcessingStage(StrEnum):
    LLM = "llm"
    FACT_GUARD = "fact_guard"
    VALIDATION = "validation"
