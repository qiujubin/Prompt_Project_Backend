from pydantic import BaseModel
from typing import Optional

class SocialAccountRead(BaseModel):
    id: int
    user_id: int
    openid: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    nickname: Optional[str] = None
    unionid: Optional[str] = None
    class Config:
        from_attributes = True

class SocialAccountCreate(BaseModel):
    user_id: int
    openid: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    nickname: Optional[str] = None
    unionid: Optional[str] = None

class SocialAccountUpdate(BaseModel):
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    nickname: Optional[str] = None
    unionid: Optional[str] = None
