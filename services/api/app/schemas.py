"""Legacy internal B1 input contracts; B2 consumes published results read-only."""
from typing import Any, Literal
from urllib.parse import urlsplit, unquote

from pydantic import BaseModel, ConfigDict, Field, field_validator


def validate_storage_uri(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.query or parsed.fragment or parsed.username or parsed.password:
        raise ValueError("storage URI must identify an immutable object without credentials/query/fragment")
    path = unquote(parsed.path)
    if "\\" in path or any(part in {".", ".."} for part in path.split("/")):
        raise ValueError("storage URI cannot contain traversal")
    if parsed.scheme == "s3":
        if not parsed.netloc or not path.strip("/"):
            raise ValueError("S3 URI requires a bucket and object key")
    elif parsed.scheme == "file":
        if parsed.netloc not in {"", "localhost"} or not path.startswith("/") or not path.strip("/"):
            raise ValueError("file URI requires an absolute local path")
    else:
        raise ValueError("storage URI must use s3:// or file://")
    return value


StorageUri = str


class InputAssetManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_type: str = Field(min_length=1, max_length=100)
    storage_uri: StorageUri = Field(min_length=8, max_length=2048)
    checksum: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    dataset_version: str = Field(min_length=1, max_length=100)

    @field_validator("storage_uri")
    @classmethod
    def require_supported_storage_scheme(cls, value: str) -> str:
        return validate_storage_uri(value)


class ScenarioManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{2,149}$")
    scenario_type: str = Field(min_length=1, max_length=50)
    model_version: str = Field(min_length=1, max_length=100)
    input_dataset_version: str = Field(min_length=1, max_length=100)
    crs: str = Field(pattern=r"^EPSG:\d+$")
    time_step_minutes: int | None = Field(default=None, gt=0)
    parameters: dict[str, Any] = Field(default_factory=dict)
    assumptions_url: str | None = None
    data_mode: Literal["demo", "production"] = "demo"
    inputs: list[InputAssetManifest] = Field(min_length=1)

    @field_validator("assumptions_url")
    @classmethod
    def validate_assumptions_url(cls, value: str | None) -> str | None:
        if value and not value.startswith(("s3://", "file://", "https://")):
            raise ValueError("assumptions_url must use s3://, file://, or https://")
        return value

    @field_validator("inputs")
    @classmethod
    def reject_duplicate_inputs(cls, values: list[InputAssetManifest]) -> list[InputAssetManifest]:
        if len({item.input_type for item in values}) != len(values):
            raise ValueError("input_type must be unique within a manifest")
        return values


class ScenarioRegistration(ScenarioManifest):
    """The persisted representation is intentionally the same as the manifest."""
