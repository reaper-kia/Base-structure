import asyncio
import pytest
from unittest.mock import patch
from ml_service.rag.embedder import get_embedding

def test_get_embedding_success():
    """Тест 2: Эмбеддинг возвращает вектор (ML-09.5)."""
    mock_response = {"embedding": [0.1, 0.2, 0.3]}
    
    async def mock_post(*args, **kwargs):
        class MockResp:
            def raise_for_status(self): pass
            def json(self): return mock_response
        return MockResp()

    with patch("httpx.AsyncClient.post", new=mock_post):
        vector = asyncio.run(get_embedding("Служебная записка"))
        assert len(vector) == 3
        assert vector == [0.1, 0.2, 0.3]

def test_get_embedding_fails_gracefully():
    """Тест 3: Недоступная Ollama отдает понятную ошибку, а не крашит приложение (ML-09.5)."""
    async def mock_post_fail(*args, **kwargs):
        raise Exception("Connection refused")
        
    with patch("httpx.AsyncClient.post", new=mock_post_fail):
        with pytest.raises(ValueError, match="embedder_unavailable"):
            asyncio.run(get_embedding("Служебная записка"))
