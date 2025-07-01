from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class FAQ(BaseModel):
    question: str
    answer: str
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None

    class Config:
        validate_by_name = True
        from_attributes = True