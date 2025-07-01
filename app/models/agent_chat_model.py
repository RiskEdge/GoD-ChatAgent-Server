from  pydantic import BaseModel, Field
from typing import Optional, Union
from enum import Enum
from datetime import datetime, timezone
import uuid

from .helper import PyObjectId

#Enum to define the sender of message
class MessageSender(str, Enum):
    USER = "user"
    BOT = "bot"
    
#Enum for the status of reported issue
class IssueStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    IN_PROGRESS = "in_progress"
    
# --- Models for storing individual chat messages --- #
class ChatMessageBase(BaseModel):
    conversation_id: str = Field(..., description="The ID of the conversation to which the message belongs.")
    sender: MessageSender = Field(..., description="Who sent the message.")
    message: str = Field(..., description="The content of the message.")
    sentAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="The timestamp of the message.")
    
class ChatMessageCreate(ChatMessageBase):
    user_id: Union[str, PyObjectId] 
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
class ChatMessageInDB(ChatMessageCreate):
    id: Optional[Union[str, PyObjectId]] = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    
    class Config:
        validate_by_name = True
        from_attributes = True
            
    