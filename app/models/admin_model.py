from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class RoleEnum(str, Enum):
    Admin = "Admin"


class Admin(BaseModel):
    name: str = Field(...)
    email: EmailStr = Field(...)
    password: str = Field(...)
    role: RoleEnum = Field(default=RoleEnum.Admin)
    createdAt: Optional[datetime]
    updatedAt: Optional[datetime]
