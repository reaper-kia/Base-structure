from __future__ import annotations

import argparse
import io
import json
import sys
import time
import urllib.error
import urllib.request
import uuid
import wave
from typing import Any


SAMPLE_RATE = 16_000
CHANNELS = 1
SAMPLE_WIDTH_BYTES = 2
SYNTHETIC_DURATION_SECONDS = 1.0
EXPECTED_MODEL = "vosk-model-small-ru-0.22"


def create_synthetic_wav() -> bytes:
    frame_count = int(
        SAMPLE_RATE * SYNTHETIC_DURATION_SECONDS
    )
    silent_pcm = b"\x00\x00" * frame_count

    output = io.BytesIO()
    with wave.open(output, "wb") as wav_file:
        wav_file.setnchannels(CHANNELS)
        wav_file.setsampwidth(SAMPLE_WIDTH_BYTES)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(silent_pcm)

    return output.getvalue()


def create_multipart_body(
    wav_data: bytes,
) -> tuple[bytes, str]:
    boundary = f"----stt-manual-{uuid.uuid4().hex}"

    header = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; '
        'name="audio"; filename="synthetic.wav"\r\n'
        "Content-Type: audio/wav\r\n"
        "\r\n"
    ).encode("utf-8")

    footer = (
        f"\r\n--{boundary}--\r\n"
    ).encode("utf-8")

    return header + wav_data + footer, boundary


def request_json(
    request: urllib.request.Request,
    timeout: float,
) -> tuple[int, dict[str, Any]]:
    try:
        with urllib.request.urlopen(
            request,
            timeout=timeout,
        ) as response:
            status_code = response.status
            raw_body = response.read()
    except urllib.error.HTTPError as exc:
        status_code = exc.code
        raw_body = exc.read()
    except urllib.error.URLError as exc:
        raise ConnectionError(str(exc.reason)) from exc

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            f"Сервис вернул невалидный JSON: {raw_body!r}"
        ) from exc

    if not isinstance(payload, dict):
        raise RuntimeError(
            f"Ожидался JSON-объект, получено: {payload!r}"
        )

    return status_code, payload


def wait_until_reachable(
    base_url: str,
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    health_url = f"{base_url}/health"
    last_connection_error: Exception | None = None

    while time.monotonic() < deadline:
        request = urllib.request.Request(
            health_url,
            method="GET",
        )

        try:
            status_code, payload = request_json(
                request,
                timeout=5.0,
            )
        except ConnectionError as exc:
            last_connection_error = exc
            time.sleep(1.0)
            continue

        if status_code != 200:
            raise RuntimeError(
                f"/health вернул HTTP {status_code}: {payload}"
            )

        if payload != {
            "status": "ok",
            "model_loaded": True,
        }:
            raise RuntimeError(
                f"Неожиданный ответ /health: {payload}"
            )

        return payload

    raise RuntimeError(
        "Сервис не стал доступен за "
        f"{timeout_seconds:.0f} секунд: "
        f"{last_connection_error}"
    )


def test_stt(base_url: str) -> dict[str, Any]:
    wav_data = create_synthetic_wav()
    request_body, boundary = create_multipart_body(wav_data)

    request = urllib.request.Request(
        f"{base_url}/stt",
        data=request_body,
        headers={
            "Content-Type": (
                f"multipart/form-data; boundary={boundary}"
            ),
            "Content-Length": str(len(request_body)),
        },
        method="POST",
    )

    status_code, payload = request_json(
        request,
        timeout=60.0,
    )

    if status_code != 200:
        raise RuntimeError(
            f"/stt вернул HTTP {status_code}: {payload}"
        )

    required_fields = {
        "text",
        "duration_seconds",
        "model",
    }
    missing_fields = required_fields.difference(payload)
    if missing_fields:
        raise RuntimeError(
            "В ответе /stt отсутствуют поля: "
            + ", ".join(sorted(missing_fields))
        )

    if not isinstance(payload["text"], str):
        raise RuntimeError(
            "Поле text должно быть строкой"
        )

    if not isinstance(
        payload["duration_seconds"],
        (int, float),
    ):
        raise RuntimeError(
            "Поле duration_seconds должно быть числом"
        )

    if abs(
        float(payload["duration_seconds"])
        - SYNTHETIC_DURATION_SECONDS
    ) > 0.01:
        raise RuntimeError(
            "Сервис вернул неожиданную длительность: "
            f"{payload['duration_seconds']}"
        )

    if payload["model"] != EXPECTED_MODEL:
        raise RuntimeError(
            "Сервис вернул неожиданное имя модели: "
            f"{payload['model']!r}"
        )

    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Техническая проверка локального STT-сервиса"
        )
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8200",
        help=(
            "Базовый URL сервиса "
            "(по умолчанию: http://localhost:8200)"
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base_url = args.url.rstrip("/")

    try:
        health_payload = wait_until_reachable(base_url)
        print(
            "Healthcheck успешно:",
            json.dumps(
                health_payload,
                ensure_ascii=False,
            ),
        )

        stt_payload = test_stt(base_url)
        print(
            "STT-проверка успешна:",
            json.dumps(
                stt_payload,
                ensure_ascii=False,
            ),
        )
    except Exception as exc:
        print(
            f"Проверка завершилась ошибкой: {exc}",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())