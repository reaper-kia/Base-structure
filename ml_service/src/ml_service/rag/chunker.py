"""Детерминированная нарезка справочных документов на небольшие фрагменты."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?…])\s+")
_WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class KnowledgeChunk:
    doc_id: str
    position: int
    section_title: str
    text: str
    doc_hash: str


def get_doc_hash(text: str) -> str:
    """Стабильный идентификатор содержимого для идемпотентной индексации."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def split_into_sentences(text: str) -> list[str]:
    """Разбивает абзац по границам предложений и нормализует пробелы."""
    normalized = _WHITESPACE.sub(" ", text).strip()
    if not normalized:
        return []
    return [part.strip() for part in _SENTENCE_BOUNDARY.split(normalized) if part]


def _split_oversized_unit(text: str, max_chars: int) -> list[str]:
    """Режет только предложение, которое физически не помещается в чанк."""
    if len(text) <= max_chars:
        return [text]

    result: list[str] = []
    current = ""

    for word in text.split():
        if len(word) > max_chars:
            if current:
                result.append(current)
                current = ""
            result.extend(
                word[offset : offset + max_chars]
                for offset in range(0, len(word), max_chars)
            )
            continue

        candidate = f"{current} {word}".strip()
        if current and len(candidate) > max_chars:
            result.append(current)
            current = word
        else:
            current = candidate

    if current:
        result.append(current)

    return result


def _is_heading(paragraph: str, *, has_following_paragraph: bool) -> bool:
    stripped = paragraph.strip()
    if stripped.startswith("#"):
        return True
    return (
        has_following_paragraph
        and len(stripped) <= 100
        and len(stripped.split()) <= 12
        and stripped[-1:] not in ".!?…;:"
    )


def chunk_document(
    text: str,
    doc_id: str,
    default_section: str = "",
    *,
    min_chars: int = 400,
    max_chars: int = 800,
) -> list[KnowledgeChunk]:
    """Нарезает документ без разрыва обычных предложений.

    ``min_chars`` — целевой нижний размер: последний фрагмент и текст перед
    очень длинным предложением могут быть короче. ``max_chars`` соблюдается
    всегда; между соседними чанками сохраняется одно предложение, если оно
    помещается вместе со следующим.
    """
    if not doc_id.strip():
        raise ValueError("doc_id must not be empty")
    if min_chars <= 0 or max_chars < min_chars:
        raise ValueError("expected 0 < min_chars <= max_chars")

    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []

    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", normalized)
        if paragraph.strip()
    ]
    doc_hash = get_doc_hash(normalized)
    chunks: list[KnowledgeChunk] = []
    current_units: list[str] = []
    current_section = default_section.strip()
    section_title = current_section

    def emit() -> None:
        nonlocal current_units
        chunk_text = " ".join(current_units).strip()
        if not chunk_text:
            return
        chunks.append(
            KnowledgeChunk(
                doc_id=doc_id,
                position=len(chunks),
                section_title=current_section,
                text=chunk_text,
                doc_hash=doc_hash,
            )
        )
        current_units = []

    for paragraph_index, paragraph in enumerate(paragraphs):
        if _is_heading(
            paragraph,
            has_following_paragraph=paragraph_index < len(paragraphs) - 1,
        ):
            emit()
            section_title = paragraph.lstrip("#").strip()
            current_section = section_title
            continue

        if current_units and current_section != section_title:
            emit()
        current_section = section_title

        units: list[str] = []
        for sentence in split_into_sentences(paragraph):
            units.extend(_split_oversized_unit(sentence, max_chars))

        for unit in units:
            if not current_units:
                current_units = [unit]
                continue

            candidate = " ".join([*current_units, unit])
            if len(candidate) <= max_chars:
                current_units.append(unit)
                continue

            previous_tail = current_units[-1]
            emit()

            overlap_candidate = f"{previous_tail} {unit}"
            current_units = (
                [previous_tail, unit] if len(overlap_candidate) <= max_chars else [unit]
            )

    emit()
    return chunks
