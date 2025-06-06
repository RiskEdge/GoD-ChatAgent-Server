from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from enum import Enum


class ModeEnum(str, Enum):
    Online = "Online"
    Offline = "Offline"
    All = "All"
    CarryIn = "Carry In"


class StatusEnum(str, Enum):
    Pending = "Pending"
    Matched = "Matched"
    Accepted = "Accepted"
    Rejected = "Rejected"
    Completed = "Completed"
    Cancelled = "Cancelled"


class GeekResponseStatusEnum(str, Enum):
    Pending = "Pending"
    Accepted = "Accepted"
    Rejected = "Rejected"


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


class ServiceRequest(BaseModel):
    service: Service
    seeker: Seeker
    geek: Optional[Geek]
    questionnaireResponses: Optional[Dict[str, Any]] = Field(default_factory=dict)
    mode: ModeEnum
    scheduledAt: datetime
    location: Optional[Address]
    status: StatusEnum = StatusEnum.Pending
    geekResponseStatus: GeekResponseStatusEnum = GeekResponseStatusEnum.Pending
    responseAt: Optional[datetime]
    createdAt: Optional[datetime]
    updatedAt: Optional[datetime]
