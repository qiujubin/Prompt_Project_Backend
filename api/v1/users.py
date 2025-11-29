"""用户相关接口。

提供获取当前登录用户信息的示例接口。"""
from fastapi import APIRouter, Depends, HTTPException, Header
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from core.security import decode_token
from database import get_db
from models.user import User
from schemas.user import UserRead

router = APIRouter(prefix="/users")

def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)):
    """从 `Authorization: Bearer <token>` 解析用户并返回 ORM 对象。"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未授权")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="未授权")
    payload = decode_token(token)
    username = payload.get("sub")
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="未授权")
    return user

@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)):
    """返回当前登录用户的基本信息。"""
    return user
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

@router.post("/update_phone")
def update_phone(user_id: int, phone: str, db: Session = Depends(get_db)):
    """用户添加或修改手机号（直接修改，不验证）。"""
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
def update_email(user_id: int, email: str, db: Session = Depends(get_db)):
    """用户添加或修改邮箱（直接修改，不验证）。"""
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
def update_password(user_id: int, password: str, db: Session = Depends(get_db)):
    """用户修改密码（直接修改）。"""
    from core.security import get_password_hash
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
        
    user.hashed_password = get_password_hash(password)
    user.updated_at = func.now()
    db.commit()
    return {"code": 200, "msg": "密码更新成功", "data": True}

@router.post("/update_username")
def update_username(user_id: int, username: str, db: Session = Depends(get_db)):
    """用户修改用户名（直接修改）。"""
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

@router.post("/update_avatar")
def update_avatar(user_id: int, avatar_url: str, db: Session = Depends(get_db)):
    """用户修改头像。"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
        
    user.avatar_url = avatar_url
    user.updated_at = func.now()
    db.commit()
    return {"code": 200, "msg": "头像更新成功", "data": True}
