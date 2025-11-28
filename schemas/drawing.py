from pydantic import BaseModel
from typing import Optional

class DrawingCreate(BaseModel):
    prompt: str
    negative_prompt: Optional[str] = None

class DrawingRead(BaseModel):
    id: int
    prompt: str
    negative_prompt: Optional[str] = None
    image_url: Optional[str] = None
    status: str

    class Config:
        from_attributes = True