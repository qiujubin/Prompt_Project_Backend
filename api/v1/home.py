from fastapi import APIRouter
from core.security import create_access_token
from schemas.auth import LoginRequest, DropdownItem, DropdownResponse

router = APIRouter(prefix="/home")

def _categories():
    return [
        {"name": "food", "label": "食物", "icon": "ForkSpoon", "children": [
            {"name": "bread", "label": "面包"},
            {"name": "noodles", "label": "面条"}
        ]},
        {"name": "beverages", "label": "饮料", "icon": "Coffee", "children": [
            {"name": "tea", "label": "茶"},
            {"name": "coffee", "label": "咖啡"}
        ]},
        {"name": "style", "label": "风格", "icon": "PictureFilled", "children": []}
    ]

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
def get_prompt_category():
    data = {"promptCatagory": _categories()}
    return {"code": 200, "msg": "OK", "data": data}

@router.post("/getDropdown")
def get_dropdown(payload: LoginRequest):
    role = "user" if payload.username else "tourist"
    token = payload.token or create_access_token({"sub": payload.username or "tourist"})
    items = _dropdown(role)
    res = DropdownResponse(role=role, token=token, dropdownList=items)
    return {"code": 200, "msg": "OK", "data": res.dict()}