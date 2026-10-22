"""Owner-facing building contracts; ownership and audit fields are server-owned."""
from datetime import datetime
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

BuildingType = Literal["Residential", "Office", "Educational", "Healthcare", "Retail", "Industrial", "Other"]
Area = Annotated[float, Field(strict=True, allow_inf_nan=False, gt=0)]


class BuildingFields(BaseModel):
    model_config = ConfigDict(extra="forbid")
    building_type: BuildingType | None = None
    floor_area_m2: Area | None = None
    city: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=4000)

    @field_validator("city", mode="before")
    @classmethod
    def trim_city(cls, value):
        return value.strip() or None if isinstance(value, str) else value

    @field_validator("name", mode="before", check_fields=False)
    @classmethod
    def trim_name(cls, value):
        return value.strip() if isinstance(value, str) else value


class BuildingCreate(BuildingFields):
    name: str = Field(min_length=1, max_length=200)


class BuildingUpdate(BuildingFields):
    name: str | None = Field(default=None, min_length=1, max_length=200)

    @model_validator(mode="after")
    def valid_patch(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one editable field")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("Building name cannot be null")
        return self


class BuildingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    building_type: BuildingType | None
    floor_area_m2: float | None
    city: str | None
    description: str | None
    created_at: datetime
    updated_at: datetime


class BuildingListResponse(BaseModel):
    buildings: list[BuildingResponse]
