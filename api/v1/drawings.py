from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_
from typing import Optional
from pydantic import BaseModel

from database import get_db
from models.drawing import Drawing
from models.user import User
from schemas.drawing import DrawingRead
from api.v1.users import get_current_user, get_current_user_optional
from services.cos import COSStorageService, StorageManager
from core.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/drawings")

class DrawingCreate(BaseModel):
    user_id: Optional[int] = None  # 忽略此字段，使用 current_user.id
    title: Optional[str] = None
    prompt: str
    negative_prompt: Optional[str] = None
    model_name: str
    image_url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    seed: Optional[str] = None
    ai_response_time_ms: Optional[int] = None
    status: str

class DrawingPublicUpdate(BaseModel):
    is_public: bool

class DrawingStatusUpdate(BaseModel):
    status: str

class DrawingTitleUpdate(BaseModel):
    title: str

@router.put("/{drawing_id}/title")
def update_drawing_title(drawing_id: int, update_in: DrawingTitleUpdate, db: Session = Depends(get_db)):
    """
    根据ID修改绘图的标题 (title)。
    """
    drawing = db.query(Drawing).filter(Drawing.id == drawing_id).first()
    if not drawing:
        raise HTTPException(status_code=404, detail="绘图记录不存在")

    drawing.title = update_in.title
    db.commit()
    db.refresh(drawing)

    return {"code": 200, "msg": "标题更新成功", "data": drawing}

@router.post("/create")
def create_drawing(drawing_in: DrawingCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    创建绘图记录。
    状态默认为 'finish'。
    """
    # 使用当前登录用户ID，忽略传入的user_id

    new_drawing = Drawing(
        user_id=current_user.id,
        title=drawing_in.title,
        prompt=drawing_in.prompt,
        negative_prompt=drawing_in.negative_prompt,
        model_name=drawing_in.model_name,
        image_url=drawing_in.image_url,
        width=drawing_in.width,
        height=drawing_in.height,
        seed=drawing_in.seed,
        ai_response_time_ms=drawing_in.ai_response_time_ms,
        status="finish"  # 默认状态
    )
    db.add(new_drawing)
    db.commit()
    db.refresh(new_drawing)

    return {"code": 200, "msg": "绘图记录创建成功", "data": new_drawing}

@router.put("/{drawing_id}/public")
def update_drawing_public(drawing_id: int, update_in: DrawingPublicUpdate, db: Session = Depends(get_db)):
    """
    根据ID修改绘图的公开状态 (is_public)。
    """
    drawing = db.query(Drawing).filter(Drawing.id == drawing_id).first()
    if not drawing:
        raise HTTPException(status_code=404, detail="绘图记录不存在")

    drawing.is_public = update_in.is_public
    db.commit()
    db.refresh(drawing)

    return {"code": 200, "msg": "公开状态更新成功", "data": drawing}

@router.put("/{drawing_id}/status")
def update_drawing_status(drawing_id: int, update_in: DrawingStatusUpdate, db: Session = Depends(get_db)):
    """
    根据ID修改绘图的状态 (status)。
    例如设置为 'delete' 或其他。
    """
    drawing = db.query(Drawing).filter(Drawing.id == drawing_id).first()
    if not drawing:
        raise HTTPException(status_code=404, detail="绘图记录不存在")

    drawing.status = update_in.status
    db.commit()
    db.refresh(drawing)

    return {"code": 200, "msg": "状态更新成功", "data": drawing}

@router.get("/{drawing_id}")
def get_drawing_detail(drawing_id: int, db: Session = Depends(get_db)):
    """
    获取单个绘图记录详情。
    """
    drawing = db.query(Drawing).filter(Drawing.id == drawing_id).first()
    if not drawing:
        raise HTTPException(status_code=404, detail="绘图记录不存在")

    # Enrich with user info
    result = DrawingRead.from_orm(drawing)
    user = db.query(User).filter(User.id == drawing.user_id).first()
    if user:
        result.username = user.username
        result.nickname = user.nickname
        result.avatar_url = user.avatar_url

    return {"code": 200, "msg": "OK", "data": result}

@router.get("/")
def list_drawings(
    user_id: Optional[int] = None,
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取绘图记录列表。
    - 如果提供 user_id，则获取该用户的绘图 (需本人或管理员)。
    - 如果不提供 user_id (仅管理员)，则获取所有绘图。
    """
    if user_id:
        if current_user.id != user_id and current_user.role != "admin":
             raise HTTPException(status_code=403, detail="无权限查看他人绘图记录")
        q = db.query(Drawing).filter(
            Drawing.user_id == user_id,
            Drawing.status != "delete",
            or_(
                and_(
                    Drawing.image_url.isnot(None),
                    Drawing.image_url != ""
                ),
                and_(
                    Drawing.local_url.isnot(None),
                    Drawing.local_url != ""
                )
            )
        )
    else:
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="无权限查看所有绘图记录")
        q = db.query(Drawing).filter(
            Drawing.status != "delete",
            or_(
                and_(
                    Drawing.image_url.isnot(None),
                    Drawing.image_url != ""
                ),
                and_(
                    Drawing.local_url.isnot(None),
                    Drawing.local_url != ""
                )
            )
        )

    total = q.count()
    drawings = q.order_by(Drawing.created_at.desc())\
            .offset((page - 1) * size)\
            .limit(size)\
            .all()

    return {"code": 200, "msg": "OK", "data": drawings, "total": total}


@router.delete("/{drawing_id}")
async def delete_drawing(
    drawing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除绘图记录。
    同时删除 COS 中的图片文件（原图和缩略图）。

    Requirements: 6.1, 6.2, 6.3, 7.3
    """
    drawing = db.query(Drawing).filter(Drawing.id == drawing_id).first()
    if not drawing:
        raise HTTPException(status_code=404, detail="绘图记录不存在")

    # 权限检查：只有作者本人或管理员可以删除
    if current_user.id != drawing.user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权限删除此绘图")

    # 1. 先删除 COS 文件
    cos_service = COSStorageService()
    cos_deleted = False

    try:
        # 删除原图
        if drawing.cos_key:
            await cos_service.delete_image(drawing.cos_key)
            logger.info(f"Deleted original image from COS: {drawing.cos_key}")

        # 删除缩略图
        if drawing.thumbnail_key:
            await cos_service.delete_image(drawing.thumbnail_key)
            logger.info(f"Deleted thumbnail from COS: {drawing.thumbnail_key}")

        cos_deleted = True
    except Exception as e:
        # COS 删除失败，记录日志但继续删除数据库记录
        logger.error(f"Failed to delete COS files for drawing {drawing_id}: {e}")

    # 2. 更新用户存储统计
    if drawing.file_size and cos_deleted:
        try:
            StorageManager.update_user_storage(
                drawing.user_id,
                -drawing.file_size,  # 负数表示减少
                db
            )
        except Exception as e:
            logger.error(f"Failed to update user storage: {e}")

    # 3. 删除数据库记录
    db.delete(drawing)
    db.commit()

    return {
        "code": 200,
        "msg": "绘图删除成功",
        "data": {
            "drawing_id": drawing_id,
            "cos_deleted": cos_deleted
        }
    }


@router.post("/batch-delete")
async def batch_delete_drawings(
    drawing_ids: list[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    批量删除绘图记录。

    Requirements: 6.4
    """
    deleted_count = 0
    failed_count = 0
    errors = []

    for drawing_id in drawing_ids:
        try:
            drawing = db.query(Drawing).filter(Drawing.id == drawing_id).first()
            if not drawing:
                failed_count += 1
                errors.append({"drawing_id": drawing_id, "error": "记录不存在"})
                continue

            # 权限检查
            if current_user.id != drawing.user_id and current_user.role != "admin":
                failed_count += 1
                errors.append({"drawing_id": drawing_id, "error": "无权限删除"})
                continue

            # 删除 COS 文件
            cos_service = COSStorageService()
            try:
                if drawing.cos_key:
                    await cos_service.delete_image(drawing.cos_key)
                if drawing.thumbnail_key:
                    await cos_service.delete_image(drawing.thumbnail_key)
            except Exception as e:
                logger.error(f"Failed to delete COS files for drawing {drawing_id}: {e}")

            # 更新存储统计
            if drawing.file_size:
                try:
                    StorageManager.update_user_storage(
                        drawing.user_id,
                        -drawing.file_size,
                        db
                    )
                except Exception as e:
                    logger.error(f"Failed to update user storage: {e}")

            # 删除数据库记录
            db.delete(drawing)
            db.commit()
            deleted_count += 1

        except Exception as e:
            failed_count += 1
            errors.append({"drawing_id": drawing_id, "error": str(e)})
            logger.error(f"Failed to delete drawing {drawing_id}: {e}")

    return {
        "code": 200,
        "msg": "批量删除完成",
        "data": {
            "deleted": deleted_count,
            "failed": failed_count,
            "errors": errors
        }
    }
