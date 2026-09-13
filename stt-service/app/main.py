from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from tempfile import SpooledTemporaryFile
from typing import Annotated, AsyncIterator, BinaryIO, Literal

import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.config import (
    HOST,
    MAX_FILE_SIZE_BYTES,
    MODEL_NAME,
    MODEL_PATH,
    PORT,
    SPOOL_MEMORY_LIMIT_BYTES,
    UPLOAD_CHUNK_SIZE_BYTES,
)
from app.recognizer import (
    InvalidAudioError,
    ModelUnavailableError,
    RecognitionError,
    VoskSpeechRecognizer,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

FILE_TOO_LARGE_DETAIL = "файл слишком большой"
SERVICE_UNAVAILABLE_DETAIL = "сервис распознавания временно недоступен"

recognizer = VoskSpeechRecognizer(MODEL_PATH)


class SttResponse(BaseModel):
    text: str
    duration_seconds: float
    model: str


class HealthResponse(BaseModel):
    status: Literal["ok", "unavailable"]
    model_loaded: bool


class ErrorResponse(BaseModel):
    detail: str


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Загрузка CPU-модели не должна блокировать основной event loop.
    await asyncio.to_thread(recognizer.load_model)
    yield


app = FastAPI(
    title="Local Vosk STT Service",
    version="1.0.0",
    lifespan=lifespan,
)


def service_unavailable_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=SERVICE_UNAVAILABLE_DETAIL,
    )


async def copy_upload_with_limit(
    audio: UploadFile,
    target: BinaryIO,
) -> int:
    """
    Копирует UploadFile порциями.

    Чтение прекращается сразу после превышения лимита. Весь файл не
    преобразуется в bytes и не удерживается целиком в оперативной памяти.
    """
    total_size = 0

    try:
        while True:
            chunk = await audio.read(UPLOAD_CHUNK_SIZE_BYTES)
            if not chunk:
                break

            total_size += len(chunk)
            if total_size > MAX_FILE_SIZE_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=FILE_TOO_LARGE_DETAIL,
                )

            target.write(chunk)
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning(
            "Не удалось прочитать загруженный аудиофайл: %s",
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="не удалось прочитать аудиофайл",
        ) from exc

    return total_size


@app.get(
    "/health",
    response_model=HealthResponse,
    responses={
        503: {
            "model": HealthResponse,
            "description": "Модель Vosk не загружена",
        }
    },
)
async def health() -> HealthResponse | JSONResponse:
    if recognizer.model_loaded:
        return HealthResponse(
            status="ok",
            model_loaded=True,
        )

    payload = HealthResponse(
        status="unavailable",
        model_loaded=False,
    )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=payload.model_dump(),
    )


@app.post(
    "/stt",
    response_model=SttResponse,
    responses={
        413: {
            "model": ErrorResponse,
            "description": "Файл превышает лимит размера",
        },
        422: {
            "model": ErrorResponse,
            "description": "Некорректный WAV или превышена длительность",
        },
        503: {
            "model": ErrorResponse,
            "description": "Модель Vosk не загружена",
        },
    },
)
async def transcribe(
    audio: Annotated[
        UploadFile,
        File(
            description="WAV, 16 кГц, моно, 16-битный PCM",
        ),
    ],
) -> SttResponse:
    if not recognizer.model_loaded:
        raise service_unavailable_error()

    # Starlette обычно сообщает точный размер файловой части после
    # multipart-парсинга. Проверка позволяет отказаться от чтения сразу.
    if audio.size is not None and audio.size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=FILE_TOO_LARGE_DETAIL,
        )

    try:
        # После 1 МиБ содержимое временного файла автоматически переносится
        # на диск, поэтому большие допустимые файлы не лежат целиком в RAM.
        with SpooledTemporaryFile(
            max_size=SPOOL_MEMORY_LIMIT_BYTES,
            mode="w+b",
        ) as temporary_audio:
            uploaded_size = await copy_upload_with_limit(
                audio,
                temporary_audio,
            )

            if uploaded_size == 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="аудиофайл пуст",
                )

            temporary_audio.seek(0)

            try:
                result = await asyncio.to_thread(
                    recognizer.recognize,
                    temporary_audio,
                )
            except InvalidAudioError as exc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=str(exc),
                ) from exc
            except (ModelUnavailableError, RecognitionError) as exc:
                logger.warning("Распознавание недоступно: %s", exc)
                raise service_unavailable_error() from exc
            except Exception as exc:
                logger.exception("Непредвиденная ошибка распознавания")
                raise service_unavailable_error() from exc

            return SttResponse(
                text=result.text,
                duration_seconds=result.duration_seconds,
                model=MODEL_NAME,
            )
    finally:
        try:
            await audio.close()
        except OSError:
            logger.warning(
                "Не удалось закрыть временный загруженный файл",
                exc_info=True,
            )


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        log_level="info",
    )
