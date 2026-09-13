import io
import json
import logging
import wave
from pathlib import Path
from vosk import Model, KaldiRecognizer

logger = logging.getLogger(__name__)

MODEL_PATH = Path("artifacts/vosk-model")
model = None

def load_model():
    global model
    if MODEL_PATH.exists():
        model = Model(str(MODEL_PATH))
        logger.info("Vosk model loaded successfully.")
    else:
        logger.warning(f"Vosk model not found at {MODEL_PATH}. STT will be unavailable.")

def recognize(audio_bytes: bytes) -> dict:
    if not model:
        raise RuntimeError("model_unavailable")

    with io.BytesIO(audio_bytes) as audio_io:
        try:
            with wave.open(audio_io, "rb") as wf:
                if wf.getnchannels() != 1 or wf.getframerate() != 16000:
                    raise ValueError("invalid_format")
                
                frames = wf.getnframes()
                rate = wf.getframerate()
                duration = frames / float(rate)
                
                if duration > 180.0:  # Лимит 3 минуты
                    raise ValueError("audio_too_long")

                rec = KaldiRecognizer(model, rate)
                rec.AcceptWaveform(wf.readframes(frames))
                result = json.loads(rec.FinalResult())
                
                return {
                    "text": result.get("text", ""),
                    "duration_seconds": round(duration, 1),
                    "model": "vosk-small-ru-0.22"
                }
        except wave.Error:
            raise ValueError("invalid_format")
