from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.user_favorite import UserFavorite
from models.user_prompt_keyword import UserPromptKeyword
from schemas.prompt import PromptKeywordRead

fav_router = APIRouter(prefix="/admin/user_favorites")

from models.prompt_keyword import PromptKeyword

@fav_router.get("/")
def list_favorites(user_id: int | None = None, db: Session = Depends(get_db)):
    """获取收藏列表（包含提示词详情）。"""
    q = db.query(UserFavorite, PromptKeyword).join(PromptKeyword, UserFavorite.keyword_id == PromptKeyword.id)
    if user_id:
        q = q.filter(UserFavorite.user_id == user_id)
    
    results = q.all()
    data = []
    for fav, keyword in results:
        data.append({
            "user_id": fav.user_id,
            "keyword_id": fav.keyword_id,
            "favorited_at": fav.favorited_at,
            "keyword": {
                "id": keyword.id,
                "word": keyword.word,
                "small_category_id": keyword.small_category_id
            }
        })
    return {"code": 200, "msg": "OK", "data": data}

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
    """获取提示词使用统计（包含提示词详情）。"""
    q = db.query(UserPromptKeyword, PromptKeyword).join(PromptKeyword, UserPromptKeyword.keyword_id == PromptKeyword.id)
    if user_id:
        q = q.filter(UserPromptKeyword.user_id == user_id)
    
    results = q.all()
    data = []
    for upk, keyword in results:
        data.append({
            "user_id": upk.user_id,
            "keyword_id": upk.keyword_id,
            "used_count": upk.used_count,
            "last_used_at": upk.last_used_at,
            "first_used_at": getattr(upk, 'first_used_at', None),
            "keyword": {
                "id": keyword.id,
                "word": keyword.word,
                "small_category_id": keyword.small_category_id
            }
        })
    return {"code": 200, "msg": "OK", "data": data}

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
        obj = UserPromptKeyword(user_id=user_id, keyword_id=keyword_id, used_count=1, first_used_at = func.now())
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

