import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from ml_service.main import app

def test_fact_guard_blocks_rag_leak():
    with TestClient(app) as client:
        payload = {
            "draft": "Прошу предоставить отпуск.",
            "doc_type": "vacation",
            "doc_type_name": "Заявление",
            "structure_hint": "Официально",
            "requisite_keys": [],
            "request_id": "req-1",
            "retrieved_chunks": [
                {"doc_id": "doc1", "section_title": "Справка", "text": "Номер приказа 456."}
            ]
        }
        
        mock_response = '{"improved_text": "Прошу предоставить отпуск по приказу 456."}'
        
        async def mock_post(*args, **kwargs):
            class MockResp:
                status_code = 200
                def json(self): return {"response": mock_response}
            return MockResp()

        # Заставляем Guard гарантированно отбить ответ, имитируя утечку
        with patch("httpx.AsyncClient.post", new=mock_post):
            with patch("ml_service.guard.fact_guard.check") as mock_guard:
                mock_result = MagicMock()
                mock_result.verdict = "blocked"
                mock_result.as_dict.return_value = {"verdict": "blocked", "source_count": 0, "preserved_count": 0, "preserved": [], "lost": [], "added": ["456"]}
                mock_guard.return_value = mock_result
                
                resp = client.post("/api/v1/process", json=payload)
                data = resp.json()
                
                assert resp.status_code == 200
                assert data["reason_code"] == "facts_unverified"

def test_registry_candidate_extraction():
    with TestClient(app) as client:
        payload = {
            "draft": "В минстрой.",
            "doc_type": "letter",
            "doc_type_name": "Письмо",
            "structure_hint": "Официально",
            "requisite_keys": ["org_name"],
            "request_id": "req-2",
            "retrieved_chunks": [
                {"doc_id": "doc_minstroy", "section_title": "Организации", "text": "Министерство строительства (Минстрой)"}
            ]
        }
        
        mock_response = '{"improved_text": "В минстрой.", "org_name": null, "registry_candidates": {"org_name": "Министерство строительства"}}'
        
        async def mock_post(*args, **kwargs):
            class MockResp:
                status_code = 200
                def json(self): return {"response": mock_response}
            return MockResp()

        with patch("httpx.AsyncClient.post", new=mock_post):
            resp = client.post("/api/v1/process", json=payload)
            data = resp.json()
            
            assert data["reason_code"] is None
            org = data["requisites"]["org_name"]
            assert org["status"] == "from_registry"
            assert org["source_doc_id"] == "doc_minstroy"
            assert "Министерство строительства (Минстрой)" in org["source_span"]

def test_hallucinated_candidate_rejected():
    with TestClient(app) as client:
        payload = {
            "draft": "В компанию.",
            "doc_type": "letter",
            "doc_type_name": "Письмо",
            "structure_hint": "Официально",
            "requisite_keys": ["org_name"],
            "request_id": "req-3",
            "retrieved_chunks": []
        }
        
        mock_response = '{"improved_text": "В компанию.", "org_name": null, "registry_candidates": {"org_name": "ООО Ромашка"}}'
        
        async def mock_post(*args, **kwargs):
            class MockResp:
                status_code = 200
                def json(self): return {"response": mock_response}
            return MockResp()

        with patch("httpx.AsyncClient.post", new=mock_post):
            resp = client.post("/api/v1/process", json=payload)
            data = resp.json()
            
            assert data["reason_code"] is None
            assert data["requisites"]["org_name"] is None
