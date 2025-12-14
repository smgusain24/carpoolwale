from typing import Optional, List
from pydantic import BaseModel


class EmergencyContact(BaseModel):
    phone_no: str
    name: str
    country_code: str = "+91"
    relationship: Optional[str] = None


class UserCreate(BaseModel):
    first_name: str
    last_name: str
    phone_no: str
    password: str
    country_code: str = "+91"
    email: Optional[str] = None
    bio: Optional[str] = None
    emergency_contact: Optional[List[EmergencyContact]] = None


class UserLogin(BaseModel):
    phone_no: str
    password: str
    country_code: str = "+91"


class UserProfile(BaseModel):
    id: int
    first_name: str
    last_name: str
    phone_no: str
    email: Optional[str] = None
    bio: Optional[str] = None
    profile_picture_url: Optional[str] = None
    is_verified: bool = False
    is_active: bool = True


class ProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    bio: Optional[str] = None
    profile_picture_url: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
