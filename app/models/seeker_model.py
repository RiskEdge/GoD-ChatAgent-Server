from pydantic import BaseModel, Field, EmailStr, validator, root_validator
from typing import Optional
from enum import Enum
from datetime import datetime


class AuthProviderEnum(str, Enum):
    google = 'google'
    linkedin = 'linkedin'
    microsoft = 'microsoft'
    custom = 'custom'


class Coordinates(BaseModel):
    latitude: Optional[float]
    longitude: Optional[float]


class Address(BaseModel):
    pin: Optional[str]
    city: Optional[str]
    state: Optional[str]
    country: Optional[str]
    line1: str
    line2: Optional[str]
    line3: Optional[str]
    coordinates: Optional[Coordinates]


class FullName(BaseModel):
    first: str
    last: str


class Location(BaseModel):
    latitude: Optional[float]
    longitude: Optional[float]
    formattedAddress: Optional[str]


class SeekerBase(BaseModel):
    id: Optional[str] = Field(alias="_id")  # MongoDB _id, optional in input

    authProvider: AuthProviderEnum
    authProviderId: str

    email: Optional[EmailStr] = None
    isEmailVerified: bool = False

    phone: Optional[str] = None
    isPhoneVerified: bool = False

    fullName: FullName

    profileImage: Optional[str] = None

    address: Optional[Address] = None

    location: Optional[Location] = None

    profileCompleted: bool = False
    needsReminderToCompleteProfile: bool = True

    authToken: Optional[str] = None

    created_at: Optional[datetime] = Field(None, alias="createdAt")
    updated_at: Optional[datetime] = Field(None, alias="updatedAt")

    @root_validator(pre=True)
    def check_email_phone_required(cls, values):
        auth_provider = values.get('authProvider')
        email = values.get('email')
        phone = values.get('phone')

        if auth_provider != AuthProviderEnum.custom and not email:
            raise ValueError('email is required when authProvider is not "custom"')

        if auth_provider == AuthProviderEnum.custom and not phone:
            raise ValueError('phone is required when authProvider is "custom"')

        return values

    class Config:
        allow_population_by_field_name = True
        orm_mode = True
