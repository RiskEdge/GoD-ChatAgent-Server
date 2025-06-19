from pydantic import BaseModel, Field
from typing import Optional, Union
from datetime import datetime, date, timezone
import uuid
from bson import ObjectId

from .agent_chat_model import IssueStatus
from .helper import PyObjectId


# --- Models for storing the structured user issue ---

class DeviceDetails(BaseModel):
    brand: Optional[str] = None
    model: Optional[str] = None
    device_type: Optional[str] = None
    os_version: Optional[str] = None

class PurchaseInformation(BaseModel):
    purchase_date: Optional[Union[str, date]] = None
    warranty_status: Optional[str] = None
    purchase_location: Optional[str] = None

class ProblemDescription(BaseModel):
    symptoms: Optional[str] = None
    error_messages: Optional[str] = None
    frequency: Optional[str] = None
    trigger: Optional[str] = None
    troubleshooting_attempts: Optional[str] = None

class UserIssueBase(BaseModel):
    user_id: Optional[Union[str, PyObjectId]] = Field(..., description="The ID of the user reporting the issue.")
    conversation_id: str = Field(..., description="The ID of the conversation where this issue was reported.")
    status: IssueStatus = Field(default=IssueStatus.OPEN, description="The current status of the issue.")
    
    device_details: DeviceDetails = None
    purchase_info: PurchaseInformation = None
    problem_description: ProblemDescription = None
    
    summary: str = Field(..., description="The final summary of the issue confirmed by the agent.")

class UserIssueCreate(UserIssueBase):
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), alias="createdAt")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), alias="updatedAt")

class UserIssueInDB(UserIssueCreate):
    id: Optional[Union[str, PyObjectId]] = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")

    class Config:
        allow_population_by_field_name = True
        orm_mode = True
        json_encoders = {ObjectId: str}
