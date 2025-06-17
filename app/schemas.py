from pydantic import BaseModel, Field
from typing import List, Optional

class InstallerSwitchSchema(BaseModel):
    parameter: str
    value: str

class NestedInstallerFileSchema(BaseModel):
    relative_file_path: str
    portable_command_alias: Optional[str] = None

class InstallerSchema(BaseModel):
    id: int
    architecture: str
    installer_type: str
    file_name: Optional[str] = None
    external_url: Optional[str] = None
    installer_sha256: str
    scope: str
    nested_installer_type: Optional[str] = None
    nested_installer_files: List[NestedInstallerFileSchema] = []
    switches: List[InstallerSwitchSchema] = []

    class Config:
        orm_mode = True

class PackageVersionSchema(BaseModel):
    id: int
    version_code: str
    package_locale: Optional[str] = None
    short_description: Optional[str] = None
    installers: List[InstallerSchema] = []

    class Config:
        orm_mode = True

class PackageSchema(BaseModel):
    id: int
    identifier: str
    name: str
    publisher: str
    download_count: int
    versions: List[PackageVersionSchema] = []

    class Config:
        orm_mode = True
