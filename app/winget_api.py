from __future__ import annotations

import asyncio
from typing import List, Optional

from fastapi import APIRouter, Response
from pydantic import BaseModel
from sqlalchemy import or_

from .models import Package, Setting

router = APIRouter(prefix="/wg", tags=["winget"])


@router.get("/")
async def index() -> str:
    """Return a health check message."""
    return "WinGet API is running, see documentation for more information"


@router.get("/information")
async def information() -> dict:
    """Return repository information."""
    repo = await asyncio.to_thread(Setting.get("REPO_NAME").get_value)
    return {
        "Data": {
            "SourceIdentifier": repo,
            "ServerSupportedVersions": ["1.4.0", "1.5.0"],
        }
    }


@router.get("/packageManifests/{name}")
async def get_package_manifest(name: str):
    """Return a package manifest or 204 if not found."""
    package = await asyncio.to_thread(
        Package.query.filter_by(identifier=name).first
    )
    if package is None:
        return Response(status_code=204)
    return package.generate_output()


class ManifestField(BaseModel):
    KeyWord: str
    MatchType: str


class ManifestFilter(BaseModel):
    PackageMatchField: str
    RequestMatch: ManifestField


class ManifestSearchRequest(BaseModel):
    MaximumResults: int = 50
    Query: Optional[ManifestField] = None
    Filters: List[ManifestFilter] = []
    Inclusions: List[ManifestFilter] = []


@router.post("/manifestSearch")
async def manifest_search(payload: ManifestSearchRequest):
    """Search for packages using WinGet's manifestSearch schema."""
    maximum_results = payload.MaximumResults or 50
    packages_query = Package.query

    combined_filters = payload.Filters + payload.Inclusions
    filter_conditions = []

    if payload.Query:
        keyword = payload.Query.KeyWord
        match_type = payload.Query.MatchType
        if match_type == "Exact":
            filter_conditions.append(
                or_(Package.name == keyword, Package.identifier == keyword)
            )

    for entry in combined_filters:
        field_map = {
            "PackageName": Package.name,
            "PackageIdentifier": Package.identifier,
            "PackageFamilyName": Package.identifier,
            "ProductCode": Package.name,
            "Moniker": Package.name,
        }
        field = field_map.get(entry.PackageMatchField)
        if not field:
            continue
        keyword = entry.RequestMatch.KeyWord
        match_type = entry.RequestMatch.MatchType
        if match_type == "Exact":
            filter_conditions.append(field == keyword)
        elif match_type in ["Partial", "Substring", "CaseInsensitive"]:
            filter_conditions.append(field.ilike(f"%{keyword}%"))

    if filter_conditions:
        packages_query = packages_query.filter(or_(*filter_conditions))

    packages_query = packages_query.limit(maximum_results)
    packages = await asyncio.to_thread(packages_query.all)
    output_data = [
        package.generate_output_manifest_search()
        for package in packages
        if package.versions and any(v.installers for v in package.versions)
    ]
    if not output_data:
        return Response(status_code=204)
    return {"Data": output_data}
