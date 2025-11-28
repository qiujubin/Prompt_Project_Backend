from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.security import get_password_hash, verify_password, create_access_token
from database import get_db
from models.user import User
from schemas.user import UserCreate, UserRead

router = APIRouter(prefix="/auth")

@router.post("/register", response_model=UserRead)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    exists = db.query(User).filter(User.username == payload.username).first()
    if exists:
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = User(username=payload.username, email=payload.email, hashed_password=get_password_hash(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post("/login")
def login(payload: UserCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="认证失败")
    token = create_access_token({"sub": user.username})
    return {"code": 200, "msg": "OK", "data": {"access_token": token, "token_type": "bearer"}}