from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import pytest
from fastapi.testclient import TestClient

from app import main as stt_main
from app.recognizer import (
    InvalidAudioError,
    RecognitionResult,
    VoskSpeechRecognizer,
)


class StubRecognizer:
    def __init__(
        self,
        *,
        loaded: bool = True,
        result: RecognitionResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self.model_loaded = loaded
        self.result = result or RecognitionResult(
            text="тестовая расшифровка",
            duration_seconds=1.25,
        )
        self.error = error

    def load_model(self) -> None:
        pass

    def recognize(self, _: BinaryIO) -> RecognitionResult:
        if self.error is not None:
            raise self.error
        return self.result


@contextmanager
def client_with_recognizer(
    monkeypatch: pytest.MonkeyPatch,
    recognizer: StubRecognizer,
) -> Iterator[TestClient]:
    monkeypatch.setattr(stt_main, "recognizer", recognizer)
    with TestClient(stt_main.app) as client:
        yield client


def test_invalid_audio_returns_422(monkeypatch: pytest.MonkeyPatch) -> None:
    recognizer = StubRecognizer(error=InvalidAudioError("invalid_format"))

    with client_with_recognizer(monkeypatch, recognizer) as client:
        response = client.post(
            "/stt",
            files={"audio": ("invalid.mp3", b"not audio", "audio/mpeg")},
        )

    assert response.status_code == 422
    assert response.json() == {"detail": "invalid_format"}


def test_unavailable_model_returns_503(monkeypatch: pytest.MonkeyPatch) -> None:
    recognizer = StubRecognizer(loaded=False)

    with client_with_recognizer(monkeypatch, recognizer) as client:
        health_response = client.get("/health")
        stt_response = client.post(
            "/stt",
            files={"audio": ("recording.wav", b"audio", "audio/wav")},
        )

    assert health_response.status_code == 503
    assert health_response.json() == {
        "status": "unavailable",
        "model_loaded": False,
    }
    assert stt_response.status_code == 503
    assert stt_response.json() == {
        "detail": stt_main.SERVICE_UNAVAILABLE_DETAIL,
    }


def test_oversized_upload_returns_413(monkeypatch: pytest.MonkeyPatch) -> None:
    recognizer = StubRecognizer()
    monkeypatch.setattr(stt_main, "MAX_FILE_SIZE_BYTES", 4)

    with client_with_recognizer(monkeypatch, recognizer) as client:
        response = client.post(
            "/stt",
            files={"audio": ("recording.wav", b"12345", "audio/wav")},
        )

    assert response.status_code == 413
    assert response.json() == {"detail": stt_main.FILE_TOO_LARGE_DETAIL}


def test_success_response_keeps_frontend_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recognizer = StubRecognizer()

    with client_with_recognizer(monkeypatch, recognizer) as client:
        response = client.post(
            "/stt",
            files={"audio": ("recording.wav", b"audio", "audio/wav")},
        )

    assert response.status_code == 200
    assert response.json() == {
        "text": "тестовая расшифровка",
        "duration_seconds": 1.25,
        "model": "vosk-model-small-ru-0.22",
    }


def test_real_recognizer_rejects_non_wav_before_vosk() -> None:
    recognizer = VoskSpeechRecognizer(Path("unused-in-test"))
    recognizer._model = object()

    with pytest.raises(InvalidAudioError, match="корректным WAV"):
        recognizer.recognize(BytesIO(b"not a wav file"))
