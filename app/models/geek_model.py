from typing import List, Optional, Union
from pydantic import BaseModel, Field, EmailStr, validator
from datetime import datetime, date
from enum import Enum
from bson import ObjectId
from .helper import PyObjectId

# Address Submodel
class Coordinates(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class Address(BaseModel):
    pin: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    line1: str
    line2: Optional[str] = None
    line3: Optional[str] = None
    coordinates: Optional[Coordinates] = None
# Enums
class ChargeTypeEnum(str, Enum):
    hourly = 'Hourly'
    per_ticket = 'Per Ticket'

class ModeOfServiceEnum(str, Enum):
    online = 'Online'
    offline = 'Offline'
    carry_in = 'Carry In'
    all = 'All'
    none = 'None'

class IdProofTypeEnum(str, Enum):
    aadhar = 'Aadhar'
    pan = 'PAN'

# Submodels
class RateCard(BaseModel):
    skill: PyObjectId
    chargeType: ChargeTypeEnum = ChargeTypeEnum.per_ticket
    rate: Optional[float] = None

class TimeSlot(BaseModel):
    from_: str = Field(..., alias='from')
    to: str

class Slot(BaseModel):
    day: str
    timeSlots: List[TimeSlot]

class Availability(BaseModel):
    slots: List[Slot]

class Certificate(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    name: Optional[str] = None
    fileUrl: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class ReviewReply(BaseModel):
    comment: str
    postedBy: PyObjectId  # can be Seeker or Geek but stored as ObjectId

class Review(BaseModel):
    rating: Optional[float] = None
    comment: Optional[str] = None
    postedBy: PyObjectId
    replies: List[ReviewReply] = []

class FullName(BaseModel):
    first: str
    last: str

class IdProof(BaseModel):
    type: IdProofTypeEnum = IdProofTypeEnum.aadhar
    idNumber: Optional[str] = None
    isAdhaarVerified: bool = False

# Main Geek base model
class GeekBase(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id")
    fullName: FullName
    email: EmailStr
    mobile: str
    isEmailVerified: bool = False
    isPhoneVerified: bool = False
    profileImage: Optional[str] = None
    primarySkill: PyObjectId
    secondarySkills: List[PyObjectId] = []
    description: Optional[str] = None
    modeOfService: ModeOfServiceEnum = ModeOfServiceEnum.none
    availability: Optional[Availability] = None
    rateCard: List[RateCard] = []
    brandsServiced: List[PyObjectId] = []
    profileCompleted: bool = False
    profileCompletedPercentage: float = 0.0
    address: Optional[Address] = None
    yoe: int = Field(default=0)
    reviews: List[Review] = []
    authToken: Optional[str] = None
    type: str  # Discriminator ('Individual' or 'Corporate')

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }


# IndividualGeek extending GeekBase
class IndividualGeek(GeekBase):
    dob: Optional[date] = None
    gender: Optional[str] = None
    qualifications: List[Certificate] = []
    idProof: Optional[IdProof] = None
    languagePreferences: List[str] = []

# CorporateGeek extending GeekBase
class CorporateGeek(GeekBase):
    companyName: str
    teamMembers: List[GeekBase] = []
    GSTIN: Optional[str] = None
    CIN: Optional[str] = None
    isVerified: bool = False
    companyDocs: List[Certificate] = []
    teamSize: Optional[int] = None
