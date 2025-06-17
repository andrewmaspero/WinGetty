import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

MODULE_PATH = Path(__file__).resolve().parents[1] / "app" / "fastapi_app.py"

class DummyQuery:
    def __init__(self, items):
        self._items = items
    def all(self):
        return self._items
    def filter_by(self, **kw):
        filtered = [i for i in self._items if all(getattr(i, k) == v for k, v in kw.items())]
        return DummyQuery(filtered)
    def first(self):
        return self._items[0] if self._items else None

def load_app(monkeypatch, data):
    Package = SimpleNamespace(query=DummyQuery(data.get("packages", [])))
    PackageVersion = SimpleNamespace(query=DummyQuery(data.get("versions", [])))
    Installer = lambda **kw: SimpleNamespace(**kw)
    db = SimpleNamespace(session=SimpleNamespace(add=lambda x: data.setdefault("added", x), commit=lambda: None))
    async def upload_bytes(data_bytes, path):
        data.setdefault("uploaded", path)

    storage = SimpleNamespace(upload_bytes=upload_bytes)

    def create_app():
        return SimpleNamespace(app_context=lambda: SimpleNamespace(push=lambda: None))

    monkeypatch.setitem(sys.modules, "app.models", SimpleNamespace(Package=Package, PackageVersion=PackageVersion, Installer=Installer, db=db))
    monkeypatch.setitem(sys.modules, "app.storage", storage)
    monkeypatch.setitem(sys.modules, "app", SimpleNamespace(create_app=create_app))
    # load real schemas module under the app package name
    schemas_spec = importlib.util.spec_from_file_location("app.schemas", Path(__file__).resolve().parents[1] / "app" / "schemas.py")
    schemas_mod = importlib.util.module_from_spec(schemas_spec)
    schemas_spec.loader.exec_module(schemas_mod)
    monkeypatch.setitem(sys.modules, "app.schemas", schemas_mod)

    spec = importlib.util.spec_from_file_location("app.fastapi_app", MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = "app"
    spec.loader.exec_module(mod)
    return TestClient(mod.app)


def test_list_packages(monkeypatch):
    pkg = SimpleNamespace(id=1, identifier="foo", name="Foo", publisher="Bar", download_count=0, versions=[])
    client = load_app(monkeypatch, {"packages": [pkg]})
    resp = client.get("/packages")
    assert resp.status_code == 200
    assert resp.json() == [{"id": 1, "identifier": "foo", "name": "Foo", "publisher": "Bar", "download_count": 0, "versions": []}]


def test_get_package_not_found(monkeypatch):
    client = load_app(monkeypatch, {"packages": []})
    resp = client.get("/packages/foo")
    assert resp.status_code == 404


def test_upload_installer(monkeypatch):
    version = SimpleNamespace(id=1, identifier="foo", version_code="1.0", installers=[])
    data = {"packages": [], "versions": [version]}
    client = load_app(monkeypatch, data)
    resp = client.post("/packages/foo/versions/1.0/installers", files={"file": ("a.txt", b"hi")})
    assert resp.status_code == 200
    assert data["uploaded"] == "packages/foo/1.0/a.txt"
    assert data["added"].file_name == "a.txt"
