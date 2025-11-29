"""提示词层级获取接口。

提供从大类 -> 小类 -> 关键词的逐级查询能力。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database import get_db
from models.prompt_category import PromptCategory
from models.prompt_subcategory import PromptSubcategory
from models.prompt_keyword import PromptKeyword
from models.prompt_log import PromptLog
from models.user import User

router = APIRouter(prefix="/prompts")

class PromptLogCreate(BaseModel):
    user_id: int
    drawing_id: Optional[int] = None
    small_category_id: int
    weight: float
    is_negative: Optional[bool] = None  # 映射到 DB 的 is_navigate

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

    new_log = PromptLog(
        user_id=log_in.user_id,
        drawing_id=log_in.drawing_id,
        small_category_id=log_in.small_category_id,
        weight=log_in.weight,
        is_navigate=log_in.is_negative  # 对应表中的 is_navigate 字段
    )
    db.add(new_log)
    db.commit()
    db.refresh(new_log)
    
    return {"code": 200, "msg": "日志记录成功", "data": new_log}

@router.delete("/keywords/{keyword_id}")
def delete_keyword(keyword_id: int, db: Session = Depends(get_db)):
    """根据ID删除提示词。"""
    item = db.query(PromptKeyword).filter(PromptKeyword.id == keyword_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="提示词不存在")
    db.delete(item)
    db.commit()
    return {"code": 200, "msg": "删除成功", "data": True}

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

