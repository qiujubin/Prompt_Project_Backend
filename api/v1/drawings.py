from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from pydantic import BaseModel

from database import get_db
from models.drawing import Drawing
from models.user import User
from schemas.drawing import DrawingRead
from api.v1.users import get_current_user, get_current_user_optional

router = APIRouter(prefix="/drawings")

class DrawingCreate(BaseModel):
    user_id: int
    prompt: str
    negative_prompt: Optional[str] = None
    model_name: str
    image_url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    seed: Optional[str] = None
    ai_response_time_ms: Optional[int] = None
    status: str

class DrawingPublicUpdate(BaseModel):
    is_public: bool

class DrawingStatusUpdate(BaseModel):
    status: str

@router.post("/create")
def create_drawing(drawing_in: DrawingCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    创建绘图记录。
    状态默认为 'finish'。
    """
    # 使用当前登录用户ID，忽略传入的user_id
    
    new_drawing = Drawing(
        user_id=current_user.id,
        prompt=drawing_in.prompt,
        negative_prompt=drawing_in.negative_prompt,
        model_name=drawing_in.model_name,
        image_url=drawing_in.image_url,
        width=drawing_in.width,
        height=drawing_in.height,
        seed=drawing_in.seed,
        ai_response_time_ms=drawing_in.ai_response_time_ms,
        status="finish"  # 默认状态
    )
    db.add(new_drawing)
    db.commit()
    db.refresh(new_drawing)
    
    return {"code": 200, "msg": "绘图记录创建成功", "data": new_drawing}

@router.put("/{drawing_id}/public")
def update_drawing_public(drawing_id: int, update_in: DrawingPublicUpdate, db: Session = Depends(get_db)):
    """
    根据ID修改绘图的公开状态 (is_public)。
    """
    drawing = db.query(Drawing).filter(Drawing.id == drawing_id).first()
    if not drawing:
        raise HTTPException(status_code=404, detail="绘图记录不存在")
    
    drawing.is_public = update_in.is_public
    db.commit()
    db.refresh(drawing)
    
    return {"code": 200, "msg": "公开状态更新成功", "data": drawing}

@router.put("/{drawing_id}/status")
def update_drawing_status(drawing_id: int, update_in: DrawingStatusUpdate, db: Session = Depends(get_db)):
    """
    根据ID修改绘图的状态 (status)。
    例如设置为 'delete' 或其他。
    """
    drawing = db.query(Drawing).filter(Drawing.id == drawing_id).first()
    if not drawing:
        raise HTTPException(status_code=404, detail="绘图记录不存在")
    
    drawing.status = update_in.status
    db.commit()
    db.refresh(drawing)
    
    return {"code": 200, "msg": "状态更新成功", "data": drawing}

@router.get("/{drawing_id}")
def get_drawing_detail(drawing_id: int, db: Session = Depends(get_db)):
    """
    获取单个绘图记录详情。
    """
    drawing = db.query(Drawing).filter(Drawing.id == drawing_id).first()
    if not drawing:
        raise HTTPException(status_code=404, detail="绘图记录不存在")
    
    # Enrich with user info
    result = DrawingRead.from_orm(drawing)
    user = db.query(User).filter(User.id == drawing.user_id).first()
    if user:
        result.username = user.username
        result.avatar_url = user.avatar_url
        
    return {"code": 200, "msg": "OK", "data": result}

@router.get("/")
def list_drawings(
    user_id: Optional[int] = None,
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取绘图记录列表。
    - 如果提供 user_id，则获取该用户的绘图 (需本人或管理员)。
    - 如果不提供 user_id (仅管理员)，则获取所有绘图。
    """
    q = db.query(Drawing)
    if user_id:
        # Check permission
        if current_user.id != user_id and current_user.role != "admin":
             raise HTTPException(status_code=403, detail="无权限查看他人绘图记录")
        q = q.filter(Drawing.user_id == user_id)
    else:
        # Admin only for all drawings
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="无权限查看所有绘图记录")
    
    total = q.count()
    drawings = q.order_by(Drawing.created_at.desc())\
            .offset((page - 1) * size)\
            .limit(size)\
            .all()
            
    return {"code": 200, "msg": "OK", "data": drawings, "total": total}
