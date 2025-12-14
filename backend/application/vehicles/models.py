from typing import Optional
from pydantic import BaseModel


class VehicleCreate(BaseModel):
    vehicle_type: str  # car, bike, auto, etc.
    make: Optional[str] = None
    model: Optional[str] = None
    color: Optional[str] = None
    license_plate: str
    max_capacity: int


class VehicleUpdate(BaseModel):
    vehicle_type: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    color: Optional[str] = None
    license_plate: Optional[str] = None
    max_capacity: Optional[int] = None


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
