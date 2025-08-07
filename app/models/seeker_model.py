from pydantic import BaseModel, Field, EmailStr, root_validator
from typing import Optional, List
from enum import Enum
from datetime import datetime
from .helper import PyObjectId
from bson import ObjectId


class AuthProviderEnum(str, Enum):
    google = 'google'
    linkedin = 'linkedin'
    microsoft = 'microsoft'
    custom = 'custom'


class Coordinates(BaseModel):
    latitude: Optional[float]
    longitude: Optional[float]
    
class Location(BaseModel):
    latitude: Optional[float]= None
    longitude: Optional[float]= None
    formattedAddress: Optional[str]= None


class Address(BaseModel):
    pin: Optional[str]= None
    city: Optional[str]= None
    state: Optional[str]= None
    country: Optional[str]= None
    line1: str
    line2: Optional[str] = None
    line3: Optional[str]= None
    coordinates: Optional[Coordinates]= None
    location: Optional[Location]= None


class FullName(BaseModel):
    first: str
    last: str


class SeekerBase(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id")  # MongoDB _id, optional in input

    authProvider: AuthProviderEnum
    authProviderId: str

    email: Optional[EmailStr] = None
    isEmailVerified: bool = False

    phone: Optional[str] = None
    isPhoneVerified: bool = False

    fullName: FullName

    profileImage: Optional[str] = None

    address: Optional[Address] = None

    profileCompleted: bool = False
    needsReminderToCompleteProfile: bool = True

    authToken: Optional[str] = None
    requests: Optional[List[PyObjectId]] = []

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
        validate_by_name = True
        from_attributes = True
        json_encoders = {ObjectId: str}
