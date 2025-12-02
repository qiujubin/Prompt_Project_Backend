from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
import datetime

from database import get_db
from api.v1.users import get_current_user
from models.user import User
from models.credit_log import CreditLog
from pydantic import BaseModel

router = APIRouter(prefix="/credits")

class CreditLogRead(BaseModel):
    id: int
    change_amount: int
    reason: str
    description: str | None
    created_at: datetime.datetime
    
    class Config:
        orm_mode = True

@router.get("/", response_model=dict)
def get_my_credits(
    page: int = 1,
    size: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取当前用户的积分和变动记录。"""
    # 确保 credits 字段存在（如果是老数据可能需要处理，但这里假设 DB 已迁移）
    current_credits = current_user.credits if current_user.credits is not None else 0
    
    logs_query = db.query(CreditLog).filter(CreditLog.user_id == current_user.id).order_by(CreditLog.created_at.desc())
    total = logs_query.count()
    logs = logs_query.offset((page - 1) * size).limit(size).all()
    
    log_list = [CreditLogRead.from_orm(log) for log in logs]
    
    return {
        "code": 200, 
        "msg": "OK", 
        "data": {
            "credits": current_credits,
            "logs": log_list
        },
        "total": total
    }

@router.post("/check_in")
def daily_check_in(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """每日签到，赠送积分。"""
    today = datetime.date.today()
    
    # 检查今日是否已签到
    # 查找 reason='daily_check_in' 且 created_at 在今天的记录
    exists = db.query(CreditLog).filter(
        CreditLog.user_id == current_user.id,
        CreditLog.reason == "daily_check_in",
        func.date(CreditLog.created_at) == today
    ).first()
    
    if exists:
        return {"code": 400, "msg": "今日已签到", "data": None}
    
    reward = 10
    
    # 更新用户积分
    current_user.credits = (current_user.credits or 0) + reward
    
    # 记录日志
    log = CreditLog(
        user_id=current_user.id,
        change_amount=reward,
        reason="daily_check_in",
        description=f"每日签到奖励 {today}"
    )
    db.add(log)
    db.commit()
    
    return {"code": 200, "msg": f"签到成功，获得 {reward} 积分", "data": {"credits": current_user.credits}}

# 辅助函数：扣除积分（供其他模块调用）
def deduct_credits(user_id: int, amount: int, reason: str, description: str, db: Session):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("User not found")
    
    if (user.credits or 0) < amount:
        raise ValueError("积分不足")
        
    user.credits -= amount
    
    log = CreditLog(
        user_id=user_id,
        change_amount=-amount,
        reason=reason,
        description=description
    )
    db.add(log)
    db.commit()
    return user.credits

def add_credits(user_id: int, amount: int, reason: str, description: str, db: Session):
    """增加积分辅助函数。"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
        
    user.credits = (user.credits or 0) + amount
    
    log = CreditLog(
        user_id=user_id,
        change_amount=amount,
        reason=reason,
        description=description
    )
    db.add(log)
    db.commit()
    return user.credits
