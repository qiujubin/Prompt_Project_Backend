from pydantic import BaseModel
from typing import Optional

class DrawingCreate(BaseModel):
    prompt: str
    model_name: str
    negative_prompt: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    seed: Optional[str] = None

class DrawingRead(BaseModel):
    id: int
    prompt: str
    negative_prompt: Optional[str] = None
    image_url: Optional[str] = None
    status: str

    class Config:
        from_attributes = True

class DrawingUpdate(BaseModel):
    prompt: Optional[str] = None
    negative_prompt: Optional[str] = None
    image_url: Optional[str] = None
    status: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    seed: Optional[str] = None
    model_name: Optional[str] = None
