"""Port — blob storage for file bytes.

This is the worked example of a **non-repository adapter**: the same
port-and-adapter shape, applied to an external system that isn't the database.
Every external seam you add later — auth provider, LLM, notifier, payments —
looks exactly like this file plus two implementations.

It passes the rent test: two real implementations exist today (S3/LocalStack in
``adapters/storage/s3.py``, in-memory in ``adapters/storage/in_memory.py``), and
the in-memory one is what makes the file tests run without a container.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class StoredObject:
    """What comes back out of storage. A value object — no identity, just data."""

    key: str
    data: bytes
    content_type: str


class ObjectStorage(ABC):
    @abstractmethod
    async def put(self, key: str, data: bytes, content_type: str) -> None:
        """Write (or overwrite) an object. Keys are opaque paths, e.g.
        ``uploads/<uuid>/report.pdf``."""

    @abstractmethod
    async def get(self, key: str) -> StoredObject | None:
        """The object, or None if the key does not exist."""

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Idempotent: deleting an absent key is not an error."""
