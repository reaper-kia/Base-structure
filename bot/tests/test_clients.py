from __future__ import annotations

import json
import unittest
from collections import deque
from uuid import uuid4

import httpx

from app.config import DOCX_MEDIA_TYPE
from app.doc_api import DocumentApiClient
from app.max_client import MaxClient, MaxRecipient, parse_inbound_update


class DocumentApiClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_complete_document_flow(self) -> None:
        document_id = str(uuid4())
        responses = deque(
            [
                httpx.Response(
                    200,
                    json=[
                        {
                            "id": "memo",
                            "name": "Записка",
                            "description": "",
                            "requisites": [
                                {
                                    "key": "doc_date",
                                    "label": "Дата",
                                    "required": True,
                                }
                            ],
                        }
                    ],
                ),
                httpx.Response(
                    200,
                    json={
                        "templates": [
                            {
                                "id": "classic",
                                "name": "Классический",
                                "description": "",
                                "available": True,
                            },
                            {
                                "id": "off",
                                "name": "Недоступный",
                                "available": False,
                            },
                        ]
                    },
                ),
                httpx.Response(202, json={"id": document_id}),
                httpx.Response(
                    200,
                    json={
                        "id": document_id,
                        "status": "processing",
                        "stage": "llm",
                        "requisites": [],
                    },
                ),
                httpx.Response(
                    200,
                    json={
                        "id": document_id,
                        "status": "processed",
                        "stage": None,
                        "requisites": [
                            {
                                "key": "doc_date",
                                "label": "Дата",
                                "value": None,
                                "status": "missing",
                            }
                        ],
                    },
                ),
                httpx.Response(
                    200,
                    content=b"PK\x03\x04fake-docx",
                    headers={
                        "content-type": DOCX_MEDIA_TYPE,
                        "content-disposition": 'attachment; filename="memo.docx"',
                    },
                ),
            ]
        )

        async def handler(request: httpx.Request) -> httpx.Response:
            response = responses.popleft()
            response.request = request
            return response

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as http_client:
            client = DocumentApiClient(
                "http://documents.test",
                poll_interval_seconds=0.001,
                processing_timeout_seconds=1.0,
                max_attempts=1,
                client=http_client,
            )
            types = await client.get_document_types()
            templates = await client.get_templates()
            created = await client.create_document(
                draft="Черновик",
                doc_type=types[0].id,
                template_id=templates[0].id,
            )
            snapshot = await client.poll_until_done(created)
            rendered = await client.render_document(created)

        self.assertEqual(len(templates), 1)
        self.assertEqual(snapshot.requisites[0].status, "missing")
        self.assertEqual(rendered.filename, "memo.docx")
        self.assertFalse(responses)


class MaxClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_file_upload_and_send_use_official_shapes(self) -> None:
        requests: list[httpx.Request] = []

        async def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            if request.url.path == "/uploads":
                return httpx.Response(
                    200,
                    json={"url": "https://upload.test/file"},
                    request=request,
                )
            if request.url.host == "upload.test":
                return httpx.Response(
                    200,
                    json={"token": "file-token"},
                    request=request,
                )
            return httpx.Response(
                200,
                json={"message": {}},
                request=request,
            )

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as http_client:
            client = MaxClient(
                "secret",
                base_url="https://max.test",
                retry_backoff_seconds=0.001,
                max_attempts=1,
                client=http_client,
            )
            await client.send_file(
                MaxRecipient(user_id=123),
                content=b"PK\x03\x04docx",
                filename="memo.docx",
                text="Готово",
            )

        self.assertEqual(requests[0].url.params["type"], "file")
        self.assertNotIn("authorization", requests[1].headers)
        self.assertEqual(requests[2].url.params["user_id"], "123")
        payload = json.loads(requests[2].content)
        self.assertEqual(
            payload["attachments"][0],
            {"type": "file", "payload": {"token": "file-token"}},
        )

    def test_inbound_dialog_targets_sender_but_uses_chat_state_key(self) -> None:
        event = parse_inbound_update(
            {
                "update_type": "message_created",
                "message": {
                    "sender": {"user_id": 55, "is_bot": False},
                    "recipient": {"chat_id": 777, "chat_type": "dialog"},
                    "body": {"text": "Черновик"},
                },
            }
        )
        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.chat_id, 777)
        self.assertEqual(event.recipient.user_id, 55)
        self.assertEqual(event.text, "Черновик")


if __name__ == "__main__":
    unittest.main()
