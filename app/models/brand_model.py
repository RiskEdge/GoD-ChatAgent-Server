from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from .helper import PyObjectId


class Brand(BaseModel):
    name: str = Field(..., description="Unique name of the brand")
    slug: str = Field(..., description="Unique lowercase slug")
    description: Optional[str] = None
    image: Optional[str] = None
    category: PyObjectId
    createdAt: Optional[datetime]
    updatedAt: Optional[datetime]

    class Config:
        validate_by_name = True
        from_attributes = True