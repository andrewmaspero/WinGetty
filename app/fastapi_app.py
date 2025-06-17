"""Minimal asynchronous API built with FastAPI."""

from __future__ import annotations

import asyncio
from typing import List

from fastapi import FastAPI, UploadFile, File, HTTPException
from .models import Package, PackageVersion, Installer, db
from .schemas import PackageSchema, PackageVersionSchema, InstallerSchema
from .storage import upload_bytes
from . import create_app

app = FastAPI(title="WinGetty Async API")

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


@app.get("/packages/{identifier}", response_model=PackageSchema)
async def get_package(identifier: str) -> PackageSchema:
    """Return a single package by its identifier."""
    package = await asyncio.to_thread(Package.query.filter_by(identifier=identifier).first)
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    return package


@app.get("/packages/{identifier}/versions", response_model=List[PackageVersionSchema])
async def list_versions(identifier: str) -> List[PackageVersionSchema]:
    """Return versions for a package."""
    package = await asyncio.to_thread(Package.query.filter_by(identifier=identifier).first)
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    return package.versions


@app.get(
    "/packages/{identifier}/versions/{version}", response_model=PackageVersionSchema
)
async def get_version(identifier: str, version: str) -> PackageVersionSchema:
    """Return a specific package version."""
    pv = await asyncio.to_thread(
        PackageVersion.query.filter_by(identifier=identifier, version_code=version).first
    )
    if not pv:
        raise HTTPException(status_code=404, detail="Version not found")
    return pv


@app.get(
    "/packages/{identifier}/versions/{version}/installers",
    response_model=List[InstallerSchema],
)
async def list_installers(identifier: str, version: str) -> List[InstallerSchema]:
    """Return installers for a version."""
    pv = await asyncio.to_thread(
        PackageVersion.query.filter_by(identifier=identifier, version_code=version).first
    )
    if not pv:
        raise HTTPException(status_code=404, detail="Version not found")
    return pv.installers

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

