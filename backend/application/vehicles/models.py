from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator
import re


VALID_VEHICLE_TYPES = {'car', 'bike', 'auto', 'suv', 'van', 'bus'}


class VehicleCreate(BaseModel):
    vehicle_type: str = Field(..., min_length=1, max_length=20)
    make: Optional[str] = Field(None, max_length=50)
    model: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=30)
    license_plate: str = Field(..., min_length=1, max_length=20)
    max_capacity: int = Field(..., ge=1, le=50)

    @field_validator('vehicle_type')
    @classmethod
    def validate_vehicle_type(cls, v):
        v_lower = v.lower().strip()
        if v_lower not in VALID_VEHICLE_TYPES:
            raise ValueError(f"vehicle_type must be one of: {', '.join(VALID_VEHICLE_TYPES)}")
        return v_lower

    @field_validator('license_plate')
    @classmethod
    def validate_license_plate(cls, v):
        # Basic validation - alphanumeric with optional spaces/hyphens
        cleaned = re.sub(r'[\s\-]', '', v).upper()
        if not re.match(r'^[A-Z0-9]+$', cleaned):
            raise ValueError("License plate must contain only letters and numbers")
        return v.upper().strip()


class VehicleUpdate(BaseModel):
    vehicle_type: Optional[str] = Field(None, min_length=1, max_length=20)
    make: Optional[str] = Field(None, max_length=50)
    model: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=30)
    license_plate: Optional[str] = Field(None, min_length=1, max_length=20)
    max_capacity: Optional[int] = Field(None, ge=1, le=50)

    @field_validator('vehicle_type')
    @classmethod
    def validate_vehicle_type(cls, v):
        if v is None:
            return v
        v_lower = v.lower().strip()
        if v_lower not in VALID_VEHICLE_TYPES:
            raise ValueError(f"vehicle_type must be one of: {', '.join(VALID_VEHICLE_TYPES)}")
        return v_lower

    @field_validator('license_plate')
    @classmethod
    def validate_license_plate(cls, v):
        if v is None:
            return v
        cleaned = re.sub(r'[\s\-]', '', v).upper()
        if not re.match(r'^[A-Z0-9]+$', cleaned):
            raise ValueError("License plate must contain only letters and numbers")
        return v.upper().strip()


class Vehicle(BaseModel):
    id: int
    user_id: int
    vehicle_type: str
    make: Optional[str] = None
    model: Optional[str] = None
    color: Optional[str] = None
    license_plate: str
    max_capacity: int
    is_active: bool = True
