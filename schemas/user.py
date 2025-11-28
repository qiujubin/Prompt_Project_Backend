from pydantic import BaseModel, EmailStr
from typing import Optional

class UserCreate(BaseModel):
    username: str
    password: str
    email: Optional[EmailStr] = None

class UserRead(BaseModel):
    id: int
    username: str
    email: Optional[EmailStr] = None
    role: str

    class Config:
        from_attributes = True