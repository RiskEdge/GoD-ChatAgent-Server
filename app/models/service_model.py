from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime
from helper import PyObjectId


class FAQEntry(BaseModel):
    __root__: PyObjectId


class Overview(BaseModel):
    description: str
    benefits: Optional[List[str]] = []
    faqs: Optional[List[PyObjectId]] = []


class Image(BaseModel):
    public_id: Optional[str]
    url: Optional[str]


class Video(BaseModel):
    public_id: Optional[str]
    url: Optional[str]


class RatingReply(BaseModel):
    comment: Optional[str]
    postedBy: Optional[PyObjectId]


class Rating(BaseModel):
    star: Optional[float]
    comment: Optional[str]
    postedBy: Optional[PyObjectId]
    replies: Optional[List[RatingReply]] = []


class ServiceProviderEntry(BaseModel):
    provider: PyObjectId
    isMatched: Optional[bool] = False


class ServiceBase(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id")
    title: str
    slug: str
    overview: Overview
    price: float
    category: PyObjectId
    totalProviders: Optional[int] = 0
    timesRequested: Optional[int] = 0
    brands: Optional[List[PyObjectId]] = []
    serviceProviders: Optional[List[ServiceProviderEntry]] = []
    images: Optional[List[Image]] = []
    tags: Optional[List[PyObjectId]] = []
    video: Optional[Video]
    ratings: Optional[List[Rating]] = []
    totalRating: Optional[str] = "0"
    createdAt: Optional[datetime]
    updatedAt: Optional[datetime]

    class Config:
        allow_population_by_field_name = True
        json_encoders = {ObjectId: str}
        orm_mode = True

    @validator("slug")
    def slug_lowercase(cls, v):
        if v != v.lower():
            raise ValueError("Slug must be lowercase")
        return v
