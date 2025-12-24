"""首页与导航相关接口。

提供分类树与动态菜单，兼容前端现有契约。"""
from fastapi import APIRouter, Depends, HTTPException, status
from core.security import create_access_token, decode_token
from api.v1.users import get_current_user, get_current_user_optional
from schemas.auth import LoginRequest, DropdownItem, DropdownResponse
from sqlalchemy.orm import Session
from database import get_db
from models.prompt_category import PromptCategory
from models.prompt_subcategory import PromptSubcategory
from models.prompt_keyword import PromptKeyword
from models.user_prompt_keyword import UserPromptKeyword
from models.user_favorite import UserFavorite
from models.user import User
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
            "user_id": k.created_by # Keep for backward compatibility if needed
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
    if not result:
        return DEFAULT_CATEGORY_TREE
    return result

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

