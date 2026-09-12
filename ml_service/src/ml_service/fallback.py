"""Резервная обработка без модели — contracts/llm_contract.md §4, шаг 4.

Включается, когда Ollama недоступна, ответ не удалось починить или Fact
Guard дважды вернул blocked. Ничего не выдумывает по определению: только
детерминированные правила.

Три слоя:

1. Разбор помеченных строк («Кому:», «Дата:», «Подпись:») в реквизиты.
   Это не догадка — пользователь сам назвал поле, значение берётся как есть.
2. Словарь просторечий и типичных опечаток -> официально-деловые обороты.
3. Нормализация пунктуации и абзацев по structure_hint.

Итог честно помечается `is_fallback: true`: бэкенд ставит документу статус
degraded, фронт показывает плашку «обработано в резервном режиме».
"""

from __future__ import annotations

import re

# Метка в начале строки -> ключ реквизита. Значение берётся дословно.
LABEL_TO_KEY: dict[str, str] = {
    "кому": "addressee",
    "адресат": "addressee",
    "от кого": "author",
    "от": "author",
    "автор": "author",
    "составитель": "author",
    "отправитель": "author",
    "должность": "position",
    "дата": "doc_date",
    "номер": "reg_number",
    "рег. номер": "reg_number",
    "заголовок": "subject",
    "тема": "subject",
    "подпись": "signature",
    "исполнитель": "executor",
    "обращение": "salutation",
}

# Просторечия и канцелярские ошибки -> деловой эквивалент.
# Пустая строка справа = выражение вычищается целиком.
COLLOQUIALISMS: tuple[tuple[str, str], ...] = (
    (r"\bкароче\b", ""),
    (r"\bкороче говоря\b", ""),
    (r"\bв общем\b", ""),
    (r"\bвообщем\b", ""),
    (r"\bздрасьте\b", ""),
    (r"\bпривет\b", ""),
    (r"\bнадо бы\b", "необходимо"),
    (r"\bнадо\b", "необходимо"),
    (r"\bнужно бы\b", "необходимо"),
    (r"\bкомпы\b", "компьютеры"),
    (r"\bкомпов\b", "компьютеров"),
    (r"\bкомпа\b", "компьютера"),
    (r"\bтелек\b", "телевизор"),
    (r"\bа то\b", ""),
    (r"\bзадолбал(?:ся|ась|ись)\b", ""),
    (r"\bзаколебал(?:ся|ась|ись)\b", ""),
    (r"\bустал сильно\b", ""),
    (r"\bкак-то так\b", ""),
    (r"\bчё\b", "что"),
    (r"\bщас\b", "сейчас"),
    (r"\bнормуль\b", "удовлетворительно"),
    (r"\bпофиксить\b", "устранить"),
    (r"\bзабить\b", "отложить"),
    (r"\bкинуть\b", "направить"),
    (r"\bскинуть\b", "направить"),
    (r"\bна недельку\b", ""),
    (r"\bгде то\b", "приблизительно"),
    (r"\bгде-то\b", "приблизительно"),
)

# Метка распознаётся только если она есть в словаре: иначе любая строка
# вида «Поставка — 10 дней» уехала бы в реквизиты. Длинные метки идут
# первыми, чтобы «от кого» выигрывало у «от».
_KNOWN_LABELS = "|".join(
    re.escape(label) for label in sorted(LABEL_TO_KEY, key=len, reverse=True)
)

# Явный разделитель — надёжный признак реквизита.
_LABEL_WITH_SEPARATOR = re.compile(
    rf"^\s*({_KNOWN_LABELS})\s*[:—-]\s*(.+?)\s*$", re.IGNORECASE
)

# Без разделителя («Дата 12.03.2025» — так пишут в реальных черновиках)
# признаём реквизитом только короткую строку без завершающей точки:
# иначе «Дата проведения проверки уточняется.» уехала бы в реквизиты.
_LABEL_BARE = re.compile(rf"^\s*({_KNOWN_LABELS})\s+(.+?)\s*$", re.IGNORECASE)
_BARE_LABEL_MAX_LENGTH = 100


def match_label(line: str) -> tuple[str, str] | None:
    """(ключ реквизита, значение) или None, если строка не похожа на реквизит."""
    match = _LABEL_WITH_SEPARATOR.match(line)

    if match is None:
        stripped = line.strip()
        if len(stripped) > _BARE_LABEL_MAX_LENGTH or stripped.endswith((".", "!", "?")):
            return None
        match = _LABEL_BARE.match(stripped)

    if match is None:
        return None

    return LABEL_TO_KEY[match.group(1).strip().lower()], match.group(2).strip()

_MULTISPACE = re.compile(r"[ \t]{2,}")
_SPACE_BEFORE_PUNCT = re.compile(r"\s+([,.;:!?])")
# Пробел после знака ставим только перед буквой: иначе «12,5» превратится
# в «12, 5», а «25.03.2025» — в «25. 03. 2025».
_MISSING_SPACE = re.compile(r"([,;:!?])(?=[A-Za-zА-Яа-яЁё])")
_MISSING_SPACE_DOT = re.compile(r"\.(?=[А-ЯЁA-Z][а-яёa-z])")
# Точка не всегда конец предложения: после инициала («Петров П.П. сообщает»)
# и после сокращения («50 000 руб. на закупку») следующее слово остаётся
# со строчной буквы.
_SENTENCE_START = re.compile(r"(^|(?<=[.!?])\s+)([а-яёa-z])")
_ABBREVIATIONS = (
    "руб.",
    "коп.",
    "тыс.",
    "млн.",
    "млрд.",
    "шт.",
    "г.",
    "гг.",
    "кв.",
    "ул.",
    "д.",
    "т.д.",
    "т.п.",
    "т.е.",
    "др.",
    "проч.",
)


def _is_sentence_boundary(text: str, position: int) -> bool:
    """Настоящий ли это конец предложения перед позицией `position`."""
    head = text[:position].rstrip()

    if head.endswith(_ABBREVIATIONS):
        return False

    # Инициал: «П.» — одна заглавная буква и точка.
    return not re.search(r"(?:^|[\s.])[А-ЯЁA-Z]\.$", head)


def _capitalize_sentences(text: str) -> str:
    def replace(match: re.Match) -> str:
        if match.group(1) and not _is_sentence_boundary(text, match.start(1)):
            return match.group(0)
        return match.group(1) + match.group(2).upper()

    return _SENTENCE_START.sub(replace, text)


def _clean_line(line: str) -> str:
    text = line
    for pattern, replacement in COLLOQUIALISMS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    text = _MULTISPACE.sub(" ", text)
    text = _SPACE_BEFORE_PUNCT.sub(r"\1", text)

    # Вычищенное просторечие оставляет после себя осиротевшую пунктуацию:
    # «Здрасьте! Нам...» -> «! Нам...», «работают. Вообщем, цена» -> «работают., цена».
    text = re.sub(r"([.!?])\s*[,;:]+", r"\1", text)
    text = re.sub(r"[,;:]{2,}", ",", text)
    text = re.sub(r"^[\s,.;:!?]+", "", text)

    text = _MISSING_SPACE.sub(r"\1 ", text)
    text = _MISSING_SPACE_DOT.sub(". ", text)
    text = re.sub(r"\s{2,}", " ", text).strip()

    if not text:
        return ""

    text = _capitalize_sentences(text)

    if text[-1] not in ".!?:":
        text += "."

    return text


def extract_requisites(draft: str, requisite_keys: list[str]) -> dict[str, str | None]:
    """Реквизиты из помеченных строк черновика. Ничего не додумывает."""
    found: dict[str, str] = {}

    for line in draft.splitlines():
        matched = match_label(line)
        if matched is None:
            continue

        key, value = matched
        if value and key not in found:
            found[key] = value

    return {key: found.get(key) for key in requisite_keys}


def improve_text(draft: str, structure_hint: str = "") -> str:
    """Чистит текст правилами: помеченные строки уходят в реквизиты."""
    body_lines: list[str] = []

    for line in draft.splitlines():
        stripped = line.strip()
        if not stripped:
            body_lines.append("")
            continue

        if match_label(stripped) is not None:
            # Реквизит: в содержательную часть он не идёт — его разместит
            # модуль оформления по правилам шаблона.
            continue

        body_lines.append(stripped)

    paragraphs: list[str] = []
    buffer: list[str] = []

    for line in body_lines:
        if line:
            buffer.append(line)
            continue
        if buffer:
            paragraphs.append(" ".join(buffer))
            buffer = []

    if buffer:
        paragraphs.append(" ".join(buffer))

    cleaned = [_clean_line(paragraph) for paragraph in paragraphs]
    result = "\n\n".join(paragraph for paragraph in cleaned if paragraph)

    # Пустой improved_text недопустим (§2): если чистка съела всё, отдаём
    # исходный текст — потерять черновик хуже, чем отдать его как есть.
    return result or draft.strip()


def process(
    draft: str,
    requisite_keys: list[str],
    structure_hint: str = "",
) -> dict:
    return {
        "improved_text": improve_text(draft, structure_hint),
        "requisites": extract_requisites(draft, requisite_keys),
        "changes": [],
    }
