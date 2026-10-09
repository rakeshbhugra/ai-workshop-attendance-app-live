"""End-to-end tests for upload/download.

Runs against ``InMemoryObjectStorage`` via the dependency override in
``conftest.py``. The same requests hit LocalStack under ``make up-aws`` and real
S3 in production, with no code change — which is the claim this file is here to
keep honest.
"""

from __future__ import annotations

from httpx import AsyncClient

API = "/api/v1"


async def test_upload_then_download(client: AsyncClient):
    upload = await client.post(
        f"{API}/files",
        files={"file": ("report.txt", b"hello world", "text/plain")},
    )

    assert upload.status_code == 201
    key = upload.json()["key"]
    assert key.startswith("uploads/")

    download = await client.get(f"{API}/files/{key}")
    assert download.status_code == 200
    assert download.content == b"hello world"
    assert download.headers["content-type"].startswith("text/plain")
    assert "report.txt" in download.headers["content-disposition"]


async def test_downloading_an_unknown_key_is_a_404(client: AsyncClient):
    response = await client.get(f"{API}/files/uploads/{'0' * 32}/missing.txt")

    assert response.status_code == 404


async def test_a_traversal_attempt_is_rejected_not_served(client: AsyncClient):
    response = await client.get(f"{API}/files/uploads/../../etc/passwd")

    # 422 (UnsafeStorageKey) or 404 — never 200, and never the file.
    assert response.status_code in {404, 422}
