"""Клиент актуального Ollama API для пакетного получения embeddings."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

import httpx


class EmbeddingUnavailable(RuntimeError):
    """Ollama или embedding-модель не смогли построить векторы."""


class OllamaEmbedder:
    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: float,
        keep_alive: str = "0",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._keep_alive = keep_alive
        self._transport = transport

    @property
    def model(self) -> str:
        return self._model

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        inputs = [text.strip() for text in texts]
        if not inputs or any(not text for text in inputs):
            raise ValueError("embedding input must contain non-empty text")

        payload = {
            "model": self._model,
            "input": inputs,
            "truncate": True,
            # Не держим bge-m3 рядом с 7B-моделью в памяти Ollama.
            "keep_alive": self._keep_alive,
        }

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds,
                transport=self._transport,
                trust_env=False,
            ) as client:
                response = await client.post(
                    f"{self._base_url}/api/embed",
                    json=payload,
                )
                response.raise_for_status()
                data: Any = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise EmbeddingUnavailable(f"Ollama embed failed: {exc}") from exc

        vectors = data.get("embeddings") if isinstance(data, dict) else None
        if not isinstance(vectors, list) or len(vectors) != len(inputs):
            raise EmbeddingUnavailable("Ollama returned an invalid embeddings count")

        normalized: list[list[float]] = []
        expected_size: int | None = None

        for vector in vectors:
            if not isinstance(vector, list) or not vector:
                raise EmbeddingUnavailable("Ollama returned an empty embedding")
            if any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                for value in vector
            ):
                raise EmbeddingUnavailable("Ollama returned a non-numeric embedding")

            float_vector = [float(value) for value in vector]
            expected_size = expected_size or len(float_vector)
            if len(float_vector) != expected_size:
                raise EmbeddingUnavailable("Ollama returned inconsistent dimensions")
            normalized.append(float_vector)

        return normalized
