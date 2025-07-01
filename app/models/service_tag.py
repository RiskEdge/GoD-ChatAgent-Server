from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
from helper import PyObjectId
from bson import ObjectId


class Tag(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id")
    title: str
    slug: str
    createdAt: Optional[datetime]
    updatedAt: Optional[datetime]

    @validator("slug")
    def slug_must_be_lowercase(cls, v):
        if v != v.lower():
            raise ValueError("Slug must be lowercase")
        return v

    class Config:
        validate_by_name = True
        from_attributes = True
        json_encoders = {ObjectId: str}
        
