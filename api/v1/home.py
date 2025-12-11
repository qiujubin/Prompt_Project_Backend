"""首页与导航相关接口。

提供分类树与动态菜单，兼容前端现有契约。"""
from fastapi import APIRouter, Depends
from core.security import create_access_token, decode_token
from schemas.auth import LoginRequest, DropdownItem, DropdownResponse
from sqlalchemy.orm import Session
from database import get_db
from models.prompt_category import PromptCategory
from models.prompt_subcategory import PromptSubcategory
from models.prompt_keyword import PromptKeyword

router = APIRouter(prefix="/home")

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

def _categories(db: Session):
    """从数据库聚合生成分类树结构。"""
    cats = db.query(PromptCategory).order_by(PromptCategory.sort_order).all()
    subs = db.query(PromptSubcategory).order_by(PromptSubcategory.sort_order).all()
    keywords = db.query(PromptKeyword).all() # 如果数据量大应该优化，但目前 seed 数据不多
    
    # 构建 Keyword Map: sub_id -> [keywords]
    kw_map = {}
    for k in keywords:
        kw_map.setdefault(k.small_category_id, []).append({
            "name": k.word,
            "label": k.display_name or k.word
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
        DropdownItem(label="个人中心", path="/userCenter", name="userCenter", url="UserCenter"),
        DropdownItem(label="管理", path="/management", name="management", url="Management"),
        DropdownItem(label="用户设置", path="/userSet", name="userSet", url="UserSet"),
        DropdownItem(label="页面设置", path="/pageSet", name="pageSet", url="PageSet")
    ]
    if role == "tourist":
        items = [DropdownItem(label="其它", path="/other", name="other", url="Other")]
    return items

@router.get("/getPromptCatagory")
def get_prompt_category(db: Session = Depends(get_db)):
    """返回分类树结构：`{ code, msg, data: { promptCatagory: [...] } }`。"""
    data = {"promptCatagory": _categories(db)}
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
