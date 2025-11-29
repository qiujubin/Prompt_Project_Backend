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

@upk_router.delete("/")
def delete_user_prompt_keyword(user_id: int, keyword_id: int, db: Session = Depends(get_db)):
    obj = db.query(UserPromptKeyword).filter(UserPromptKeyword.user_id == user_id, UserPromptKeyword.keyword_id == keyword_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(obj)
    db.commit()
    return {"code": 200, "msg": "OK", "data": True}

