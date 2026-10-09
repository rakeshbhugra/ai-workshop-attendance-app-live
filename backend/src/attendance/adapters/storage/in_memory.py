"""In-memory ObjectStorage — the test double, and the zero-config local default.

Also what the app falls back to when no bucket is configured, so a fresh clone
runs with no AWS credentials and no LocalStack container.
"""

from __future__ import annotations

from attendance.ports.object_storage import ObjectStorage, StoredObject


class InMemoryObjectStorage(ObjectStorage):
    def __init__(self) -> None:
        self._objects: dict[str, StoredObject] = {}

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        self._objects[key] = StoredObject(key=key, data=data, content_type=content_type)

    async def get(self, key: str) -> StoredObject | None:
        return self._objects.get(key)

    async def delete(self, key: str) -> None:
        self._objects.pop(key, None)
