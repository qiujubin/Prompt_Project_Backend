from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    username: str
    password: str
    email: Optional[str] = None

class UserRead(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    role: Optional[str] = "user"
    avatar_url: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    avatar_url: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    source: Optional[str] = None
