import logging
import httpx
from typing import List
from ml_service.config import settings

logger = logging.getLogger(__name__)

EMBED_MODEL = "bge-m3"

async def get_embedding(text: str) -> List[float]:
    """
    ML-09: Получение вектора через Ollama HTTP API.
    Не падает при недоступности, а пробрасывает ValueError для перехвата.
    """
    url = f"{settings.ollama_url.rstrip('/')}/api/embeddings"
    payload = {
        "model": EMBED_MODEL,
        "prompt": text
    }
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url, json=payload, timeout=settings.ollama_timeout_seconds)
            resp.raise_for_status()
            data = resp.json()
            return data.get("embedding", [])
        except Exception as e:
            logger.error(f"Ошибка получения эмбеддинга от Ollama: {e}")
            raise ValueError("embedder_unavailable")
