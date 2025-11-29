from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.user_favorite import UserFavorite
from models.user_prompt_keyword import UserPromptKeyword
from schemas.prompt import PromptKeywordRead

fav_router = APIRouter(prefix="/admin/user_favorites")

@fav_router.get("/")
def list_favorites(user_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(UserFavorite)
    if user_id:
        q = q.filter(UserFavorite.user_id == user_id)
    return q.all()

@fav_router.post("/add")
def add_favorite(user_id: int, keyword_id: int, db: Session = Depends(get_db)):
    """某用户(调用ID)通过提示词ID将某提示词添加到收藏。"""
    # 检查是否存在
    exists = db.query(UserFavorite).filter(UserFavorite.user_id == user_id, UserFavorite.keyword_id == keyword_id).first()
    if exists:
         return {"code": 200, "msg": "已存在", "data": True}
    
    obj = UserFavorite(user_id=user_id, keyword_id=keyword_id)
    db.add(obj)
    db.commit()
    return {"code": 200, "msg": "添加成功", "data": True}

@fav_router.post("/remove")
def remove_favorite(user_id: int, keyword_id: int, db: Session = Depends(get_db)):
    """某用户(调用ID)取消收藏某提示词。"""
    obj = db.query(UserFavorite).filter(UserFavorite.user_id == user_id, UserFavorite.keyword_id == keyword_id).first()
    if not obj:
        # 如果不存在，也视为取消成功
        return {"code": 500, "msg": "提示词不存在", "data": False}
    
    db.delete(obj)
    db.commit()
    return {"code": 200, "msg": "取消成功", "data": True}

@fav_router.post("/")
def create_favorite(user_id: int, keyword_id: int, db: Session = Depends(get_db)):
    obj = UserFavorite(user_id=user_id, keyword_id=keyword_id)
    db.merge(obj)
    db.commit()
    return {"code": 200, "msg": "OK", "data": True}

@fav_router.delete("/")
def delete_favorite(user_id: int, keyword_id: int, db: Session = Depends(get_db)):
    obj = db.query(UserFavorite).filter(UserFavorite.user_id == user_id, UserFavorite.keyword_id == keyword_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(obj)
    db.commit()
    return {"code": 200, "msg": "OK", "data": True}

upk_router = APIRouter(prefix="/admin/user_prompt_keywords")

@upk_router.get("/")
def list_user_prompt_keywords(user_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(UserPromptKeyword)
    if user_id:
        q = q.filter(UserPromptKeyword.user_id == user_id)
    return q.all()

@upk_router.post("/")
def create_user_prompt_keyword(user_id: int, keyword_id: int, used_count: int = 1, db: Session = Depends(get_db)):
    obj = UserPromptKeyword(user_id=user_id, keyword_id=keyword_id, used_count=used_count)
    db.merge(obj)
    db.commit()
    return {"code": 200, "msg": "OK", "data": True}

@upk_router.put("/")
def update_user_prompt_keyword(user_id: int, keyword_id: int, used_count: int, db: Session = Depends(get_db)):
    obj = db.query(UserPromptKeyword).filter(UserPromptKeyword.user_id == user_id, UserPromptKeyword.keyword_id == keyword_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Not found")
    obj.used_count = used_count
    db.commit()
    return {"code": 200, "msg": "OK", "data": True}

@upk_router.post("/increment")
def increment_usage(user_id: int, keyword_id: int, db: Session = Depends(get_db)):
    """记录提示词使用：不存在则创建(count=1)，存在则+1。"""
    from sqlalchemy.sql import func
    
    obj = db.query(UserPromptKeyword).filter(UserPromptKeyword.user_id == user_id, UserPromptKeyword.keyword_id == keyword_id).first()
    if not obj:
        obj = UserPromptKeyword(user_id=user_id, keyword_id=keyword_id, used_count=1)
        db.add(obj)
    else:
        obj.used_count += 1
        obj.last_used_at = func.now()
    
    db.commit()
    return {"code": 200, "msg": "记录成功", "data": True}

@upk_router.delete("/")
def delete_user_prompt_keyword(user_id: int, keyword_id: int, db: Session = Depends(get_db)):
    obj = db.query(UserPromptKeyword).filter(UserPromptKeyword.user_id == user_id, UserPromptKeyword.keyword_id == keyword_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(obj)
    db.commit()
    return {"code": 200, "msg": "OK", "data": True}

