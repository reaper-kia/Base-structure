import asyncio
import json

from ml_service.config import settings
from ml_service.pipeline import process
from ml_service.rag.retriever import RetrievedChunk
from ml_service.schemas import ProcessRequest


class StaticClient:
    model = "test-model"

    def __init__(self, response: dict) -> None:
        self.response = response
        self.prompts: list[str] = []

    async def generate(self, prompt: str, response_schema: dict) -> str:
        self.prompts.append(prompt)
        return json.dumps(self.response, ensure_ascii=False)


class StaticRetriever:
    def __init__(self, text: str) -> None:
        self.text = text
        self.queries: list[str] = []

    async def retrieve(self, query: str) -> list[RetrievedChunk]:
        self.queries.append(query)
        return [
            RetrievedChunk(
                doc_id="style.md",
                position=0,
                section_title="Просьба",
                text=self.text,
                doc_hash="a" * 64,
                score=0.9,
                method="vector",
            )
        ]


class BrokenRetriever:
    async def retrieve(self, query: str) -> list[RetrievedChunk]:
        raise RuntimeError("index unavailable")


def _request(draft: str = "Прошу согласовать отпуск.") -> ProcessRequest:
    return ProcessRequest(
        draft=draft,
        doc_type="memo",
        doc_type_name="Служебная записка",
        structure_hint="основание -> просьба",
        requisite_keys=["author"],
        request_id="rag-test",
    )


def _valid_response(text: str = "Прошу согласовать отпуск.") -> dict:
    return {
        "improved_text": text,
        "requisites": {"author": None},
        "changes": [],
    }


def test_rag_context_reaches_model_without_changing_response_contract(
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "rag_enabled", True)
    client = StaticClient(_valid_response())
    retriever = StaticRetriever("Просьбу формулируют нейтрально.")

    response = asyncio.run(process(_request(), client=client, retriever=retriever))

    assert response.is_fallback is False
    assert response.requisites == {"author": None}
    assert retriever.queries
    assert "Служебная записка" in retriever.queries[0]
    assert "[Источник: style.md; раздел: Просьба]" in client.prompts[0]
    assert "Просьбу формулируют нейтрально." in client.prompts[0]


def test_rag_failure_does_not_break_normal_generation(monkeypatch) -> None:
    monkeypatch.setattr(settings, "rag_enabled", True)
    client = StaticClient(_valid_response())

    response = asyncio.run(
        process(_request(), client=client, retriever=BrokenRetriever())
    )

    assert response.is_fallback is False
    assert "Релевантные справочные фрагменты не найдены." in client.prompts[0]


def test_fact_guard_blocks_fact_copied_from_rag(monkeypatch) -> None:
    monkeypatch.setattr(settings, "rag_enabled", True)
    client = StaticClient(_valid_response("Заседание состоится 01.07.2030."))
    retriever = StaticRetriever("Заседание состоится 01.07.2030.")

    response = asyncio.run(
        process(
            _request("Прошу подготовить повестку."),
            client=client,
            retriever=retriever,
        )
    )

    assert response.is_fallback is True
    assert response.reason_code == "facts_unverified"
    assert "01.07.2030" not in response.improved_text
    assert len(client.prompts) == settings.max_attempts


def test_disabled_rag_never_calls_retriever() -> None:
    class MustNotRun:
        async def retrieve(self, query: str) -> list[RetrievedChunk]:
            raise AssertionError("disabled RAG must not retrieve")

    response = asyncio.run(
        process(
            _request(), client=StaticClient(_valid_response()), retriever=MustNotRun()
        )
    )

    assert response.is_fallback is False


def test_public_process_request_does_not_gain_branch_only_fields() -> None:
    assert "retrieved_chunks" not in ProcessRequest.model_fields
    assert "terminology_context" not in ProcessRequest.model_fields
