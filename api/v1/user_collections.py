from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from database import get_db
from models.drawing import Drawing
from models.drawing_interaction import DrawingLike, DrawingFavorite
from models.user import User
from api.v1.users import get_current_user
from schemas.drawing import DrawingRead

router = APIRouter(prefix="/user/collections", tags=["User Collections"])

@router.get("/likes", response_model=dict)
def get_user_likes(
    page: int = 1, 
    size: int = 20, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """获取用户点赞的画作"""
    # 连表查询：从 DrawingLike 表连接 Drawing 表
    q = db.query(Drawing).join(DrawingLike, Drawing.id == DrawingLike.drawing_id)\
        .filter(DrawingLike.user_id == current_user.id)\
        .order_by(DrawingLike.created_at.desc())
    
    total = q.count()
    drawings = q.offset((page - 1) * size).limit(size).all()
    
    result = []
    for d in drawings:
        d_data = DrawingRead.from_orm(d)
        # 既然在点赞列表里，那肯定是被点赞过的
        d_data.is_liked = True
        # 顺便查一下是否被收藏
        fav_exists = db.query(DrawingFavorite).filter(
            DrawingFavorite.user_id == current_user.id, 
            DrawingFavorite.drawing_id == d.id
        ).first()
        d_data.is_favorited = bool(fav_exists)
        result.append(d_data)
        
    return {"code": 200, "msg": "OK", "data": result, "total": total}

@router.get("/favorites", response_model=dict)
def get_user_favorites(
    page: int = 1, 
    size: int = 20, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """获取用户收藏的画作"""
    q = db.query(Drawing).join(DrawingFavorite, Drawing.id == DrawingFavorite.drawing_id)\
        .filter(DrawingFavorite.user_id == current_user.id)\
        .order_by(DrawingFavorite.created_at.desc())
    
    total = q.count()
    drawings = q.offset((page - 1) * size).limit(size).all()
    
    result = []
    for d in drawings:
        d_data = DrawingRead.from_orm(d)
        d_data.is_favorited = True
        # 顺便查一下是否被点赞
        like_exists = db.query(DrawingLike).filter(
            DrawingLike.user_id == current_user.id, 
            DrawingLike.drawing_id == d.id
        ).first()
        d_data.is_liked = bool(like_exists)
        result.append(d_data)
        
    return {"code": 200, "msg": "OK", "data": result, "total": total}
