"""预设相关的 Pydantic Schema 定义。

定义预设系统的请求/响应模型，包括：
- PresetItemCreate: 创建预设项的请求模型
- PresetItemRead: 预设项的响应模型
- PresetCreate: 创建预设的请求模型
- PresetUpdate: 更新预设的请求模型
- PresetRead: 预设的响应模型
- PresetListRead: 预设列表项的响应模型

Requirements: 5.3, 5.4, 5.5
- 5.3: THE creation dialog SHALL allow users to input preset name (English) and display_name (Chinese)
- 5.4: THE creation dialog SHALL allow users to select prompts from any category
- 5.5: THE creation dialog SHALL allow users to set individual weights for each selected prompt
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime


class PresetItemCreate(BaseModel):
    """创建预设项的请求模型。

    用于在创建或更新预设时指定包含的提示词及其权重。
    """
    keyword_id: int = Field(..., description="关联的提示词ID")
    weight: float = Field(default=1.0, ge=0.1, le=2.0, description="提示词权重，范围 0.1-2.0")
    sort_order: int = Field(default=0, ge=0, description="排序顺序")


class PresetItemRead(BaseModel):
    """预设项的响应模型。

    返回预设项的完整信息，包括关联的提示词详情。
    """
    id: int
    preset_id: int
    keyword_id: int
    weight: float
    sort_order: int
    # 关联的提示词信息
    keyword_word: Optional[str] = None
    keyword_display_name: Optional[str] = None

    class Config:
        from_attributes = True


class PresetCreate(BaseModel):
    """创建预设的请求模型。

    Requirements: 5.3, 5.4, 5.5, 5.8, 5.9
    """
    name: str = Field(..., min_length=1, max_length=256, description="预设英文名称")
    display_name: str = Field(..., min_length=1, max_length=256, description="预设中文显示名称")
    items: List[PresetItemCreate] = Field(..., min_length=1, description="预设包含的提示词列表")

    @field_validator('name', 'display_name')
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('名称不能为空')
        return v.strip()

    @field_validator('items')
    @classmethod
    def validate_items_not_empty(cls, v: List[PresetItemCreate]) -> List[PresetItemCreate]:
        if not v:
            raise ValueError('预设必须包含至少一个提示词')
        return v


class PresetUpdate(BaseModel):
    """更新预设的请求模型。

    Requirements: 6.3, 6.4, 6.5, 6.6
    """
    name: Optional[str] = Field(None, min_length=1, max_length=256, description="预设英文名称")
    display_name: Optional[str] = Field(None, min_length=1, max_length=256, description="预设中文显示名称")
    items: Optional[List[PresetItemCreate]] = Field(None, description="预设包含的提示词列表")

    @field_validator('name', 'display_name')
    @classmethod
    def validate_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError('名称不能为空')
        return v.strip() if v else v

    @field_validator('items')
    @classmethod
    def validate_items_not_empty(cls, v: Optional[List[PresetItemCreate]]) -> Optional[List[PresetItemCreate]]:
        if v is not None and len(v) == 0:
            raise ValueError('预设必须包含至少一个提示词')
        return v


class PresetRead(BaseModel):
    """预设的完整响应模型。

    用于获取预设详情时返回完整信息。
    Requirements: 3.2, 3.3, 3.4
    """
    id: int
    name: str
    display_name: str
    subcategory_id: Optional[int] = None
    created_by: Optional[int] = None
    is_official: bool
    usage_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    # 预设包含的提示词列表
    items: List[PresetItemRead] = []
    # 当前用户相关信息
    is_favorited: bool = False
    user_used_count: int = 0

    class Config:
        from_attributes = True


class PresetListRead(BaseModel):
    """预设列表项的响应模型。

    用于列表展示时返回简化信息。
    Requirements: 2.5, 2.6
    """
    id: int
    name: str
    display_name: str
    subcategory_id: Optional[int] = None
    is_official: bool
    usage_count: int
    item_count: int = 0
    is_favorited: bool = False
    user_used_count: int = 0

    class Config:
        from_attributes = True


class PresetSelectResponse(BaseModel):
    """预设选择的响应模型。

    返回选择预设后的提示词列表。
    Requirements: 4.1, 4.4, 4.9
    """
    preset_id: int
    preset_name: str
    items: List[PresetItemRead] = []


class PresetFavoriteResponse(BaseModel):
    """预设收藏操作的响应模型。

    Requirements: 8.1, 8.2, 8.3
    """
    preset_id: int
    is_favorited: bool
    message: str
