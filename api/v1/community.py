from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, exists
from typing import Optional
from database import get_db
from models.drawing import Drawing
from models.drawing_interaction import DrawingLike, DrawingFavorite, DrawingComment
from models.user import User
from schemas.community import CommentCreate, CommentRead
from schemas.drawing import DrawingRead
from api.v1.users import get_current_user
from core.security import decode_token

router = APIRouter(prefix="/community")

def get_optional_current_user(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> Optional[User]:
    """尝试获取当前用户，如果未登录返回 None"""
    if not authorization:
        return None
    try:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer":
            return None
        payload = decode_token(token)
        username = payload.get("sub")
        if not username:
            return None
        user = db.query(User).filter(User.username == username).first()
        return user
    except:
        return None

@router.get("/feed", response_model=dict)
def get_community_feed(
    page: int = 1, 
    size: int = 20, 
    sort_by: str = "newest", # newest, hot
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """
    获取社区动态（公开的画作）。
    """
    q = db.query(Drawing).filter(Drawing.is_public == True, Drawing.status != 'delete')
    
    if sort_by == "hot":
        q = q.order_by(Drawing.like_count.desc(), Drawing.created_at.desc())
    else:
        q = q.order_by(Drawing.created_at.desc())
        
    total = q.count()
    drawings = q.offset((page - 1) * size).limit(size).all()
    
    # Enhance with user context if provided
    result = []
    user_id = current_user.id if current_user else None
    
    for d in drawings:
        d_data = DrawingRead.from_orm(d)
        if user_id:
            d_data.is_liked = db.query(exists().where(DrawingLike.user_id == user_id, DrawingLike.drawing_id == d.id)).scalar()
            d_data.is_favorited = db.query(exists().where(DrawingFavorite.user_id == user_id, DrawingFavorite.drawing_id == d.id)).scalar()
        result.append(d_data)
        
    return {"code": 200, "msg": "OK", "data": result, "total": total}

@router.post("/drawings/{drawing_id}/like")
def toggle_like(drawing_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """点赞/取消点赞"""
    drawing = db.query(Drawing).filter(Drawing.id == drawing_id).first()
    if not drawing:
        raise HTTPException(status_code=404, detail="Drawing not found")
        
    existing = db.query(DrawingLike).filter(DrawingLike.drawing_id == drawing_id, DrawingLike.user_id == current_user.id).first()
    
    if existing:
        db.delete(existing)
        drawing.like_count = max(0, drawing.like_count - 1)
        status = "unliked"
    else:
        new_like = DrawingLike(user_id=current_user.id, drawing_id=drawing_id)
        db.add(new_like)
        drawing.like_count += 1
        status = "liked"
        
    db.commit()
    return {"code": 200, "msg": "Success", "data": {"status": status, "count": drawing.like_count}}

@router.post("/drawings/{drawing_id}/favorite")
def toggle_favorite(drawing_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """收藏/取消收藏 (画作)"""
    drawing = db.query(Drawing).filter(Drawing.id == drawing_id).first()
    if not drawing:
        raise HTTPException(status_code=404, detail="Drawing not found")
        
    existing = db.query(DrawingFavorite).filter(DrawingFavorite.drawing_id == drawing_id, DrawingFavorite.user_id == current_user.id).first()
    
    if existing:
        db.delete(existing)
        drawing.favorite_count = max(0, drawing.favorite_count - 1)
        status = "unfavorited"
    else:
        new_fav = DrawingFavorite(user_id=current_user.id, drawing_id=drawing_id)
        db.add(new_fav)
        drawing.favorite_count += 1
        status = "favorited"
        
    db.commit()
    return {"code": 200, "msg": "Success", "data": {"status": status, "count": drawing.favorite_count}}

@router.post("/drawings/{drawing_id}/view")
def increment_view(drawing_id: int, db: Session = Depends(get_db)):
    """增加浏览量"""
    drawing = db.query(Drawing).filter(Drawing.id == drawing_id).first()
    if not drawing:
        raise HTTPException(status_code=404, detail="Drawing not found")
        
    drawing.view_count += 1
    db.commit()
    return {"code": 200, "msg": "Success", "data": {"count": drawing.view_count}}

@router.get("/drawings/{drawing_id}/comments")
def get_comments(drawing_id: int, page: int = 1, size: int = 20, db: Session = Depends(get_db)):
    """获取评论列表"""
    q = db.query(DrawingComment).filter(DrawingComment.drawing_id == drawing_id).order_by(DrawingComment.created_at.desc())
    total = q.count()
    comments = q.offset((page - 1) * size).limit(size).all()
    
    # Enrich with user info
    result = []
    for c in comments:
        c_data = CommentRead.from_orm(c)
        user = db.query(User).filter(User.id == c.user_id).first()
        if user:
            c_data.username = user.username
            c_data.avatar_url = user.avatar_url
        result.append(c_data)
        
    return {"code": 200, "msg": "OK", "data": result, "total": total}

@router.post("/drawings/{drawing_id}/comments")
def add_comment(drawing_id: int, comment: CommentCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """发表评论"""
    drawing = db.query(Drawing).filter(Drawing.id == drawing_id).first()
    if not drawing:
        raise HTTPException(status_code=404, detail="Drawing not found")
        
    new_comment = DrawingComment(
        user_id=current_user.id,
        drawing_id=drawing_id,
        content=comment.content,
        parent_id=comment.parent_id
    )
    db.add(new_comment)
    drawing.comment_count += 1
    db.commit()
    db.refresh(new_comment)
    
    return {"code": 200, "msg": "Success", "data": new_comment}
