"""Picks the ObjectStorage adapter from configuration.

This is the *only* place that decides between S3 and in-memory. Services take the
port and never ask which one they got — that's what makes the seam real.
"""

from __future__ import annotations

from attendance.adapters.storage.in_memory import InMemoryObjectStorage
from attendance.adapters.storage.s3 import S3ObjectStorage
from attendance.config.settings import Settings
from attendance.ports.object_storage import ObjectStorage

__all__ = ["InMemoryObjectStorage", "S3ObjectStorage", "build_object_storage"]


def build_object_storage(settings: Settings) -> ObjectStorage:
    """No bucket configured = storage off, and uploads live in process memory.
    That keeps a fresh clone runnable with no AWS account and no containers; it
    also means uploads vanish on restart, which is fine for local dev and would
    be a bug in production — so set ``ATTENDANCE_S3_BUCKET`` in every deployed env."""
    if not settings.s3_bucket:
        return InMemoryObjectStorage()
    return S3ObjectStorage(
        settings.s3_bucket,
        region=settings.s3_region,
        endpoint_url=settings.s3_endpoint_url,
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key,
    )
