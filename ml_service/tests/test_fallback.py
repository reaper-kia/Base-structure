"""Резервная обработка — contracts/llm_contract.md §4, шаг 4.

Главное свойство fallback: он детерминирован и ничего не выдумывает.
Сценарий 6 проверяет именно это — сервис без модели обязан отдать
пригодный документ, а не потерять черновик.
"""

from ml_service.fallback import extract_requisites, improve_text, match_label

KEYS = ["addressee", "author", "doc_date", "reg_number", "subject", "position"]


def test_labelled_lines_become_requisites() -> None:
    draft = (
        "Кому: Генеральному директору ООО «Ромашка» Иванову И.И.\n"
        "От кого: начальник отдела аналитики Петров П.П.\n"
        "Дата: 12.03.2025\n"
        "Номер: 47-СЗ\n"
        "Заголовок: О закупке офисной техники\n\n"
        "Прошу выделить средства."
    )
    requisites = extract_requisites(draft, KEYS)

    assert (
        requisites["addressee"] == "Генеральному директору ООО «Ромашка» Иванову И.И."
    )
    assert requisites["doc_date"] == "12.03.2025"
    assert requisites["reg_number"] == "47-СЗ"
    assert requisites["subject"] == "О закупке офисной техники"
    assert requisites["author"] == "Петров П.П."
    assert requisites["position"] == "Начальник отдела аналитики"


def test_author_position_split_preserves_letter_organization() -> None:
    requisites = extract_requisites(
        "От кого: Генеральный директор ООО «Ромашка» Иванов И.И.",
        ["author", "position"],
    )

    assert requisites == {
        "author": "ООО «Ромашка» Иванов И.И.",
        "position": "Генеральный директор",
    }


def test_reference_author_keeps_position_when_position_key_is_absent() -> None:
    requisites = extract_requisites(
        "Составитель: руководитель отдела развития Козлов К.К.",
        ["author"],
    )

    assert requisites["author"] == "руководитель отдела развития Козлов К.К."


def test_label_without_separator_is_recognised() -> None:
    """В реальных черновиках двоеточие ставят не всегда."""
    assert match_label("Дата 12.03.2025") == ("doc_date", "12.03.2025")


def test_long_sentence_starting_with_label_word_is_not_a_requisite() -> None:
    """«Дата проведения проверки уточняется.» — это текст, а не реквизит."""
    assert match_label("Дата проведения проверки будет уточнена позднее.") is None


def test_unnamed_requisite_stays_null() -> None:
    """Сценарий 3: чего не назвали — того нет. Подставлять нельзя."""
    requisites = extract_requisites("Прошу выделить средства.", KEYS)

    assert all(value is None for value in requisites.values())


def test_requisites_do_not_duplicate_body_text() -> None:
    """Помеченные строки уходят в поля, а не остаются в тексте документа."""
    draft = "Кому: Иванову И.И.\nПрошу выделить средства."

    assert "Кому" not in improve_text(draft)


def test_colloquialisms_are_replaced() -> None:
    text = improve_text("кароче надо бы купить три компа")

    assert "кароче" not in text.lower()
    assert "компьютера" in text


def test_facts_are_never_touched() -> None:
    draft = "Стоимость 180 000 рублей, срок не позднее 25.03.2025."
    text = improve_text(draft)

    assert "180 000 рублей" in text
    assert "25.03.2025" in text
    assert "не позднее" in text


def test_dates_are_not_broken_by_punctuation_normalisation() -> None:
    assert "25.03.2025" in improve_text("Ответ направить до 25.03.2025")


def test_initials_do_not_start_a_new_sentence() -> None:
    text = improve_text("Начальник отдела Петров П.П. сообщает о закупке")

    assert "П.П. сообщает" in text


def test_abbreviation_does_not_start_a_new_sentence() -> None:
    text = improve_text("Выдать 50 000 руб. на закупку канцелярии")

    assert "руб. на закупку" in text


def test_empty_result_falls_back_to_the_draft() -> None:
    """Потерять черновик хуже, чем отдать его как есть."""
    assert improve_text("кароче").strip()
