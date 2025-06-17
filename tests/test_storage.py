import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

pytest_plugins = ["pytest_asyncio"]

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "app" / "storage.py"


def load_storage(monkeypatch, settings):
    async def upload_blob(data, overwrite=False):
        settings.setdefault("blob_called", {"data": data, "overwrite": overwrite})

    fake_boto3 = SimpleNamespace(
        client=lambda *_: SimpleNamespace(
            put_object=lambda **kw: settings.setdefault("s3_called", kw)
        )
    )
    fake_blob = SimpleNamespace(
        BlobServiceClient=SimpleNamespace(
            from_connection_string=lambda *_: SimpleNamespace(
                get_container_client=lambda *_: SimpleNamespace(
                    get_blob_client=lambda *_: SimpleNamespace(upload_blob=upload_blob)
                )
            )
        )
    )
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)
    monkeypatch.setitem(sys.modules, "azure.storage.blob.aio", fake_blob)
    monkeypatch.setitem(
        sys.modules,
        "app.models",
        SimpleNamespace(
            Setting=SimpleNamespace(
                get=lambda name: SimpleNamespace(get_value=lambda: settings.get(name.lower()))
            )
        ),
    )
    monkeypatch.setitem(sys.modules, "app", sys.modules.get("app", SimpleNamespace()))
    spec = importlib.util.spec_from_file_location("app.storage", MODULE_PATH)
    storage = importlib.util.module_from_spec(spec)
    storage.__package__ = "app"
    spec.loader.exec_module(storage)
    return storage


@pytest.mark.asyncio
async def test_upload_local(tmp_path, monkeypatch):
    settings = {"use_s3": False, "use_azure": False}
    storage = load_storage(monkeypatch, settings)
    monkeypatch.setattr(storage, "basedir", str(tmp_path))
    await storage.upload_bytes(b"data", "foo/bar.txt")
    assert (tmp_path / "foo" / "bar.txt").read_bytes() == b"data"


@pytest.mark.asyncio
async def test_upload_s3(monkeypatch):
    settings = {"use_s3": True, "use_azure": False, "bucket_name": "buck"}
    storage = load_storage(monkeypatch, settings)
    await storage.upload_bytes(b"hi", "p.txt")
    assert settings["s3_called"] == {"Bucket": "buck", "Key": "p.txt", "Body": b"hi"}


@pytest.mark.asyncio
async def test_upload_azure(monkeypatch):
    settings = {"use_s3": False, "use_azure": True, "azure_container": "cont", "azure_connection_string": "conn"}
    storage = load_storage(monkeypatch, settings)
    await storage.upload_bytes(b"hi", "p.txt")
    assert settings["blob_called"] == {"data": b"hi", "overwrite": True}
