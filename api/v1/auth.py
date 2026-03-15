"""认证与账号绑定接口。

支持账户密码登录、邮箱/短信验证码登录与邮箱/手机号/微信绑定。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from core.security import get_password_hash, verify_password, create_access_token
from core.config import settings
from database import get_db
from models.user import User, SocialAccount
from schemas.user import UserCreate, UserRead
from services.code_service import code_service
import random

router = APIRouter(prefix="/auth")

class VerificationCodeRequest(BaseModel):
    target: str
    type: str
    captcha: str

class PhoneLoginRequest(BaseModel):
    phoneNumber: str
    captcha: str
    verificationCode: str

class EmailLoginRequest(BaseModel):
    email: str
    captcha: str
    verificationCode: str

def generate_unique_nickname(db: Session) -> str:
    """生成唯一的默认昵称 '用户_xxxx'"""
    while True:
        suffix = str(random.randint(1000, 9999))
        nickname = f"用户_{suffix}"
        if not db.query(User).filter(User.nickname == nickname).first():
            return nickname

@router.post("/register", response_model=UserRead)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    """注册新用户（账户+密码）。"""
    exists = db.query(User).filter(User.username == payload.username).first()
    if exists:
        raise HTTPException(status_code=400, detail="用户名已存在")

    nickname = generate_unique_nickname(db)
    user = User(
        username=payload.username,
        hashed_password=get_password_hash(payload.password),
        nickname=nickname
    )
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
        nickname = generate_unique_nickname(db)
        user = User(username=email, email=email, nickname=nickname)
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
        nickname = generate_unique_nickname(db)
        user = User(username=phone, phone=phone, nickname=nickname)
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

from services.email_service import email_service

@router.post("/verification-code")
def send_verification_code(
    payload: VerificationCodeRequest,
    db: Session = Depends(get_db)
):
    """统一的验证码发送接口

    Args:
        target: 手机号或邮箱
        type: 'phone' 或 'email'
        captcha: 人机验证码
    """
    # 验证人机验证码（简化实现，实际应该验证真实的captcha）
    if not payload.captcha or len(payload.captcha) < 4:
        raise HTTPException(status_code=400, detail="人机验证码无效")

    try:
        if payload.type == "phone":
            # 🔥 使用阿里云短信认证服务发送真实短信
            from services.sms_service import sms_service
            result = sms_service.send_sms_verify_code(payload.target)

            if result["success"]:
                # 将阿里云返回的验证码存储到我们的验证码服务中
                if result.get("verify_code"):
                    # 使用阿里云返回的验证码，覆盖我们生成的
                    code_service._store[("sms", payload.target)] = {
                        "code": result["verify_code"],
                        "sent_at": code_service._now(),
                        "expire_at": code_service._now() + settings.VERIFICATION_CODE_EXPIRE_SECONDS,
                        "attempts": 0,
                    }

                # 生产环境应该移除 verification_code 返回
                return {
                    "code": 200,
                    "msg": "验证码已发送到您的手机",
                    "data": {
                        "phone": payload.target,
                        "verification_code": result.get("verify_code")  # 测试环境返回
                    }
                }
            else:
                # 发送失败，返回友好的错误信息
                error_msg = sms_service.get_error_message(result.get("error_code", ""))
                raise HTTPException(status_code=500, detail=error_msg)
        elif payload.type == "email":
            code = code_service.generate("email", payload.target)

            # 🔥 发送真实邮件
            success = email_service.send_verification_code(payload.target, code)
            if not success:
                raise HTTPException(status_code=500, detail="邮件发送失败，请稍后重试")

            # 生产环境应该移除 verification_code 返回
            return {"code": 200, "msg": "验证码已发送到您的邮箱", "data": {"email": payload.target, "verification_code": code}}
        else:
            raise HTTPException(status_code=400, detail="不支持的验证码类型")
    except ValueError as e:
        raise HTTPException(status_code=429, detail=str(e))

@router.post("/login/phone")
def login_with_phone(
    payload: PhoneLoginRequest,
    db: Session = Depends(get_db)
):
    """手机验证码登录

    Args:
        phoneNumber: 手机号
        captcha: 人机验证码
        verificationCode: 短信验证码
    """
    # 验证人机验证码
    if not payload.captcha or len(payload.captcha) < 4:
        raise HTTPException(status_code=400, detail="人机验证码无效")

    # 验证短信验证码
    if not code_service.verify("sms", payload.phoneNumber, payload.verificationCode):
        raise HTTPException(status_code=400, detail="验证码错误或已失效")

    # 查找用户
    user = db.query(User).filter(User.phone == payload.phoneNumber).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    token = create_access_token({"sub": user.username})
    return {"code": 200, "msg": "登录成功", "data": {"access_token": token, "token_type": "bearer"}}

@router.post("/login/email")
def login_with_email(
    payload: EmailLoginRequest,
    db: Session = Depends(get_db)
):
    """邮箱验证码登录

    Args:
        email: 邮箱地址
        captcha: 人机验证码
        verificationCode: 邮箱验证码
    """
    # 验证人机验证码
    if not payload.captcha or len(payload.captcha) < 4:
        raise HTTPException(status_code=400, detail="人机验证码无效")

    # 验证邮箱验证码
    if not code_service.verify("email", payload.email, payload.verificationCode):
        raise HTTPException(status_code=400, detail="验证码错误或已失效")

    # 查找用户
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    token = create_access_token({"sub": user.username})
    return {"code": 200, "msg": "登录成功", "data": {"access_token": token, "token_type": "bearer"}}

@router.post("/register/phone")
def register_with_phone(
    payload: PhoneLoginRequest,
    db: Session = Depends(get_db)
):
    """手机号注册并登录"""
    # 验证人机验证码
    if not payload.captcha or len(payload.captcha) < 4:
        raise HTTPException(status_code=400, detail="人机验证码无效")

    # 验证短信验证码
    if not code_service.verify("sms", payload.phoneNumber, payload.verificationCode):
        raise HTTPException(status_code=400, detail="验证码错误或已失效")

    # 检查用户是否已存在
    existing_user = db.query(User).filter(User.phone == payload.phoneNumber).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="该手机号已注册")

    # 创建新用户
    nickname = generate_unique_nickname(db)
    user = User(username=payload.phoneNumber, phone=payload.phoneNumber, nickname=nickname)
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.username})
    return {"code": 200, "msg": "注册成功", "data": {"access_token": token, "token_type": "bearer"}}

@router.post("/register/email")
def register_with_email(
    payload: EmailLoginRequest,
    db: Session = Depends(get_db)
):
    """邮箱注册并登录"""
    # 验证人机验证码
    if not payload.captcha or len(payload.captcha) < 4:
        raise HTTPException(status_code=400, detail="人机验证码无效")

    # 验证邮箱验证码
    if not code_service.verify("email", payload.email, payload.verificationCode):
        raise HTTPException(status_code=400, detail="验证码错误或已失效")

    # 检查用户是否已存在
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="该邮箱已注册")

    # 创建新用户
    nickname = generate_unique_nickname(db)
    user = User(username=payload.email, email=payload.email, nickname=nickname)
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.username})
    return {"code": 200, "msg": "注册成功", "data": {"access_token": token, "token_type": "bearer"}}
