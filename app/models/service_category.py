from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime
from bson import ObjectId

from .helper import PyObjectId

class CategoryBase(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id")
    title: str
    slug: str
    subCategories: List[PyObjectId] = []

    created_at: Optional[datetime] = Field(None, alias="createdAt")
    updated_at: Optional[datetime] = Field(None, alias="updatedAt")

    @validator('slug')
    def slug_must_be_lowercase(cls, v):
        if v != v.lower():
            raise ValueError('slug must be lowercase')
        return v

    class Config:
        allow_population_by_field_name = True
        json_encoders = {ObjectId: str}
        orm_mode = True
