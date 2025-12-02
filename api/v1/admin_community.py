from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from database import get_db
from models.drawing import Drawing
from models.drawing_interaction import DrawingComment
from models.user import User
from api.v1.users import get_current_user
from schemas.community import CommentRead
from typing import List

router = APIRouter(prefix="/admin/community", tags=["Admin Community"])

def get_admin_user(current_user: User = Depends(get_current_user)):
    """验证管理员权限"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Permission denied")
    return current_user

@router.delete("/comments/{comment_id}")
def delete_comment(
    comment_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    管理员删除评论
    """
    comment = db.query(DrawingComment).filter(DrawingComment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # 更新画作的评论计数
    drawing = db.query(Drawing).filter(Drawing.id == comment.drawing_id).first()
    if drawing:
        drawing.comment_count = max(0, drawing.comment_count - 1)
        
    db.delete(comment)
    db.commit()
    return {"code": 200, "msg": "Comment deleted"}

@router.put("/drawings/{drawing_id}/status")
def update_drawing_status(
    drawing_id: int,
    is_public: bool,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    管理员更改画作状态（如强制下架/隐藏）
    """
    drawing = db.query(Drawing).filter(Drawing.id == drawing_id).first()
    if not drawing:
        raise HTTPException(status_code=404, detail="Drawing not found")
    
    drawing.is_public = is_public
    db.commit()
    return {"code": 200, "msg": "Drawing status updated", "data": {"id": drawing.id, "is_public": drawing.is_public}}

@router.get("/comments", response_model=dict)
def list_all_comments(
    page: int = 1,
    size: int = 20,
    user_id: int = None,
    drawing_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    管理员获取评论列表（支持按用户或画作筛选）
    """
    q = db.query(DrawingComment)
    
    if user_id:
        q = q.filter(DrawingComment.user_id == user_id)
    if drawing_id:
        q = q.filter(DrawingComment.drawing_id == drawing_id)
        
    total = q.count()
    comments = q.order_by(DrawingComment.created_at.desc()).offset((page - 1) * size).limit(size).all()
    
    return {
        "code": 200, 
        "msg": "OK", 
        "data": [CommentRead.from_orm(c) for c in comments],
        "total": total
    }
