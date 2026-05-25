"""通用 CRUD 路由生成器。

为具备单键主键的模型快速生成列表、详情、创建、更新、删除接口。
支持基于常见字符串字段的简单模糊查询与分页参数。
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Type, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from database import get_db

STRING_SEARCH_FIELDS = [
    'name', 'display_name', 'word', 'username', 'email', 'model_name', 'label'
]

def apply_updates(obj, data: dict):
    """将请求体中的非空字段应用到 ORM 对象。"""
    for k, v in data.items():
        if v is not None and hasattr(obj, k):
            setattr(obj, k, v)

def create_crud_router(model: Type, read_schema: Type, create_schema: Type, update_schema: Type, prefix: str):
    """为给定模型创建 CRUD 路由。

    参数：
    - model: ORM 模型类
    - read_schema/create_schema/update_schema: 对应的 Pydantic 模型
    - prefix: 路由前缀，例如 `/admin/users`
    """
    router = APIRouter(prefix=prefix)

    @router.get("/")
    def list_items(page: int = 1, size: int = 10, q: Optional[str] = None, db: Session = Depends(get_db)):
        """分页列出资源，支持简单模糊查询。"""
        stmt = select(model)
        if q:
            search_conditions = []
            for field in STRING_SEARCH_FIELDS:
                if hasattr(model, field):
                    search_conditions.append(getattr(model, field).ilike(f"%{q}%"))
            if search_conditions:
                from sqlalchemy import or_
                stmt = stmt.where(or_(*search_conditions))
        
        # 计算总数
        # 注意：在大数据量下建议优化 count 查询
        total_stmt = select(func.count()).select_from(stmt.subquery())
        # 简单实现：直接查全量长度（小数据量可行）
        # total = len(db.execute(stmt).scalars().all()) 
        # 更优实现：
        total = db.scalar(select(func.count()).select_from(stmt))

        items = db.execute(stmt.offset((page - 1) * size).limit(size)).scalars().all()
        
        return {
            "code": 200,
            "msg": "OK",
            "data": items,
            "total": total,
            "page": page,
            "size": size
        }

    @router.get("/{item_id}")
    def get_item(item_id: int, db: Session = Depends(get_db)):
        """获取指定资源详情。"""
        obj = db.get(model, item_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Not found")
        return {"code": 200, "msg": "OK", "data": obj}

    @router.post("/")
    def create_item(payload: create_schema, db: Session = Depends(get_db)):
        """创建资源。"""
        obj = model(**payload.dict())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return {"code": 200, "msg": "OK", "data": obj}

    @router.put("/{item_id}")
    def update_item(item_id: int, payload: update_schema, db: Session = Depends(get_db)):
        """全量更新资源。"""
        obj = db.get(model, item_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Not found")
        apply_updates(obj, payload.dict())
        db.commit()
        db.refresh(obj)
        return {"code": 200, "msg": "OK", "data": obj}

    @router.patch("/{item_id}")
    def patch_item(item_id: int, payload: update_schema, db: Session = Depends(get_db)):
        """部分更新资源。"""
        obj = db.get(model, item_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Not found")
        apply_updates(obj, payload.dict(exclude_unset=True))
        db.commit()
        db.refresh(obj)
        return {"code": 200, "msg": "OK", "data": obj}

    @router.delete("/{item_id}")
    def delete_item(item_id: int, db: Session = Depends(get_db)):
        """删除资源。"""
        obj = db.get(model, item_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Not found")
        db.delete(obj)
        db.commit()
        return {"code": 200, "msg": "OK", "data": True}

    return router

