"""Minimal asynchronous API built with FastAPI."""

from __future__ import annotations

import asyncio
from typing import List

from fastapi import FastAPI, UploadFile, File, HTTPException
from .models import Package, PackageVersion, Installer, db
from .winget_api import router as winget_router
from .schemas import PackageSchema
from .storage import upload_bytes
from . import create_app

app = FastAPI(title="WinGetty Async API")
app.include_router(winget_router)

@app.on_event("startup")
async def startup() -> None:
    # Initialize Flask application context for SQLAlchemy
    flask_app = create_app()
    flask_app.app_context().push()

@app.get("/packages", response_model=List[PackageSchema])
async def list_packages() -> List[PackageSchema]:
    """Return all packages."""
    packages = await asyncio.to_thread(Package.query.all)
    return packages  # FastAPI will use orm_mode

@app.post("/packages/{identifier}/versions/{version}/installers")
async def upload_installer(identifier: str, version: str, file: UploadFile = File(...)) -> dict:
    """Upload an installer and store metadata in the database."""
    package_version = await asyncio.to_thread(
        PackageVersion.query.filter_by(identifier=identifier, version_code=version).first
    )
    if not package_version:
        raise HTTPException(status_code=404, detail="Version not found")
    data = await file.read()
    path = f"packages/{identifier}/{version}/{file.filename}"
    await upload_bytes(data, path)
    installer = Installer(
        version_id=package_version.id,
        architecture="unknown",
        installer_type="exe",
        file_name=file.filename,
        installer_sha256="",
        scope="machine",
    )
    db.session.add(installer)
    db.session.commit()
    return {"status": "uploaded", "path": path}

