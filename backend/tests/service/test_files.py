"""Service tests for the non-database seam.

Same pattern as the note service tests, different port: the real service, a real
(in-memory) adapter, no container and no credentials. This is the payoff of
``ports/object_storage.py`` — S3 behaviour is testable without S3.
"""

from __future__ import annotations

import pytest

from attendance.adapters.storage.in_memory import InMemoryObjectStorage
from attendance.services.files import FileNotFound, FileService, UnsafeStorageKey


@pytest.fixture
def service() -> FileService:
    return FileService(InMemoryObjectStorage())


async def test_store_then_fetch_returns_the_same_bytes(service: FileService):
    key = await service.store("report.pdf", b"%PDF-1.7", content_type="application/pdf")

    stored = await service.fetch(key)

    assert stored.data == b"%PDF-1.7"
    assert stored.content_type == "application/pdf"


async def test_the_content_type_is_guessed_when_the_client_omits_it(service: FileService):
    key = await service.store("notes.txt", b"hello", content_type="")

    assert (await service.fetch(key)).content_type == "text/plain"


async def test_two_uploads_of_the_same_filename_do_not_collide(service: FileService):
    first = await service.store("report.pdf", b"one")
    second = await service.store("report.pdf", b"two")

    assert first != second
    assert (await service.fetch(first)).data == b"one"
    assert (await service.fetch(second)).data == b"two"


async def test_a_path_traversal_filename_is_neutralised(service: FileService):
    key = await service.store("../../etc/passwd", b"x")

    # The directory components are stripped, so the key stays inside uploads/.
    assert key.startswith("uploads/")
    assert ".." not in key


async def test_fetching_a_key_this_service_did_not_issue_is_refused(service: FileService):
    """The download endpoint takes the key from the client, so it is untrusted
    input. Rejecting it here is what stops the endpoint being a file-disclosure
    bug."""
    for key in ("../../../etc/passwd", "uploads/../secrets", "secrets/x/y", "uploads/x/y"):
        with pytest.raises(UnsafeStorageKey):
            await service.fetch(key)


async def test_fetching_a_well_formed_but_absent_key_is_a_not_found(service: FileService):
    key = await service.store("report.pdf", b"x")
    await service.delete(key)

    with pytest.raises(FileNotFound):
        await service.fetch(key)
