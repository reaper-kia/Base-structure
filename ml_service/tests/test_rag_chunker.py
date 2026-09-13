from ml_service.rag.chunker import chunk_document, get_doc_hash


def test_chunker_preserves_heading_limits_overlap_and_hash() -> None:
    text = (
        "# Порядок согласования\n\n"
        "Первое предложение важно. Второе предложение нужно. "
        "Третье предложение полезно. Четвёртое предложение уместно."
    )

    chunks = chunk_document(text, "rules.md", min_chars=20, max_chars=60)

    assert len(chunks) >= 2
    assert all(chunk.doc_id == "rules.md" for chunk in chunks)
    assert all(chunk.section_title == "Порядок согласования" for chunk in chunks)
    assert all(len(chunk.text) <= 60 for chunk in chunks)
    assert all(chunk.doc_hash == get_doc_hash(text.strip()) for chunk in chunks)
    assert chunks[0].text.split()[-3:] == chunks[1].text.split()[:3]
    assert [chunk.position for chunk in chunks] == list(range(len(chunks)))


def test_chunker_is_deterministic_and_handles_oversized_tokens() -> None:
    text = "Терминология\n\n" + "а" * 95

    first = chunk_document(text, "terms.txt", min_chars=10, max_chars=30)
    second = chunk_document(text, "terms.txt", min_chars=10, max_chars=30)

    assert first == second
    assert "".join(chunk.text for chunk in first) == "а" * 95
    assert all(len(chunk.text) <= 30 for chunk in first)


def test_chunker_rejects_invalid_limits_and_empty_document_id() -> None:
    try:
        chunk_document("текст", "", min_chars=10, max_chars=20)
    except ValueError as exc:
        assert "doc_id" in str(exc)
    else:
        raise AssertionError("empty doc_id must be rejected")

    try:
        chunk_document("текст", "doc", min_chars=30, max_chars=20)
    except ValueError as exc:
        assert "min_chars" in str(exc)
    else:
        raise AssertionError("invalid limits must be rejected")


def test_empty_document_produces_no_chunks() -> None:
    assert chunk_document(" \n\n ", "empty.md") == []
