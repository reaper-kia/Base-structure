import json as json_module
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

import ml_service.main as main_module
from ml_service.main import app


LLM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "improved_text": {
            "type": "string",
            "minLength": 1,
        },
        "requisites": {
            "type": "object",
            "additionalProperties": {
                "type": ["string", "null"],
            },
        },
        "changes": {
            "type": "array",
        },
    },
    "required": [
        "improved_text",
        "requisites",
    ],
}

REQUEST = {
    "draft": ("Срок — 14 календарных дней. " "Ответственный: иванов и.и."),
    "doc_type": "memo",
    "doc_type_name": "Служебная записка",
    "structure_hint": "Адресат, текст, подпись",
    "requisite_keys": [
        "deadline",
        "responsible",
    ],
}


class FakeResponse:
    def __init__(
        self,
        payload: dict[str, Any],
        status_code: int = 200,
    ) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> dict[str, Any]:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code < 400:
            return

        request = httpx.Request(
            "POST",
            "http://ollama/api/generate",
        )
        response = httpx.Response(
            self.status_code,
            request=request,
        )

        raise httpx.HTTPStatusError(
            "Ollama error",
            request=request,
            response=response,
        )


def install_fake_ollama(
    monkeypatch: pytest.MonkeyPatch,
    *,
    outputs: list[dict[str, Any]] | None = None,
    unavailable: bool = False,
) -> None:
    responses: Iterator[dict[str, Any]] = iter(outputs or [])

    class FakeAsyncClient:
        def __init__(
            self,
            *args: Any,
            **kwargs: Any,
        ) -> None:
            pass

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(
            self,
            *args: Any,
        ) -> None:
            return None

        async def get(
            self,
            url: str,
        ) -> FakeResponse:
            if unavailable:
                raise httpx.ConnectError("Ollama unavailable")

            return FakeResponse(
                {
                    "models": [
                        {
                            "name": (main_module.settings.ollama_model),
                        }
                    ]
                }
            )

        async def post(
            self,
            url: str,
            *,
            json: dict[str, Any],
        ) -> FakeResponse:
            if unavailable:
                raise httpx.ConnectError("Ollama unavailable")

            payload = next(responses)

            return FakeResponse(
                {
                    "response": json_module.dumps(
                        payload,
                        ensure_ascii=False,
                    )
                }
            )

    monkeypatch.setattr(
        main_module.httpx,
        "AsyncClient",
        FakeAsyncClient,
    )


@pytest.fixture(autouse=True)
def stub_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        main_module,
        "load_llm_schema",
        lambda: LLM_SCHEMA,
    )


def test_health() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_contract_file_exists_and_is_json() -> None:
    contract_path = (
        Path(__file__).resolve().parents[2] / "contracts" / "llm_schema.json"
    )

    payload = json_module.loads(contract_path.read_text(encoding="utf-8"))

    assert payload["type"] == "object"
    assert set(payload["properties"]) == {
        "improved_text",
        "requisites",
        "changes",
    }


def test_model_health_reports_loaded_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_ollama(monkeypatch)

    with TestClient(app) as client:
        response = client.get("/health/model")

    assert response.status_code == 200
    assert response.json() == {
        "model_loaded": True,
        "model_version": (main_module.settings.ollama_model),
        "fallback_enabled": (main_module.settings.fallback_enabled),
        "supported_tasks": ["process"],
    }


def test_process_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_ollama(
        monkeypatch,
        outputs=[
            {
                "improved_text": (
                    "Срок исполнения — "
                    "14 календарных дней. "
                    "Ответственный: Иванов И. И."
                ),
                "requisites": {
                    "deadline": ("14 календарных дней"),
                    "responsible": "Иванов И. И.",
                    "unexpected": "ignored",
                },
                "changes": [
                    {
                        "type": "style",
                        "from": "Срок",
                        "to": "Срок исполнения",
                    }
                ],
            }
        ],
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/process",
            json=REQUEST,
        )

    assert response.status_code == 200

    body = response.json()

    assert body["is_fallback"] is False
    assert body["requisites"] == {
        "deadline": "14 календарных дней",
        "responsible": "Иванов И. И.",
    }
    assert body["changes"] == [
        {
            "type": "style",
            "from": "Срок",
            "to": "Срок исполнения",
        }
    ]
    assert body["fact_guard"]["verdict"] == "clean"


def test_process_falls_back_when_ollama_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_ollama(
        monkeypatch,
        unavailable=True,
    )
    monkeypatch.setattr(
        main_module.settings,
        "fallback_enabled",
        True,
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/process",
            json=REQUEST,
        )

    assert response.status_code == 200

    body = response.json()

    assert body["is_fallback"] is True
    assert body["improved_text"] == REQUEST["draft"]
    assert body["requisites"] == {
        "deadline": None,
        "responsible": None,
    }


def test_process_blocks_hallucinations_and_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hallucinated = {
        "improved_text": (f'{REQUEST["draft"]} ' "Регистрационный номер № 999."),
        "requisites": {
            "deadline": None,
            "responsible": None,
        },
        "changes": [],
    }

    install_fake_ollama(
        monkeypatch,
        outputs=[
            hallucinated,
            hallucinated,
        ],
    )
    monkeypatch.setattr(
        main_module.settings,
        "fallback_enabled",
        True,
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/process",
            json=REQUEST,
        )

    assert response.status_code == 200

    body = response.json()

    assert body["is_fallback"] is True
    assert body["improved_text"] == REQUEST["draft"]


def test_process_returns_503_when_fallback_is_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_ollama(
        monkeypatch,
        unavailable=True,
    )
    monkeypatch.setattr(
        main_module.settings,
        "fallback_enabled",
        False,
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/process",
            json=REQUEST,
        )

    assert response.status_code == 503


def test_process_rejects_empty_draft() -> None:
    payload = {
        **REQUEST,
        "draft": "",
    }

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/process",
            json=payload,
        )

    assert response.status_code == 422
