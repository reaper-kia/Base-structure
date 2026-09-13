import asyncio
import json

import httpx
import pytest

from ml_service.rag.embedder import EmbeddingUnavailable, OllamaEmbedder


def test_embedder_uses_current_batch_api_and_validates_vectors() -> None:
    captured: dict = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        assert request.url.path == "/api/embed"
        return httpx.Response(200, json={"embeddings": [[1, 0], [0.5, 0.5]]})

    embedder = OllamaEmbedder(
        base_url="http://ollama:11434/",
        model="bge-m3",
        timeout_seconds=2,
        keep_alive="0",
        transport=httpx.MockTransport(handler),
    )

    vectors = asyncio.run(embedder.embed(["первый", "второй"]))

    assert vectors == [[1.0, 0.0], [0.5, 0.5]]
    assert captured == {
        "model": "bge-m3",
        "input": ["первый", "второй"],
        "truncate": True,
        "keep_alive": "0",
    }


@pytest.mark.parametrize(
    "response_payload",
    [
        {"embedding": [0.1, 0.2]},
        {"embeddings": []},
        {"embeddings": [[0.1], [0.2]]},
        {"embeddings": [[True, 0.2]]},
        {"embeddings": [[float("nan"), 0.2]]},
    ],
)
def test_embedder_rejects_malformed_ollama_response(response_payload: dict) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=response_payload)

    embedder = OllamaEmbedder(
        base_url="http://ollama:11434",
        model="bge-m3",
        timeout_seconds=2,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(EmbeddingUnavailable):
        asyncio.run(embedder.embed(["текст"]))


def test_embedder_turns_http_failure_into_typed_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "model not found"})

    embedder = OllamaEmbedder(
        base_url="http://ollama:11434",
        model="missing",
        timeout_seconds=2,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(EmbeddingUnavailable, match="Ollama embed failed"):
        asyncio.run(embedder.embed(["текст"]))


def test_embedder_rejects_empty_input_before_http_call() -> None:
    embedder = OllamaEmbedder(
        base_url="http://ollama:11434",
        model="bge-m3",
        timeout_seconds=2,
    )

    with pytest.raises(ValueError, match="non-empty"):
        asyncio.run(embedder.embed([]))
