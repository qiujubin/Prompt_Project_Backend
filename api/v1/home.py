"""首页与导航相关接口。

提供分类树与动态菜单，兼容前端现有契约。"""
from fastapi import APIRouter, Depends, HTTPException, status
from core.security import create_access_token, decode_token
from api.v1.users import get_current_user, get_current_user_optional
from schemas.auth import LoginRequest, DropdownItem, DropdownResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from database import get_db
from models.prompt_category import PromptCategory
from models.prompt_subcategory import PromptSubcategory
from models.prompt_keyword import PromptKeyword
from models.user_prompt_keyword import UserPromptKeyword
from models.user_favorite import UserFavorite
from models.user import User
from models.prompt_preset import PromptPreset
from models.preset_item import PresetItem
from models.user_preset_favorite import UserPresetFavorite
from models.user_preset_usage import UserPresetUsage
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/home")

class FavoritePromptRequest(BaseModel):
    name: str

DEFAULT_CATEGORY_TREE = [
    {
        "name": "style",
        "label": "风格",
        "icon": "Box",
        "children": [
            {
                "name": "anime",
                "label": "二次元",
                "children": [
                    {"name": "anime_girl", "label": "动漫女孩"},
                    {"name": "anime_boy", "label": "动漫男孩"},
                    {"name": "chibi", "label": "Q版"}
                ]
            },
            {
                "name": "realistic",
                "label": "写实",
                "children": [
                    {"name": "portrait", "label": "人像"},
                    {"name": "landscape", "label": "风景"},
                    {"name": "still_life", "label": "静物"}
                ]
            }
        ]
    },
    {
        "name": "subject",
        "label": "题材",
        "icon": "Box",
        "children": [
            {
                "name": "nature",
                "label": "自然",
                "children": [
                    {"name": "forest", "label": "森林"},
                    {"name": "sea", "label": "海洋"}
                ]
            },
            {
                "name": "city",
                "label": "城市",
                "children": [
                    {"name": "street", "label": "街景"},
                    {"name": "architecture", "label": "建筑"}
                ]
            }
        ]
    }
]

def _categories(db: Session, user_id: int = None):
    """从数据库聚合生成分类树结构。"""
    cats = db.query(PromptCategory).order_by(PromptCategory.sort_order).all()
    subs = db.query(PromptSubcategory).order_by(PromptSubcategory.sort_order).all()
    keywords = db.query(PromptKeyword).all() # 如果数据量大应该优化，但目前 seed 数据不多

    # 获取用户收藏的提示词ID
    fav_keyword_ids = set()
    user_usage_map = {}
    if user_id:
        favs = db.query(UserFavorite.keyword_id).filter(UserFavorite.user_id == user_id).all()
        fav_keyword_ids = {f[0] for f in favs}

        # 获取用户使用统计
        user_usages = db.query(UserPromptKeyword).filter(UserPromptKeyword.user_id == user_id).all()
        for uu in user_usages:
            user_usage_map[uu.keyword_id] = uu.used_count

    # 构建 Keyword Map: sub_id -> [keywords]
    kw_map = {}
    for k in keywords:
        kw_map.setdefault(k.small_category_id, []).append({
            "id": k.id,
            "name": k.word,
            "label": k.display_name or k.word,
            "word": k.word, # Standardize
            "display_name": k.display_name, # Standardize
            "is_favorite": k.id in fav_keyword_ids,
            "usage_count": k.usage_count,
            "used_count": user_usage_map.get(k.id, 0),
            "created_by": k.created_by, # Standardize
            "user_id": k.created_by, # Keep for backward compatibility if needed
            "small_category_id": k.small_category_id # 用于统计记录
        })

    # 构建 Subcategory Map: cat_id -> [subcategories]
    sub_map = {}
    for s in subs:
        sub_map.setdefault(s.category_id, []).append({
            "name": s.name,
            "label": s.display_name,
            "children": kw_map.get(s.id, [])
        })

    result = []
    for c in cats:
        result.append({
            "name": c.name,
            "label": c.display_name,
            "icon": c.icon or "Box",
            "children": sub_map.get(c.id, [])
        })

    # 添加预设大分类 (Requirements: 2.1)
    preset_category = _build_preset_category(db, user_id)
    if preset_category:
        result.append(preset_category)

    if not result:
        return DEFAULT_CATEGORY_TREE
    return result


def _build_preset_category(db: Session, user_id: int = None):
    """构建预设大分类及其子分类。

    Requirements: 2.1, 2.2, 2.3, 2.4, 2.7
    - 2.1: THE Preset_System SHALL display "预设" as a category in the sidebar after all regular prompt categories
    - 2.2: WHEN a user clicks the preset category, THE Preset_System SHALL load and display preset subcategories
    - 2.3: THE Preset_System SHALL display Official_Preset items in their designated subcategories
    - 2.4: THE Preset_System SHALL display User_Preset items in a fixed "我的预设" subcategory
    - 2.7: IF the user is not logged in, THE Preset_System SHALL only display Official_Preset items
    """
    # 查询预设数据
    # 如果用户未登录，只显示官方预设 (Requirement 2.7)
    if user_id:
        # 登录用户：显示官方预设 + 自己的预设
        presets = db.query(PromptPreset).filter(
            or_(
                PromptPreset.is_official == True,
                PromptPreset.created_by == user_id
            )
        ).all()
    else:
        # 未登录用户：只显示官方预设
        presets = db.query(PromptPreset).filter(PromptPreset.is_official == True).all()

    # 获取用户收藏的预设ID
    fav_preset_ids = set()
    user_preset_usage_map = {}
    if user_id:
        fav_presets = db.query(UserPresetFavorite.preset_id).filter(
            UserPresetFavorite.user_id == user_id
        ).all()
        fav_preset_ids = {f[0] for f in fav_presets}

        # 获取用户预设使用统计
        user_preset_usages = db.query(UserPresetUsage).filter(
            UserPresetUsage.user_id == user_id
        ).all()
        for upu in user_preset_usages:
            user_preset_usage_map[upu.preset_id] = upu.used_count

    # 获取所有预设的items数量（用于预览）
    preset_item_counts = {}
    for preset in presets:
        preset_item_counts[preset.id] = len(preset.items) if preset.items else 0

    # 按小分类分组预设
    # 官方预设按 subcategory_id 分组 (Requirement 2.3)
    # 用户预设统一放到 "我的预设" 分类 (Requirement 2.4)
    official_subcategory_map = {}  # subcategory_id -> [presets]
    user_presets = []  # 用户自己的预设

    for preset in presets:
        preset_data = {
            "id": preset.id,
            "name": preset.name,
            "label": preset.display_name,
            "display_name": preset.display_name,
            "is_official": preset.is_official,
            "is_preset": True,  # 标记为预设类型，前端用于区分样式
            "is_favorite": preset.id in fav_preset_ids,
            "usage_count": preset.usage_count,
            "used_count": user_preset_usage_map.get(preset.id, 0),
            "item_count": preset_item_counts.get(preset.id, 0),
            "created_by": preset.created_by
        }

        if preset.is_official:
            # 官方预设按小分类分组
            sub_id = preset.subcategory_id
            official_subcategory_map.setdefault(sub_id, []).append(preset_data)
        else:
            # 用户预设
            user_presets.append(preset_data)

    # 构建子分类列表
    children = []

    # 添加官方预设的小分类
    if official_subcategory_map:
        # 获取小分类信息
        sub_ids = [sid for sid in official_subcategory_map.keys() if sid is not None]
        subcategories = []
        if sub_ids:
            subcategories = db.query(PromptSubcategory).filter(
                PromptSubcategory.id.in_(sub_ids)
            ).order_by(PromptSubcategory.sort_order).all()

        for sub in subcategories:
            children.append({
                "name": sub.name,
                "label": sub.display_name,
                "is_preset_subcategory": True,  # 标记为预设小分类
                "children": official_subcategory_map.get(sub.id, [])
            })

        # 处理没有关联小分类的官方预设（subcategory_id 为 None）
        if None in official_subcategory_map:
            children.append({
                "name": "official_uncategorized",
                "label": "官方预设",
                "is_preset_subcategory": True,
                "children": official_subcategory_map[None]
            })

    # 添加 "我的预设" 小分类（仅登录用户可见）(Requirement 2.4)
    if user_id:
        children.append({
            "name": "my_presets",
            "label": "我的预设",
            "is_preset_subcategory": True,
            "is_user_preset_category": True,  # 标记为用户预设分类，前端可显示创建按钮
            "children": user_presets
        })

    # 返回预设大分类 (Requirement 2.1)
    return {
        "name": "presets",
        "label": "预设",
        "icon": "Collection",  # Element Plus 图标
        "is_preset_category": True,  # 标记为预设大分类
        "children": children
    }

def _dropdown(role):
    items = [
        DropdownItem(label="个人中心", path="/user/center", name="userCenter", url="UserCenter"),
        DropdownItem(label="管理", path="/management", name="management", url="Management"),
        DropdownItem(label="用户设置", path="/user/settings", name="userSet", url="UserSet"),
        DropdownItem(label="页面设置", path="/pageSet", name="pageSet", url="PageSet")
    ]
    if role == "tourist":
        items = [DropdownItem(label="其它", path="/other", name="other", url="Other")]
    return items

@router.get("/getPromptCatagory")
def get_prompt_category(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """返回分类树结构：`{ code, msg, data: { promptCatagory: [...] } }`。"""
    user_id = current_user.id if current_user else None
    data = {"promptCatagory": _categories(db, user_id)}
    return {"code": 200, "msg": "OK", "data": data}

@router.post("/getDropdown")
def get_dropdown(payload: LoginRequest):
    """根据角色返回动态菜单。
    优先使用 token 判定是否已登录；若 token 有效则视为已登录用户。
    """
    role = "tourist"
    token = payload.token

    if token:
        try:
            decoded = decode_token(token)
            sub = decoded.get("sub")
            if sub:
                role = "user"
        except Exception:
            # 无效 token，降级为游客
            role = "tourist"
            token = None

    if not token:
        token = create_access_token({"sub": payload.username or "tourist"})
        if payload.username:
            role = "user"

    items = _dropdown(role)
    res = DropdownResponse(role=role, token=token, dropdownList=items)
    return {"code": 200, "msg": "OK", "data": res.dict()}

@router.post("/favoritePrompt")
def favorite_prompt(
    payload: FavoritePromptRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    收藏/取消收藏提示词 (通过提示词名称)
    如果已收藏则取消收藏，如果未收藏则添加收藏。
    """
    # 1. 查找提示词是否存在
    keyword = db.query(PromptKeyword).filter(PromptKeyword.word == payload.name).first()
    if not keyword:
        # 尝试查找 display_name 匹配的情况 (可选)
        keyword = db.query(PromptKeyword).filter(PromptKeyword.display_name == payload.name).first()

    if not keyword:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt '{payload.name}' not found"
        )

    # 2. 查找是否已收藏
    fav = db.query(UserFavorite).filter(
        UserFavorite.user_id == current_user.id,
        UserFavorite.keyword_id == keyword.id
    ).first()

    # 3. 如果已收藏 -> 取消收藏
    if fav:
        db.delete(fav)
        db.commit()
        return {"code": 200, "msg": "取消收藏成功", "data": {"is_favorite": False}}

    # 4. 如果未收藏 -> 添加收藏
    new_fav = UserFavorite(user_id=current_user.id, keyword_id=keyword.id)
    db.add(new_fav)
    db.commit()
    return {"code": 200, "msg": "添加收藏成功", "data": {"is_favorite": True}}

