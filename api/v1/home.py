"""首页与导航相关接口。

提供分类树与动态菜单，兼容前端现有契约。"""
from fastapi import APIRouter, Depends
from core.security import create_access_token
from schemas.auth import LoginRequest, DropdownItem, DropdownResponse
from sqlalchemy.orm import Session
from database import get_db
from models.prompt_category import PromptCategory
from models.prompt_subcategory import PromptSubcategory

router = APIRouter(prefix="/home")

def _categories(db: Session):
    """从数据库聚合生成分类树结构。"""
    cats = db.query(PromptCategory).order_by(PromptCategory.sort_order).all()
    subs = db.query(PromptSubcategory).order_by(PromptSubcategory.sort_order).all()
    sub_map = {}
    for s in subs:
        sub_map.setdefault(s.category_id, []).append({"name": s.name, "label": s.display_name})
    result = []
    for c in cats:
        result.append({
            "name": c.name,
            "label": c.display_name,
            "icon": "Box",
            "children": sub_map.get(c.id, [])
        })
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
    """根据角色返回动态菜单。"""
    role = "user" if payload.username else "tourist"
    token = payload.token or create_access_token({"sub": payload.username or "tourist"})
    items = _dropdown(role)
    res = DropdownResponse(role=role, token=token, dropdownList=items)
    return {"code": 200, "msg": "OK", "data": res.dict()}
