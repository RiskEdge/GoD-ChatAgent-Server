from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class Brand(BaseModel):
    name: str = Field(..., description="Unique name of the brand")
    slug: str = Field(..., description="Unique lowercase slug")
    description: Optional[str] = None
    image: Optional[str] = None
    createdAt: Optional[datetime]
    updatedAt: Optional[datetime]

    class Config:
        allow_population_by_field_name = True