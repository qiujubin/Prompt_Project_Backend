"""绘图接口。

提供绘图记录的创建与列表查询（示例）。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models.drawing import Drawing
from schemas.drawing import DrawingCreate, DrawingRead
from typing import List

router = APIRouter(prefix="/drawings")

@router.post("/", response_model=DrawingRead)
def create_drawing(payload: DrawingCreate, db: Session = Depends(get_db)):
    """创建一个绘图记录。"""
    d = Drawing(prompt=payload.prompt, negative_prompt=payload.negative_prompt)
    db.add(d)
    db.commit()
    db.refresh(d)
    return d

@router.get("/", response_model=List[DrawingRead])
def list_drawings(db: Session = Depends(get_db)):
    """按时间倒序列出绘图记录。"""
    return db.query(Drawing).order_by(Drawing.id.desc()).all()
