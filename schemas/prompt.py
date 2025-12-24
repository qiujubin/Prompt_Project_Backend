from pydantic import BaseModel
from typing import Optional, List

class PromptCategoryRead(BaseModel):
    id: int
    name: str
    display_name: str
    sort_order: Optional[int] = 0
    class Config:
        from_attributes = True

class PromptCategoryCreate(BaseModel):
    name: str
    display_name: str
    sort_order: Optional[int] = 0

class PromptCategoryUpdate(BaseModel):
    name: Optional[str] = None
    display_name: Optional[str] = None
    sort_order: Optional[int] = None

class PromptSubcategoryRead(BaseModel):
    id: int
    category_id: int
    name: str
    display_name: str
    sort_order: Optional[int] = 0
    class Config:
        from_attributes = True

class PromptSubcategoryCreate(BaseModel):
    category_id: int
    name: str
    display_name: str
    sort_order: Optional[int] = 0

class PromptSubcategoryUpdate(BaseModel):
    category_id: Optional[int] = None
    name: Optional[str] = None
    display_name: Optional[str] = None
    sort_order: Optional[int] = None

class PromptKeywordRead(BaseModel):
    id: int
    word: str
    small_category_id: Optional[int] = None
    created_by: Optional[int] = None
    usage_count: Optional[int] = 0
    class Config:
        from_attributes = True

class PromptKeywordCreate(BaseModel):
    word: str
    display_name: Optional[str] = None
    small_category_id: int
    user_id: Optional[int] = None

class PromptKeywordUpdate(BaseModel):
    word: Optional[str] = None
    display_name: Optional[str] = None
    small_category_id: Optional[int] = None
    created_by: Optional[int] = None

class PromptTreeItem(BaseModel):
    name: str
    label: str
    children: List[dict] | None = None

# Translation Schemas
class TranslateItem(BaseModel):
    word: str = ""
    translation: str = ""

class TranslateRequest(BaseModel):
    items: List[TranslateItem]
    engine: str = "baidu" # 'baidu' or 'deepseek'

class TranslateResponse(BaseModel):
    items: List[TranslateItem]
