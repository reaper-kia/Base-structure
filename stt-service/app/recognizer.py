from __future__ import annotations

import json
import logging
import struct
import wave
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any, BinaryIO

from app.config import (
    EXPECTED_CHANNELS,
    EXPECTED_COMPRESSION_TYPE,
    EXPECTED_SAMPLE_RATE,
    EXPECTED_SAMPLE_WIDTH_BYTES,
    MAX_AUDIO_DURATION_SECONDS,
    RECOGNITION_CHUNK_FRAMES,
)

logger = logging.getLogger(__name__)

try:
    import vosk
except Exception as exc:  # Приложение должно подняться даже при проблеме с Vosk.
    vosk = None
    _VOSK_IMPORT_ERROR: Exception | None = exc
else:
    _VOSK_IMPORT_ERROR = None


_AUDIO_PARSE_ERRORS = (
    wave.Error,
    EOFError,
    OSError,
    ValueError,
    OverflowError,
    struct.error,
)


class ModelUnavailableError(RuntimeError):
    """Модель Vosk не загружена и распознавание сейчас невозможно."""


class InvalidAudioError(ValueError):
    """Переданный файл не соответствует поддерживаемому WAV-формату."""


class RecognitionError(RuntimeError):
    """Vosk не смог технически завершить распознавание."""


@dataclass(frozen=True, slots=True)
class RecognitionResult:
    text: str
    duration_seconds: float


class VoskSpeechRecognizer:
    def __init__(self, model_path: Path) -> None:
        self._model_path = model_path
        self._model: Any | None = None
        self._load_error: str | None = None
        self._lock = Lock()

    @property
    def model_loaded(self) -> bool:
        with self._lock:
            return self._model is not None

    @property
    def load_error(self) -> str | None:
        with self._lock:
            return self._load_error

    def load_model(self) -> None:
        """
        Загружает модель в память.

        Все ошибки перехватываются намеренно: FastAPI должен продолжить работу,
        чтобы /health и /stt могли вернуть осмысленный ответ 503.
        """
        with self._lock:
            self._model = None
            self._load_error = None

            if vosk is None:
                self._load_error = (
                    f"не удалось импортировать пакет vosk: {_VOSK_IMPORT_ERROR}"
                )
                logger.error(self._load_error)
                return

            try:
                if not self._model_path.is_dir():
                    raise FileNotFoundError(
                        f"каталог модели не найден: {self._model_path}"
                    )

                vosk.SetLogLevel(-1)
                model = vosk.Model(str(self._model_path))
            except Exception as exc:
                self._load_error = str(exc)
                logger.exception(
                    "Не удалось загрузить модель Vosk из %s",
                    self._model_path,
                )
                return

            self._model = model
            logger.info("Модель Vosk загружена из %s", self._model_path)

    def recognize(self, audio_file: BinaryIO) -> RecognitionResult:
        with self._lock:
            model = self._model

        if model is None:
            raise ModelUnavailableError("модель Vosk не загружена")

        wav_file, frame_count, duration_seconds = self._open_validated_wav(
            audio_file
        )

        try:
            try:
                kaldi_recognizer = vosk.KaldiRecognizer(
                    model,
                    EXPECTED_SAMPLE_RATE,
                )
            except Exception as exc:
                logger.exception("Vosk не смог создать распознаватель")
                raise RecognitionError(
                    "не удалось инициализировать распознавание"
                ) from exc

            expected_pcm_bytes = (
                frame_count
                * EXPECTED_CHANNELS
                * EXPECTED_SAMPLE_WIDTH_BYTES
            )
            consumed_pcm_bytes = 0
            text_parts: list[str] = []

            while True:
                try:
                    pcm_chunk = wav_file.readframes(
                        RECOGNITION_CHUNK_FRAMES
                    )
                except _AUDIO_PARSE_ERRORS as exc:
                    raise InvalidAudioError(
                        "WAV-файл повреждён: не удалось прочитать аудиоданные"
                    ) from exc

                if not pcm_chunk:
                    break

                consumed_pcm_bytes += len(pcm_chunk)

                try:
                    if kaldi_recognizer.AcceptWaveform(pcm_chunk):
                        text = self._extract_text(
                            kaldi_recognizer.Result()
                        )
                        if text:
                            text_parts.append(text)
                except RecognitionError:
                    raise
                except Exception as exc:
                    logger.exception(
                        "Ошибка Vosk во время обработки аудиоданных"
                    )
                    raise RecognitionError(
                        "ошибка во время распознавания"
                    ) from exc

            if consumed_pcm_bytes != expected_pcm_bytes:
                raise InvalidAudioError(
                    "WAV-файл повреждён: аудиоданные обрезаны"
                )

            try:
                final_text = self._extract_text(
                    kaldi_recognizer.FinalResult()
                )
            except RecognitionError:
                raise
            except Exception as exc:
                logger.exception(
                    "Vosk не смог сформировать итоговый результат"
                )
                raise RecognitionError(
                    "не удалось получить результат распознавания"
                ) from exc

            if final_text:
                text_parts.append(final_text)

            normalized_text = " ".join(" ".join(text_parts).split())

            return RecognitionResult(
                text=normalized_text,
                duration_seconds=round(duration_seconds, 3),
            )
        finally:
            wav_file.close()

    @staticmethod
    def _open_validated_wav(
        audio_file: BinaryIO,
    ) -> tuple[wave.Wave_read, int, float]:
        try:
            audio_file.seek(0)
            wav_file = wave.open(audio_file, "rb")
        except _AUDIO_PARSE_ERRORS as exc:
            raise InvalidAudioError(
                "файл не является корректным WAV"
            ) from exc

        try:
            channels = wav_file.getnchannels()
            sample_rate = wav_file.getframerate()
            sample_width = wav_file.getsampwidth()
            compression_type = wav_file.getcomptype()
            frame_count = wav_file.getnframes()
        except _AUDIO_PARSE_ERRORS as exc:
            wav_file.close()
            raise InvalidAudioError(
                "WAV-файл повреждён: не удалось прочитать заголовок"
            ) from exc

        try:
            if compression_type != EXPECTED_COMPRESSION_TYPE:
                raise InvalidAudioError(
                    "WAV должен содержать несжатый 16-битный PCM-звук"
                )

            if channels != EXPECTED_CHANNELS:
                raise InvalidAudioError(
                    "ожидается моно WAV: файл должен содержать ровно один канал"
                )

            if sample_rate != EXPECTED_SAMPLE_RATE:
                raise InvalidAudioError(
                    "ожидается WAV с частотой дискретизации 16000 Гц"
                )

            if sample_width != EXPECTED_SAMPLE_WIDTH_BYTES:
                raise InvalidAudioError(
                    "ожидается WAV с 16-битными PCM-сэмплами"
                )

            if frame_count <= 0:
                raise InvalidAudioError(
                    "WAV-файл не содержит аудиоданных"
                )

            maximum_frames = int(
                MAX_AUDIO_DURATION_SECONDS * EXPECTED_SAMPLE_RATE
            )
            if frame_count > maximum_frames:
                raise InvalidAudioError(
                    "запись длиннее 3 минут, разбейте на части"
                )

            duration_seconds = frame_count / EXPECTED_SAMPLE_RATE
        except InvalidAudioError:
            wav_file.close()
            raise

        return wav_file, frame_count, duration_seconds

    @staticmethod
    def _extract_text(result_json: str) -> str:
        try:
            payload = json.loads(result_json)
        except (json.JSONDecodeError, TypeError) as exc:
            raise RecognitionError(
                "Vosk вернул некорректный JSON"
            ) from exc

        if not isinstance(payload, dict):
            raise RecognitionError(
                "Vosk вернул неожиданный формат результата"
            )

        text = payload.get("text")
        if not isinstance(text, str):
            raise RecognitionError(
                "в результате Vosk отсутствует текст"
            )

        return text.strip()