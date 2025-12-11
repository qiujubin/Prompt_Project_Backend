"""用户相关接口。

提供获取当前登录用户信息的示例接口。"""
from fastapi import APIRouter, Depends, HTTPException, Header, UploadFile, File
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from core.security import decode_token
from database import get_db
from models.user import User
from schemas.user import UserRead
import shutil
import os
import uuid

router = APIRouter(prefix="/users")

def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)):
    """从 `Authorization: Bearer <token>` 解析用户并返回 ORM 对象。"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未授权")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="未授权")
    try:
        payload = decode_token(token)
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="未授权")
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(status_code=401, detail="未授权")
        return user
    except Exception:
        raise HTTPException(status_code=401, detail="未授权")

def get_current_user_optional(authorization: str = Header(None), db: Session = Depends(get_db)):
    """尝试获取当前用户，若未登录返回 None。"""
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        return None
    try:
        payload = decode_token(token)
        username = payload.get("sub")
        if not username:
            return None
        user = db.query(User).filter(User.username == username).first()
        return user
    except:
        return None

@router.get("/me")
def me(user: User = Depends(get_current_user)):
    """返回当前登录用户的基本信息。"""
    return {"code": 200, "msg": "OK", "data": user}
@router.get("/")
def list_users(page: int = 1, size: int = 10, q: Optional[str] = None, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current.role != "admin":
        raise HTTPException(status_code=403, detail="无权限")
    query = db.query(User)
    if q:
        query = query.filter(User.username.ilike(f"%{q}%"))
    
    total = query.count()
    items = query.order_by(User.id.desc()).offset((page - 1) * size).limit(size).all()
    
    return {
        "code": 200,
        "msg": "OK",
        "data": items,
        "total": total,
        "page": page,
        "size": size
    }

@router.delete("/{user_id}")
def delete_user(user_id: int, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """根据ID删除用户（仅管理员）。"""
    if current.role != "admin":
        raise HTTPException(status_code=403, detail="无权限")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    db.delete(user)
    db.commit()
    return {"code": 200, "msg": "删除成功", "data": True}

@router.put("/{user_id}/role")
def update_user_role(user_id: int, role: str, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """管理员修改用户角色。"""
    if current.role != "admin":
        raise HTTPException(status_code=403, detail="无权限")
    
    if role not in ["user", "admin"]:
         raise HTTPException(status_code=400, detail="无效的角色")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
        
    user.role = role
    user.updated_at = func.now()
    db.commit()
    return {"code": 200, "msg": "角色更新成功", "data": True}

@router.post("/update_phone")
def update_phone(user_id: int, phone: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """用户添加或修改手机号。"""
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权限修改他人信息")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 检查手机号是否被占用
    exists = db.query(User).filter(User.phone == phone).first()
    if exists and exists.id != user_id:
        raise HTTPException(status_code=400, detail="手机号已被使用")
        
    user.phone = phone
    user.updated_at = func.now()
    db.commit()
    return {"code": 200, "msg": "手机号更新成功", "data": True}

@router.post("/update_email")
def update_email(user_id: int, email: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """用户添加或修改邮箱。"""
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权限修改他人信息")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 检查邮箱是否被占用
    exists = db.query(User).filter(User.email == email).first()
    if exists and exists.id != user_id:
        raise HTTPException(status_code=400, detail="邮箱已被使用")
        
    user.email = email
    user.updated_at = func.now()
    db.commit()
    return {"code": 200, "msg": "邮箱更新成功", "data": True}

@router.post("/update_password")
def update_password(user_id: int, password: str, old_password: Optional[str] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """用户修改密码。"""
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权限修改他人信息")
        
    from core.security import get_password_hash, verify_password
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 如果是用户自己修改（非管理员强制修改），且提供了旧密码，则验证
    # 或者要求必须验证旧密码（更安全）
    # 这里逻辑：如果用户自己修改，必须提供旧密码。如果是管理员，可以不提供。
    if current_user.role != "admin":
        if not old_password:
            raise HTTPException(status_code=400, detail="请提供旧密码")
        if not verify_password(old_password, user.hashed_password):
            raise HTTPException(status_code=400, detail="旧密码错误")
        
    user.hashed_password = get_password_hash(password)
    user.updated_at = func.now()
    db.commit()
    return {"code": 200, "msg": "密码更新成功", "data": True}

@router.post("/update_username")
def update_username(user_id: int, username: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """用户修改用户名。"""
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权限修改他人信息")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 检查用户名唯一性
    exists = db.query(User).filter(User.username == username).first()
    if exists and exists.id != user_id:
        raise HTTPException(status_code=400, detail="用户名已被使用")

    user.username = username
    user.updated_at = func.now()
    db.commit()
    return {"code": 200, "msg": "用户名更新成功", "data": True}

@router.post("/update_signature")
def update_signature(user_id: int, signature: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """用户修改签名。"""
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权限修改他人信息")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
        
    user.signature = signature
    user.updated_at = func.now()
    db.commit()
    return {"code": 200, "msg": "签名更新成功", "data": True}

@router.post("/update_avatar")
def update_avatar(user_id: int, avatar_url: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """用户修改头像。"""
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权限修改他人信息")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
        
    user.avatar_url = avatar_url
    user.updated_at = func.now()
    db.commit()
    return {"code": 200, "msg": "头像更新成功", "data": True}

@router.post("/upload_avatar")
def upload_avatar(file: UploadFile = File(...)):
    """上传头像并返回URL"""
    if not os.path.exists("static/uploads"):
        os.makedirs("static/uploads")
    
    file_extension = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4()}{file_extension}"
    file_path = f"static/uploads/{filename}"
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Assuming the server is running on localhost:8000 or configured domain
    # For now returning relative path or absolute URL if domain is known
    # Better to return relative path and let frontend prepend base URL
    url = f"/static/uploads/{filename}"
    return {"code": 200, "msg": "Upload successful", "data": {"url": url}}
