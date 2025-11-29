"""用户相关接口。

提供获取当前登录用户信息的示例接口。"""
from fastapi import APIRouter, Depends, HTTPException, Header
from typing import List, Optional
from sqlalchemy.orm import Session
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
