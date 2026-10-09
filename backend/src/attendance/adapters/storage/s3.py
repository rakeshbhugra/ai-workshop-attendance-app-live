"""S3 ObjectStorage adapter — works against real AWS S3 and against LocalStack.

The only difference between the two is ``endpoint_url``: set it to
``http://localstack:4566`` for the compose profile, leave it empty for real S3.
Nothing above this file knows which one is running.

boto3 is synchronous. Rather than take an extra async-AWS dependency, every call
is pushed to a worker thread with ``asyncio.to_thread`` so it can't block the
event loop. That is the right trade at this scale; if S3 ever becomes a hot path,
swap this adapter for an aioboto3 one — the port doesn't change, which is the
entire point of the port.
"""

from __future__ import annotations

import asyncio

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from attendance.ports.object_storage import ObjectStorage, StoredObject


class S3ObjectStorage(ObjectStorage):
    def __init__(
        self,
        bucket: str,
        *,
        region: str = "us-east-1",
        endpoint_url: str = "",
        access_key: str = "",
        secret_key: str = "",
    ) -> None:
        self._bucket = bucket
        # Empty credentials fall through to the default boto3 chain (instance
        # role / env / ~/.aws), which is what you want in production. They're only
        # passed explicitly for LocalStack, which needs any non-empty pair.
        self._client = boto3.client(
            "s3",
            region_name=region,
            endpoint_url=endpoint_url or None,
            aws_access_key_id=access_key or None,
            aws_secret_access_key=secret_key or None,
            # Path-style addressing: LocalStack and MinIO serve buckets at
            # <endpoint>/<bucket>, not <bucket>.<endpoint>, and real S3 accepts
            # both — so this one setting works everywhere.
            config=Config(s3={"addressing_style": "path"}),
        )

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )

    async def get(self, key: str) -> StoredObject | None:
        try:
            response = await asyncio.to_thread(
                self._client.get_object, Bucket=self._bucket, Key=key
            )
        except ClientError as exc:
            # A missing key is an expected outcome, not a failure. Anything else
            # (permissions, throttling, a wrong bucket) must keep propagating.
            if exc.response.get("Error", {}).get("Code") in {"NoSuchKey", "404"}:
                return None
            raise
        body: bytes = await asyncio.to_thread(response["Body"].read)
        return StoredObject(
            key=key,
            data=body,
            content_type=response.get("ContentType", "application/octet-stream"),
        )

    async def delete(self, key: str) -> None:
        # S3's delete_object is already idempotent — absent keys return 204.
        await asyncio.to_thread(self._client.delete_object, Bucket=self._bucket, Key=key)
