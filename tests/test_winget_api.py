import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace
import types
from fastapi.testclient import TestClient

pytest_plugins = ["pytest_asyncio"]

APP_PATH = Path(__file__).resolve().parents[1] / "app" / "fastapi_app.py"


def load_app(monkeypatch, package=None):
    class FakeQuery:
        def __init__(self, result=None):
            self.result = result
        def filter_by(self, **kw):
            return self
        def first(self):
            return self.result
        def all(self):
            return [self.result] if self.result else []
        def limit(self, *a, **kw):
            return self
        def filter(self, *a, **kw):
            return self

    fake_models = SimpleNamespace(
        Package=SimpleNamespace(query=FakeQuery(package)),
        PackageVersion=None,
        Installer=None,
        db=SimpleNamespace(session=SimpleNamespace(add=lambda *a, **kw: None, commit=lambda: None)),
        Setting=SimpleNamespace(get=lambda name: SimpleNamespace(get_value=lambda: "Repo")),
    )

    dummy_ctx = SimpleNamespace(app_context=lambda: SimpleNamespace(push=lambda: None))
    winget_module_path = Path(__file__).resolve().parents[1] / "app" / "winget_api.py"
    spec2 = importlib.util.spec_from_file_location("app.winget_api", winget_module_path)
    winget_module = importlib.util.module_from_spec(spec2)
    winget_module.__package__ = "app"

    fake_app_pkg = types.ModuleType("app")
    fake_app_pkg.__path__ = []
    fake_app_pkg.create_app = lambda: dummy_ctx
    monkeypatch.setitem(sys.modules, "app", fake_app_pkg)
    monkeypatch.setitem(sys.modules, "app.models", fake_models)
    fake_schema_mod = types.ModuleType("schemas")
    fake_schema_mod.PackageSchema = object
    monkeypatch.setitem(sys.modules, "app.schemas", fake_schema_mod)
    fake_storage = types.ModuleType("storage")
    fake_storage.upload_bytes = lambda *a, **kw: None
    monkeypatch.setitem(sys.modules, "app.storage", fake_storage)
    monkeypatch.setitem(sys.modules, "app.winget_api", winget_module)

    spec2.loader.exec_module(winget_module)

    spec = importlib.util.spec_from_file_location("app.fastapi_app", APP_PATH)
    module = importlib.util.module_from_spec(spec)
    module.__package__ = "app"
    spec.loader.exec_module(module)
    return module.app


def test_information(monkeypatch):
    app = load_app(monkeypatch)
    client = TestClient(app)
    resp = client.get("/wg/information")
    assert resp.status_code == 200
    assert resp.json()["Data"]["SourceIdentifier"] == "Repo"


def test_manifest_not_found(monkeypatch):
    app = load_app(monkeypatch, None)
    client = TestClient(app)
    resp = client.get("/wg/packageManifests/foo")
    assert resp.status_code == 204


def test_manifest_found(monkeypatch):
    pkg = SimpleNamespace(generate_output=lambda: {"foo": "bar"}, versions=[], installers=[])
    app = load_app(monkeypatch, pkg)
    client = TestClient(app)
    resp = client.get("/wg/packageManifests/foo")
    assert resp.status_code == 200
    assert resp.json() == {"foo": "bar"}
