from pydantic import BaseModel
from typing import Optional

class PromptLogRead(BaseModel):
    id: int
    user_id: int
    used_at: str
    small_category_id: int
    weight: float
    is_negative: Optional[bool] = None
    drawing_id: Optional[int] = None
    class Config:
        from_attributes = True

class PromptLogCreate(BaseModel):
    user_id: int
    small_category_id: int
    weight: float
    is_negative: Optional[bool] = None
    drawing_id: Optional[int] = None

class PromptLogUpdate(BaseModel):
    weight: Optional[float] = None
    is_negative: Optional[bool] = None
    drawing_id: Optional[int] = None
