from __future__ import annotations

import asyncio
import os
from enum import Enum
from typing import Optional

import boto3
from azure.storage.blob.aio import BlobServiceClient

from .models import Setting

basedir = os.path.abspath(os.path.dirname(__file__))

_s3_client = boto3.client("s3")
_blob_client: Optional[BlobServiceClient] = None


class StorageBackend(str, Enum):
    """Available storage backends."""

    LOCAL = "local"
    S3 = "s3"
    AZURE = "azure"


def _get_backend() -> StorageBackend:
    """Return the configured storage backend."""
    if Setting.get("use_s3").get_value():
        return StorageBackend.S3
    if Setting.get("use_azure").get_value():
        return StorageBackend.AZURE
    return StorageBackend.LOCAL

async def _get_blob_client() -> BlobServiceClient:
    """Return a cached Azure BlobServiceClient instance."""
    global _blob_client
    if _blob_client is None:
        conn = Setting.get("azure_connection_string").get_value()
        _blob_client = BlobServiceClient.from_connection_string(conn)
    return _blob_client

async def upload_bytes(data: bytes, path: str) -> None:
    """Upload ``data`` to ``path`` using the configured backend."""
    backend = _get_backend()
    if backend is StorageBackend.S3:
        bucket = Setting.get("bucket_name").get_value()
        await asyncio.to_thread(_s3_client.put_object, Bucket=bucket, Key=path, Body=data)
    elif backend is StorageBackend.AZURE:
        container = Setting.get("azure_container").get_value()
        client = await _get_blob_client()
        blob = client.get_container_client(container).get_blob_client(path)
        await blob.upload_blob(data, overwrite=True)
    else:
        file_path = os.path.join(basedir, path)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        await asyncio.to_thread(_write_file, file_path, data)

def _write_file(fp: str, data: bytes) -> None:
    """Write data to a file path synchronously."""
    with open(fp, "wb") as f:
        f.write(data)

