from pydantic import BaseModel, Field
from typing import Optional, Union, Dict, Any
from datetime import datetime
from bson import ObjectId
from enum import Enum
from helper import PyObjectId


class AadhaarVerificationStatus(str, Enum):
    completed = "completed"
    in_progress = "in_progress"
    error = "error"


class AadhaarVerification(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id")
    geek: PyObjectId
    idNumber: str
    status: AadhaarVerificationStatus = AadhaarVerificationStatus.error
    response: Optional[Union[Dict[str, Any], Any]] = None
    verifiedAt: Optional[datetime] = Field(default_factory=datetime.now(datetime.timezone.utc))
    requestId: str

    createdAt: Optional[datetime]
    updatedAt: Optional[datetime]

    class Config:
        validate_by_name = True
        from_attributes = True
        json_encoders = {ObjectId: str}
