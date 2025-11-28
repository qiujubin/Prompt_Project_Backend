from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from core.security import decode_token
from database import get_db
from models.user import User
from schemas.user import UserRead

router = APIRouter(prefix="/users")

def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization:
        raise HTTPException(status_code=401, detail="未授权")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="未授权")
    payload = decode_token(token)
    username = payload.get("sub")
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="未授权")
    return user

@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)):
    return user