"""Application service over the ObjectStorage port.

The example of a service whose dependency is *not* a database. It takes the port,
so its tests run against ``InMemoryObjectStorage`` with no container and no
credentials — same trick as ``FakeUnitOfWork``, different seam.
"""

from __future__ import annotations

import mimetypes
import re
import uuid

from attendance.domain.exceptions import NotFoundError, ValidationError
from attendance.ports.object_storage import ObjectStorage, StoredObject

KEY_PREFIX = "uploads"
MAX_FILENAME_LENGTH = 120
# Anything outside this set is replaced. Deliberately strict: a key is later
# accepted back from the client as a URL path, so "/" and ".." must never survive.
_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


class FileNotFound(NotFoundError):
    def __init__(self, key: str) -> None:
        super().__init__(f"No stored file at {key}.")


class UnsafeStorageKey(ValidationError):
    def __init__(self) -> None:
        super().__init__("That storage key is not one this service issued.")


class FileService:
    def __init__(self, storage: ObjectStorage) -> None:
        self._storage = storage

    async def store(self, filename: str, data: bytes, content_type: str = "") -> str:
        """Save the bytes and return the key the client should use to fetch them.

        Every upload gets its own UUID directory, so two people uploading
        ``report.pdf`` don't overwrite each other and the original filename
        survives for the download's Content-Disposition.
        """
        safe_name = _safe_filename(filename)
        key = f"{KEY_PREFIX}/{uuid.uuid4().hex}/{safe_name}"
        await self._storage.put(
            key,
            data,
            content_type or _guess_content_type(safe_name),
        )
        return key

    async def fetch(self, key: str) -> StoredObject:
        _require_safe_key(key)
        stored = await self._storage.get(key)
        if stored is None:
            raise FileNotFound(key)
        return stored

    async def delete(self, key: str) -> None:
        _require_safe_key(key)
        await self._storage.delete(key)


def _safe_filename(filename: str) -> str:
    # Strip any directory component the browser sent (IE used to send full
    # Windows paths, and a crafted multipart body still can).
    stem = filename.replace("\\", "/").rsplit("/", 1)[-1]
    cleaned = _UNSAFE.sub("_", stem).strip("._") or "file"
    return cleaned[:MAX_FILENAME_LENGTH]


def _guess_content_type(filename: str) -> str:
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or "application/octet-stream"


def _require_safe_key(key: str) -> None:
    """Keys come back from the client on download. Re-derive that the key is one
    we could have issued instead of trusting it — otherwise ``../../secrets``
    is a valid S3 key and the endpoint is a file-disclosure bug."""
    parts = key.split("/")
    if len(parts) != 3 or parts[0] != KEY_PREFIX or ".." in parts:
        raise UnsafeStorageKey
    if _safe_filename(parts[2]) != parts[2]:
        raise UnsafeStorageKey
    try:
        uuid.UUID(hex=parts[1])
    except ValueError as exc:
        raise UnsafeStorageKey from exc
