"""提示词层级获取接口。

提供从大类 -> 小类 -> 关键词的逐级查询能力。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from pydantic import BaseModel
from typing import Optional
from database import get_db
from models.prompt_category import PromptCategory
from models.prompt_subcategory import PromptSubcategory
from models.prompt_keyword import PromptKeyword
from models.user_prompt_keyword import UserPromptKeyword
from models.prompt_log import PromptLog
from models.user import User
from schemas.prompt import PromptKeywordCreate
from api.v1.users import get_current_user, get_current_user_optional

router = APIRouter(prefix="/prompts")

class PromptLogCreate(BaseModel):
    user_id: int
    prompt_id:int
    drawing_id: Optional[int] = None
    small_category_id: int
    weight: float
    is_negative: Optional[bool] = None

@router.post("/logs")
def create_prompt_log(log_in: PromptLogCreate, db: Session = Depends(get_db)):
    """
    记录提示词使用日志。
    记录某人什么时候(自动生成)，在哪个画上，使用了什么提示词(这里指分类)，是否负面，权重是多少。
    """
    # 简单验证用户
    user = db.query(User).filter(User.id == log_in.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    prompt = db.query(PromptKeyword).filter(PromptKeyword.id == log_in.prompt_id).first()
    if not prompt:
      raise HTTPException(status_code=404,detail="关键词不存在")

    new_log = PromptLog(
        user_id=log_in.user_id,
        prompt_id = log_in.prompt_id,
        drawing_id=log_in.drawing_id,
        small_category_id=log_in.small_category_id,
        weight=log_in.weight,
        is_negative=log_in.is_negative
    )
    db.add(new_log)
    db.commit()
    db.refresh(new_log)
    
    return {"code": 200, "msg": "日志记录成功", "data": new_log}

@router.get("/logs")
def get_prompt_logs(
    user_id: Optional[int] = None,
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取提示词使用日志。
    - 如果提供 user_id，则获取该用户的日志。
    - 如果不提供 user_id (仅管理员)，则获取所有日志。
    """
    q = db.query(PromptLog)
    if user_id:
        # Check if user is accessing their own logs or is admin
        if current_user.id != user_id and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="无权限查看他人日志")
        q = q.filter(PromptLog.user_id == user_id)
    else:
        # If no user_id provided, only admin can view all
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="无权限查看所有日志")
    
    total = q.count()
    logs = q.order_by(PromptLog.used_at.desc())\
            .offset((page - 1) * size)\
            .limit(size)\
            .all()
            
    return {"code": 200, "msg": "OK", "data": logs, "total": total}

@router.post("/keywords")
def create_keyword(
    keyword_in: PromptKeywordCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    用户添加一个新的提示词在某个小分类上。
    """
    # 验证小分类
    subcategory = db.query(PromptSubcategory).filter(PromptSubcategory.id == keyword_in.small_category_id).first()
    if not subcategory:
        raise HTTPException(status_code=404, detail="小分类不存在")

    new_keyword = PromptKeyword(
        word=keyword_in.word,
        display_name=keyword_in.display_name,
        small_category_id=keyword_in.small_category_id,
        created_by=current_user.id,
        usage_count=1  # 新增关键词初始热度为1
    )
    db.add(new_keyword)
    db.commit()
    db.refresh(new_keyword)

    return {"code": 200, "msg": "提示词创建成功", "data": new_keyword}

@router.delete("/keywords/{keyword_id}")
def delete_keyword(keyword_id: int, user_id: int, db: Session = Depends(get_db)):
    """
    删除提示词。
    - 用户只能删除自己创建的。
    - 管理员可以删除所有。
    """
    # 获取操作用户
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 获取提示词
    item = db.query(PromptKeyword).filter(PromptKeyword.id == keyword_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="提示词不存在")

    # 权限检查
    # 如果是管理员(role='admin')，或者 created_by == user_id，则允许删除
    # 注意：根据 User 模型定义，role 默认为 'user'
    is_admin = (user.role == 'admin')
    is_owner = (item.created_by == user.id)

    if not (is_admin or is_owner):
        raise HTTPException(status_code=403, detail="无权限删除此提示词")

    db.delete(item)
    db.commit()
    return {"code": 200, "msg": "删除成功", "data": True}

@router.post("/keywords/{keyword_id}/increment_usage")
def increment_keyword_usage(keyword_id: int, db: Session = Depends(get_db)):
    """
    增加提示词热度值。
    当用户从选择区选择提示词时调用。
    """
    keyword = db.query(PromptKeyword).filter(PromptKeyword.id == keyword_id).first()
    if not keyword:
        raise HTTPException(status_code=404, detail="提示词不存在")
    
    keyword.usage_count = (keyword.usage_count or 0) + 1
    db.commit()
    db.refresh(keyword)
    return {"code": 200, "msg": "热度更新成功", "data": keyword.usage_count}


@router.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    """获取所有大分类。"""
    items = db.query(PromptCategory).order_by(PromptCategory.sort_order).all()
    return {"code": 200, "msg": "OK", "data": items}

@router.get("/categories/{category_id}/subcategories")
def get_subcategories(category_id: int, db: Session = Depends(get_db)):
    """获取指定大分类下的所有小分类。"""
    items = db.query(PromptSubcategory).filter(PromptSubcategory.category_id == category_id).order_by(PromptSubcategory.sort_order).all()
    return {"code": 200, "msg": "OK", "data": items}

@router.get("/subcategories/{subcategory_id}/keywords")
def get_keywords(subcategory_id: int, db: Session = Depends(get_db)):
    """获取指定小分类下的所有提示词。"""
    items = db.query(PromptKeyword).filter(PromptKeyword.small_category_id == subcategory_id).all()
    return {"code": 200, "msg": "OK", "data": items}

@router.get("/search")
def search_keywords(q: str, db: Session = Depends(get_db)):
    """
    Search for keywords by word or display_name.
    """
    if not q:
        return {"code": 200, "msg": "OK", "data": []}
    
    keywords = db.query(PromptKeyword).filter(
        or_(
            PromptKeyword.word.ilike(f"%{q}%"),
            PromptKeyword.display_name.ilike(f"%{q}%")
        )
    ).limit(20).all()
    
    return {"code": 200, "msg": "OK", "data": keywords}

@router.get("/categories/{category_id}/tree")
def get_category_tree(category_id: int, db: Session = Depends(get_db)):
    """
    获取指定大分类下的所有小分类及其关联的提示词（嵌套结构）。
    返回格式示例：
    [
      {
        "id": 1,
        "name": "sub_cat_1",
        "display_name": "小分类1",
        "keywords": [
          { "id": 101, "word": "keyword1" },
          ...
        ]
      },
      ...
    ]
    """
    # 1. 获取该大类下的所有小类
    subcategories = db.query(PromptSubcategory)\
        .filter(PromptSubcategory.category_id == category_id)\
        .order_by(PromptSubcategory.sort_order)\
        .all()
    
    if not subcategories:
        return {"code": 200, "msg": "OK", "data": []}

    # 2. 获取这些小类下的所有提示词
    subcategory_ids = [sub.id for sub in subcategories]
    keywords = db.query(PromptKeyword)\
        .filter(PromptKeyword.small_category_id.in_(subcategory_ids))\
        .all()

    # 3. 将提示词按小类ID分组
    keywords_map = {}
    for kw in keywords:
        sid = kw.small_category_id
        if sid not in keywords_map:
            keywords_map[sid] = []
        keywords_map[sid].append({
            "id": kw.id,
            "word": kw.word,
            "created_by": kw.created_by
        })

    # 4. 组装最终结果
    result = []
    for sub in subcategories:
        result.append({
            "id": sub.id,
            "name": sub.name,
            "display_name": sub.display_name,
            "sort_order": sub.sort_order,
            "keywords": keywords_map.get(sub.id, [])
        })

    return {"code": 200, "msg": "OK", "data": result}

