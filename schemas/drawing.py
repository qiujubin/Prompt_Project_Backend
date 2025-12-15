from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class DrawingCreate(BaseModel):
    title: Optional[str] = None
    prompt: str
    model_name: str
    negative_prompt: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    seed: Optional[str] = None
    image_url: Optional[str] = None # Allow manual creation with URL
    ai_response_time_ms: Optional[int] = None

class DrawingRead(BaseModel):
    id: int
    user_id: int
    title: Optional[str] = None
    prompt: str
    negative_prompt: Optional[str] = None
    model_name: str
    image_url: Optional[str] = None
    status: str
    width: Optional[int] = None
    height: Optional[int] = None
    seed: Optional[str] = None
    created_at: datetime
    is_public: bool = False
    
    # Community stats
    view_count: int = 0
    like_count: int = 0
    favorite_count: int = 0
    comment_count: int = 0

    # User context (optional, filled if user is logged in)
    is_liked: Optional[bool] = False
    is_favorited: Optional[bool] = False
    
    # Creator info
    username: Optional[str] = None
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None

    class Config:
        from_attributes = True

class DrawingUpdate(BaseModel):
    title: Optional[str] = None
    prompt: Optional[str] = None
    negative_prompt: Optional[str] = None
    image_url: Optional[str] = None
    status: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    seed: Optional[str] = None
    model_name: Optional[str] = None
    is_public: Optional[bool] = None
