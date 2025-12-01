"""认证与账号绑定接口。

支持账户密码登录、邮箱/短信验证码登录与邮箱/手机号/微信绑定。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.security import get_password_hash, verify_password, create_access_token
from database import get_db
from models.user import User, SocialAccount
from schemas.user import UserCreate, UserRead
from services.code_service import code_service

router = APIRouter(prefix="/auth")

@router.post("/register", response_model=UserRead)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    """注册新用户（账户+密码）。"""
    exists = db.query(User).filter(User.username == payload.username).first()
    if exists:
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = User(username=payload.username, hashed_password=get_password_hash(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post("/login")
def login(payload: UserCreate, db: Session = Depends(get_db)):
    """账户+密码登录，返回访问令牌。"""
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="认证失败")
    token = create_access_token({"sub": user.username})
    return {"code": 200, "msg": "OK", "data": {"access_token": token, "token_type": "bearer"}}

@router.post("/send_email_code")
def send_email_code(email: str):
    """发送邮箱验证码（示例实现）。"""
    code = code_service.generate("email", email)
    # 在此处集成实际邮件发送
    return {"code": 200, "msg": "OK", "data": {"email": email}}

@router.post("/send_sms_code")
def send_sms_code(phone: str):
    """发送短信验证码（示例实现）。"""
    code = code_service.generate("sms", phone)
    # 在此处集成实际短信发送
    return {"code": 200, "msg": "OK", "data": {"phone": phone}}

@router.post("/login_with_email_code")
def login_with_email_code(email: str, code: str, db: Session = Depends(get_db)):
    """邮箱验证码登录，不存在则自动注册。"""
    if not code_service.verify("email", email, code):
        raise HTTPException(status_code=400, detail="验证码错误或失效")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(username=email, email=email)
        db.add(user)
        db.commit()
        db.refresh(user)
    token = create_access_token({"sub": user.username})
    return {"code": 200, "msg": "OK", "data": {"access_token": token, "token_type": "bearer"}}

@router.post("/login_with_sms_code")
def login_with_sms_code(phone: str, code: str, db: Session = Depends(get_db)):
    """短信验证码登录，不存在则自动注册。"""
    if not code_service.verify("sms", phone, code):
        raise HTTPException(status_code=400, detail="验证码错误或失效")
    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        user = User(username=phone, phone=phone)
        db.add(user)
        db.commit()
        db.refresh(user)
    token = create_access_token({"sub": user.username})
    return {"code": 200, "msg": "OK", "data": {"access_token": token, "token_type": "bearer"}}

@router.post("/bind_email")
def bind_email(user_id: int, email: str, code: str, db: Session = Depends(get_db)):
    """绑定邮箱到指定用户，需验证码校验与唯一性检查。"""
    if not code_service.verify("email", email, code):
        raise HTTPException(status_code=400, detail="验证码错误或失效")
    exists = db.query(User).filter(User.email == email).first()
    if exists and exists.id != user_id:
        raise HTTPException(status_code=400, detail="邮箱已被使用")
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.email = email
    db.commit()
    return {"code": 200, "msg": "OK", "data": True}

@router.post("/bind_phone")
def bind_phone(user_id: int, phone: str, code: str, db: Session = Depends(get_db)):
    """绑定手机号到指定用户，需验证码校验与唯一性检查。"""
    if not code_service.verify("sms", phone, code):
        raise HTTPException(status_code=400, detail="验证码错误或失效")
    exists = db.query(User).filter(User.phone == phone).first()
    if exists and exists.id != user_id:
        raise HTTPException(status_code=400, detail="手机号已被使用")
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.phone = phone
    db.commit()
    return {"code": 200, "msg": "OK", "data": True}

@router.post("/bind_wechat")
def bind_wechat(user_id: int, openid: str, db: Session = Depends(get_db)):
    """绑定微信 openid 到指定用户，确保唯一性。"""
    exists = db.query(SocialAccount).filter(SocialAccount.openid == openid).first()
    if exists and exists.user_id != user_id:
        raise HTTPException(status_code=400, detail="该微信已绑定其他账号")
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if not exists:
        sa = SocialAccount(user_id=user_id, openid=openid)
        db.add(sa)
    else:
        exists.user_id = user_id
    db.commit()
    return {"code": 200, "msg": "OK", "data": True}
