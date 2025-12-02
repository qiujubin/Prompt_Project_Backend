from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# Comment Schemas
class CommentBase(BaseModel):
    content: str
    parent_id: Optional[int] = None

class CommentCreate(CommentBase):
    pass # drawing_id is in path param usually, but ok if here too

class CommentRead(CommentBase):
    id: int
    user_id: int
    drawing_id: int
    created_at: datetime
    username: Optional[str] = None
    avatar_url: Optional[str] = None

    class Config:
        from_attributes = True

# Interaction Response
class InteractionResponse(BaseModel):
    status: str # "liked", "unliked", "favorited", "unfavorited"
    count: int
