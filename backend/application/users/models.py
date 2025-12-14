from typing import Optional, List
import re
from pydantic import BaseModel, Field, field_validator, EmailStr


class EmergencyContact(BaseModel):
    phone_no: str = Field(..., min_length=10, max_length=15)
    name: str = Field(..., min_length=1, max_length=100)
    country_code: str = Field("+91", max_length=5)
    relationship: Optional[str] = Field(None, max_length=50)

    @field_validator('phone_no')
    @classmethod
    def validate_phone(cls, v):
        # Remove any non-digit characters for validation
        digits = re.sub(r'\D', '', v)
        if len(digits) < 10 or len(digits) > 15:
            raise ValueError("Phone number must be 10-15 digits")
        return v


class UserCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    phone_no: str = Field(..., min_length=10, max_length=15)
    password: str = Field(..., min_length=8, max_length=128)
    country_code: str = Field("+91", max_length=5)
    email: Optional[EmailStr] = None
    bio: Optional[str] = Field(None, max_length=500)
    emergency_contact: Optional[List[EmergencyContact]] = Field(None, max_length=5)

    @field_validator('phone_no')
    @classmethod
    def validate_phone(cls, v):
        digits = re.sub(r'\D', '', v)
        if len(digits) < 10 or len(digits) > 15:
            raise ValueError("Phone number must be 10-15 digits")
        return v

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r'[A-Za-z]', v):
            raise ValueError("Password must contain at least one letter")
        if not re.search(r'\d', v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserLogin(BaseModel):
    phone_no: str = Field(..., min_length=10, max_length=15)
    password: str = Field(..., min_length=1, max_length=128)
    country_code: str = Field("+91", max_length=5)


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
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    email: Optional[EmailStr] = None
    bio: Optional[str] = Field(None, max_length=500)
    profile_picture_url: Optional[str] = Field(None, max_length=500)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
