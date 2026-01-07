"""预设相关接口。

提供预设的 CRUD 操作、选择、收藏等功能。

Requirements:
- 2.2, 2.3, 2.4, 2.6, 2.7: 预设分类展示
- 3.2, 3.3, 3.4: 预设预览功能
- 4.7, 4.8, 9.3, 9.5: 预设选择功能
- 5.7, 5.8, 5.9: 预设创建功能
- 6.1-6.7: 预设编辑功能
- 7.1, 7.2, 7.4, 7.5: 预设删除功能
- 8.1, 8.2, 8.3: 预设收藏功能
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, asc
from typing import Optional, List
from database import get_db
from models.prompt_preset import PromptPreset
from models.preset_item import PresetItem
from models.user_preset_favorite import UserPresetFavorite
from models.user_preset_usage import UserPresetUsage
from models.prompt_keyword import PromptKeyword
from models.prompt_subcategory import PromptSubcategory
from models.user import User
from schemas.preset import (
    PresetCreate, PresetUpdate, PresetRead, PresetListRead,
    PresetItemRead, PresetSelectResponse, PresetFavoriteResponse
)
from api.v1.users import get_current_user, get_current_user_optional

router = APIRouter(prefix="/presets")


def _get_preset_item_read(item: PresetItem) -> PresetItemRead:
    """将 PresetItem ORM 对象转换为 PresetItemRead schema。"""
    return PresetItemRead(
        id=item.id,
        preset_id=item.preset_id,
        keyword_id=item.keyword_id,
        weight=item.weight,
        sort_order=item.sort_order,
        keyword_word=item.keyword.word if item.keyword else None,
        keyword_display_name=item.keyword.display_name if item.keyword else None
    )


def _get_or_create_my_preset_subcategory(db: Session) -> int:
    """获取或创建"我的预设"小分类，返回其 ID。"""
    # 查找名为"我的预设"的小分类
    subcategory = db.query(PromptSubcategory).filter(
        PromptSubcategory.name == "my_presets"
    ).first()

    if not subcategory:
        # 如果不存在，创建一个
        # 首先需要找到或创建"预设"大分类
        from models.prompt_category import PromptCategory
        preset_category = db.query(PromptCategory).filter(
            PromptCategory.name == "presets"
        ).first()

        if not preset_category:
            # 创建预设大分类
            preset_category = PromptCategory(
                name="presets",
                display_name="预设",
                sort_order=999  # 放在最后
            )
            db.add(preset_category)
            db.flush()

        # 创建"我的预设"小分类
        subcategory = PromptSubcategory(
            category_id=preset_category.id,
            name="my_presets",
            display_name="我的预设",
            sort_order=999
        )
        db.add(subcategory)
        db.flush()

    return subcategory.id


@router.get("/", response_model=None)
def get_presets(
    subcategory_id: Optional[int] = None,
    sort_by: str = Query("hot", pattern="^(hot|common|newest)$"),
    favorites_first: bool = False,
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    获取预设列表。

    Requirements: 2.2, 2.3, 2.4, 2.6, 2.7
    - 2.2: WHEN a user clicks the preset category, THE Preset_System SHALL load and display preset subcategories
    - 2.3: THE Preset_System SHALL display Official_Preset items in their designated subcategories
    - 2.4: THE Preset_System SHALL display User_Preset items in a fixed "我的预设" subcategory
    - 2.6: WHEN displaying presets, THE Preset_System SHALL show both the English name and Chinese display_name
    - 2.7: IF the user is not logged in, THE Preset_System SHALL only display Official_Preset items

    Parameters:
    - subcategory_id: 筛选指定小分类的预设
    - sort_by: 排序方式 (hot=全局热度, common=个人常用, newest=最新)
    - favorites_first: 是否收藏优先
    - page, size: 分页参数
    """
    query = db.query(PromptPreset).options(
        joinedload(PromptPreset.items).joinedload(PresetItem.keyword)
    )

    # 未登录用户只能看到官方预设 (Requirement 2.7)
    if not current_user:
        query = query.filter(PromptPreset.is_official == True)
    else:
        # 登录用户可以看到官方预设和自己的预设
        query = query.filter(
            (PromptPreset.is_official == True) |
            (PromptPreset.created_by == current_user.id)
        )

    # 按小分类筛选
    if subcategory_id:
        query = query.filter(PromptPreset.subcategory_id == subcategory_id)

    # 排序逻辑
    if sort_by == "hot":
        query = query.order_by(desc(PromptPreset.usage_count))
    elif sort_by == "newest":
        query = query.order_by(desc(PromptPreset.created_at))
    elif sort_by == "common" and current_user:
        # 按个人使用次数排序，需要 left join
        query = query.outerjoin(
            UserPresetUsage,
            (UserPresetUsage.preset_id == PromptPreset.id) &
            (UserPresetUsage.user_id == current_user.id)
        ).order_by(desc(func.coalesce(UserPresetUsage.used_count, 0)))
    else:
        query = query.order_by(desc(PromptPreset.usage_count))

    # 收藏优先排序
    if favorites_first and current_user:
        # 需要重新构建查询以支持收藏优先
        pass  # 简化实现，后续可优化

    # 分页
    total = query.count()
    presets = query.offset((page - 1) * size).limit(size).all()

    # 构建响应数据
    result = []
    for preset in presets:
        # 获取用户收藏状态和使用次数
        is_favorited = False
        user_used_count = 0

        if current_user:
            favorite = db.query(UserPresetFavorite).filter(
                UserPresetFavorite.user_id == current_user.id,
                UserPresetFavorite.preset_id == preset.id
            ).first()
            is_favorited = favorite is not None

            usage = db.query(UserPresetUsage).filter(
                UserPresetUsage.user_id == current_user.id,
                UserPresetUsage.preset_id == preset.id
            ).first()
            user_used_count = usage.used_count if usage else 0

        result.append(PresetListRead(
            id=preset.id,
            name=preset.name,
            display_name=preset.display_name,
            subcategory_id=preset.subcategory_id,
            is_official=preset.is_official,
            usage_count=preset.usage_count,
            item_count=len(preset.items),
            is_favorited=is_favorited,
            user_used_count=user_used_count
        ))

    return {
        "code": 200,
        "msg": "OK",
        "data": result,
        "total": total,
        "page": page,
        "size": size
    }


@router.get("/{preset_id}", response_model=None)
def get_preset_detail(
    preset_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    获取预设详情。

    Requirements: 3.2, 3.3, 3.4
    - 3.2: THE Preset_Preview SHALL show all prompt items contained in the preset
    - 3.3: THE Preset_Preview SHALL display each prompt item's name, display_name, and weight
    - 3.4: THE Preset_Preview SHALL indicate the total number of prompts in the preset
    """
    preset = db.query(PromptPreset).options(
        joinedload(PromptPreset.items).joinedload(PresetItem.keyword)
    ).filter(PromptPreset.id == preset_id).first()

    if not preset:
        raise HTTPException(status_code=404, detail="预设不存在")

    # 权限检查：未登录用户只能查看官方预设
    if not current_user and not preset.is_official:
        raise HTTPException(status_code=403, detail="无权限查看此预设")

    # 登录用户只能查看官方预设或自己的预设
    if current_user and not preset.is_official and preset.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="无权限查看此预设")

    # 获取用户收藏状态和使用次数
    is_favorited = False
    user_used_count = 0

    if current_user:
        favorite = db.query(UserPresetFavorite).filter(
            UserPresetFavorite.user_id == current_user.id,
            UserPresetFavorite.preset_id == preset.id
        ).first()
        is_favorited = favorite is not None

        usage = db.query(UserPresetUsage).filter(
            UserPresetUsage.user_id == current_user.id,
            UserPresetUsage.preset_id == preset.id
        ).first()
        user_used_count = usage.used_count if usage else 0

    # 构建预设项列表
    items = [_get_preset_item_read(item) for item in sorted(preset.items, key=lambda x: x.sort_order)]

    return {
        "code": 200,
        "msg": "OK",
        "data": PresetRead(
            id=preset.id,
            name=preset.name,
            display_name=preset.display_name,
            subcategory_id=preset.subcategory_id,
            created_by=preset.created_by,
            is_official=preset.is_official,
            usage_count=preset.usage_count,
            created_at=preset.created_at,
            updated_at=preset.updated_at,
            items=items,
            is_favorited=is_favorited,
            user_used_count=user_used_count
        )
    }



@router.post("/", response_model=None)
def create_preset(
    preset_in: PresetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建预设。

    Requirements: 5.7, 5.8, 5.9
    - 5.7: WHEN a user confirms creation, THE Preset_System SHALL save the preset to the "我的预设" subcategory
    - 5.8: IF the preset name is empty, THE Preset_System SHALL prevent creation and show an error message
    - 5.9: IF the preset contains no prompts, THE Preset_System SHALL prevent creation and show an error message

    验证逻辑已在 PresetCreate schema 中实现。
    """
    # 验证所有关键词是否存在
    keyword_ids = [item.keyword_id for item in preset_in.items]
    existing_keywords = db.query(PromptKeyword.id).filter(
        PromptKeyword.id.in_(keyword_ids)
    ).all()
    existing_ids = {kw.id for kw in existing_keywords}

    missing_ids = set(keyword_ids) - existing_ids
    if missing_ids:
        raise HTTPException(
            status_code=400,
            detail=f"提示词不存在: {list(missing_ids)}"
        )

    # 获取或创建"我的预设"小分类
    my_preset_subcategory_id = _get_or_create_my_preset_subcategory(db)

    # 创建预设
    new_preset = PromptPreset(
        name=preset_in.name,
        display_name=preset_in.display_name,
        subcategory_id=my_preset_subcategory_id,
        created_by=current_user.id,
        is_official=False,
        usage_count=0
    )
    db.add(new_preset)
    db.flush()  # 获取 preset id

    # 创建预设项
    for idx, item in enumerate(preset_in.items):
        preset_item = PresetItem(
            preset_id=new_preset.id,
            keyword_id=item.keyword_id,
            weight=item.weight,
            sort_order=item.sort_order if item.sort_order else idx
        )
        db.add(preset_item)

    db.commit()
    db.refresh(new_preset)

    # 重新加载预设以获取完整数据
    preset = db.query(PromptPreset).options(
        joinedload(PromptPreset.items).joinedload(PresetItem.keyword)
    ).filter(PromptPreset.id == new_preset.id).first()

    items = [_get_preset_item_read(item) for item in sorted(preset.items, key=lambda x: x.sort_order)]

    return {
        "code": 200,
        "msg": "预设创建成功",
        "data": PresetRead(
            id=preset.id,
            name=preset.name,
            display_name=preset.display_name,
            subcategory_id=preset.subcategory_id,
            created_by=preset.created_by,
            is_official=preset.is_official,
            usage_count=preset.usage_count,
            created_at=preset.created_at,
            updated_at=preset.updated_at,
            items=items,
            is_favorited=False,
            user_used_count=0
        )
    }



@router.put("/{preset_id}", response_model=None)
def update_preset(
    preset_id: int,
    preset_in: PresetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新预设。

    Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7
    - 6.1: THE Preset_System SHALL allow users to edit their own User_Preset items
    - 6.2: THE Preset_System SHALL NOT allow users to edit Official_Preset items
    - 6.3: WHEN editing, THE Preset_System SHALL allow modification of preset name and display_name
    - 6.4: WHEN editing, THE Preset_System SHALL allow adding or removing prompts
    - 6.5: WHEN editing, THE Preset_System SHALL allow adjusting prompt weights
    - 6.6: WHEN editing, THE Preset_System SHALL allow reordering prompts within the preset
    - 6.7: WHEN a user saves edits, THE Preset_System SHALL update the preset in the database
    """
    preset = db.query(PromptPreset).filter(PromptPreset.id == preset_id).first()

    if not preset:
        raise HTTPException(status_code=404, detail="预设不存在")

    # 权限检查：不能编辑官方预设 (Requirement 6.2)
    if preset.is_official:
        raise HTTPException(status_code=403, detail="无权限编辑官方预设")

    # 权限检查：只能编辑自己的预设 (Requirement 6.1)
    if preset.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="无权限编辑此预设")

    # 更新名称 (Requirement 6.3)
    if preset_in.name is not None:
        preset.name = preset_in.name
    if preset_in.display_name is not None:
        preset.display_name = preset_in.display_name

    # 更新预设项 (Requirements 6.4, 6.5, 6.6)
    if preset_in.items is not None:
        # 验证所有关键词是否存在
        keyword_ids = [item.keyword_id for item in preset_in.items]
        existing_keywords = db.query(PromptKeyword.id).filter(
            PromptKeyword.id.in_(keyword_ids)
        ).all()
        existing_ids = {kw.id for kw in existing_keywords}

        missing_ids = set(keyword_ids) - existing_ids
        if missing_ids:
            raise HTTPException(
                status_code=400,
                detail=f"提示词不存在: {list(missing_ids)}"
            )

        # 删除旧的预设项
        db.query(PresetItem).filter(PresetItem.preset_id == preset_id).delete()

        # 创建新的预设项
        for idx, item in enumerate(preset_in.items):
            preset_item = PresetItem(
                preset_id=preset_id,
                keyword_id=item.keyword_id,
                weight=item.weight,
                sort_order=item.sort_order if item.sort_order else idx
            )
            db.add(preset_item)

    db.commit()
    db.refresh(preset)

    # 重新加载预设以获取完整数据
    preset = db.query(PromptPreset).options(
        joinedload(PromptPreset.items).joinedload(PresetItem.keyword)
    ).filter(PromptPreset.id == preset_id).first()

    items = [_get_preset_item_read(item) for item in sorted(preset.items, key=lambda x: x.sort_order)]

    # 获取用户收藏状态和使用次数
    favorite = db.query(UserPresetFavorite).filter(
        UserPresetFavorite.user_id == current_user.id,
        UserPresetFavorite.preset_id == preset.id
    ).first()
    is_favorited = favorite is not None

    usage = db.query(UserPresetUsage).filter(
        UserPresetUsage.user_id == current_user.id,
        UserPresetUsage.preset_id == preset.id
    ).first()
    user_used_count = usage.used_count if usage else 0

    return {
        "code": 200,
        "msg": "预设更新成功",
        "data": PresetRead(
            id=preset.id,
            name=preset.name,
            display_name=preset.display_name,
            subcategory_id=preset.subcategory_id,
            created_by=preset.created_by,
            is_official=preset.is_official,
            usage_count=preset.usage_count,
            created_at=preset.created_at,
            updated_at=preset.updated_at,
            items=items,
            is_favorited=is_favorited,
            user_used_count=user_used_count
        )
    }



@router.delete("/{preset_id}", response_model=None)
def delete_preset(
    preset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除预设。

    Requirements: 7.1, 7.2, 7.4, 7.5
    - 7.1: THE Preset_System SHALL allow users to delete their own User_Preset items
    - 7.2: THE Preset_System SHALL NOT allow users to delete Official_Preset items
    - 7.4: WHEN deletion is confirmed, THE Preset_System SHALL remove the preset and all its items from the database
    - 7.5: WHEN deletion is confirmed, THE Preset_System SHALL remove any user favorites referencing this preset

    级联删除通过数据库外键约束 ON DELETE CASCADE 实现。
    """
    preset = db.query(PromptPreset).filter(PromptPreset.id == preset_id).first()

    if not preset:
        raise HTTPException(status_code=404, detail="预设不存在")

    # 权限检查：不能删除官方预设 (Requirement 7.2)
    if preset.is_official:
        raise HTTPException(status_code=403, detail="无权限删除官方预设")

    # 权限检查：只能删除自己的预设 (Requirement 7.1)
    if preset.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="无权限删除此预设")

    # 删除预设（级联删除 preset_items, user_preset_favorites, user_preset_usage）
    # 由于设置了 ON DELETE CASCADE，相关数据会自动删除 (Requirements 7.4, 7.5)
    db.delete(preset)
    db.commit()

    return {
        "code": 200,
        "msg": "预设删除成功",
        "data": True
    }



@router.post("/{preset_id}/select", response_model=None)
def select_preset(
    preset_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    选择预设，返回预设包含的所有提示词，并更新使用统计。

    Requirements: 4.7, 4.8, 9.3, 9.5
    - 4.7: WHEN a preset is selected, THE Preset_System SHALL increment the preset's usage_count
    - 4.8: WHEN a preset is selected, THE Preset_System SHALL increment the usage_count of each contained prompt_keyword
    - 9.3: WHEN a preset is selected, THE Preset_System SHALL increment both global and user-specific counts
    - 9.5: WHEN a preset is used, THE Preset_System SHALL also increment usage statistics for each contained prompt
    """
    preset = db.query(PromptPreset).options(
        joinedload(PromptPreset.items).joinedload(PresetItem.keyword)
    ).filter(PromptPreset.id == preset_id).first()

    if not preset:
        raise HTTPException(status_code=404, detail="预设不存在")

    # 权限检查：未登录用户只能选择官方预设
    if not current_user and not preset.is_official:
        raise HTTPException(status_code=403, detail="无权限使用此预设")

    # 登录用户只能选择官方预设或自己的预设
    if current_user and not preset.is_official and preset.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="无权限使用此预设")

    # 1. 更新预设全局使用次数 (Requirement 4.7)
    preset.usage_count = (preset.usage_count or 0) + 1

    # 2. 更新每个提示词的使用次数 (Requirements 4.8, 9.5)
    for item in preset.items:
        if item.keyword:
            item.keyword.usage_count = (item.keyword.usage_count or 0) + 1

    # 3. 更新用户个人使用统计 (Requirement 9.3)
    if current_user:
        user_usage = db.query(UserPresetUsage).filter(
            UserPresetUsage.user_id == current_user.id,
            UserPresetUsage.preset_id == preset_id
        ).first()

        if user_usage:
            user_usage.used_count = (user_usage.used_count or 0) + 1
            user_usage.last_used_at = func.now()
        else:
            new_usage = UserPresetUsage(
                user_id=current_user.id,
                preset_id=preset_id,
                used_count=1
            )
            db.add(new_usage)

    db.commit()

    # 构建响应数据
    items = [_get_preset_item_read(item) for item in sorted(preset.items, key=lambda x: x.sort_order)]

    return {
        "code": 200,
        "msg": "预设选择成功",
        "data": PresetSelectResponse(
            preset_id=preset.id,
            preset_name=preset.name,
            items=items
        )
    }



@router.post("/{preset_id}/favorite", response_model=None)
def toggle_preset_favorite(
    preset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    收藏/取消收藏预设。

    Requirements: 8.1, 8.2, 8.3
    - 8.1: THE Preset_System SHALL allow logged-in users to favorite any preset (both Official and User presets)
    - 8.2: WHEN a user favorites a preset, THE Preset_System SHALL store the favorite relationship in the database
    - 8.3: WHEN a user unfavorites a preset, THE Preset_System SHALL remove the favorite relationship
    """
    preset = db.query(PromptPreset).filter(PromptPreset.id == preset_id).first()

    if not preset:
        raise HTTPException(status_code=404, detail="预设不存在")

    # 检查是否已收藏
    existing_favorite = db.query(UserPresetFavorite).filter(
        UserPresetFavorite.user_id == current_user.id,
        UserPresetFavorite.preset_id == preset_id
    ).first()

    if existing_favorite:
        # 取消收藏 (Requirement 8.3)
        db.delete(existing_favorite)
        db.commit()
        return {
            "code": 200,
            "msg": "取消收藏成功",
            "data": PresetFavoriteResponse(
                preset_id=preset_id,
                is_favorited=False,
                message="取消收藏成功"
            )
        }
    else:
        # 添加收藏 (Requirements 8.1, 8.2)
        new_favorite = UserPresetFavorite(
            user_id=current_user.id,
            preset_id=preset_id
        )
        db.add(new_favorite)
        db.commit()
        return {
            "code": 200,
            "msg": "收藏成功",
            "data": PresetFavoriteResponse(
                preset_id=preset_id,
                is_favorited=True,
                message="收藏成功"
            )
        }
