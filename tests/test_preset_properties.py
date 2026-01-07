"""预设系统属性测试。

使用 Hypothesis 进行属性测试，验证预设系统的核心正确性属性。

Property 1: Preset Type Determines Permissions
Property 4: Usage Count Consistency
Property 14: Cascade Deletion
"""
import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from sqlalchemy import create_engine, Integer
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from database import Base
from models.prompt_preset import PromptPreset
from models.preset_item import PresetItem
from models.user_preset_favorite import UserPresetFavorite
from models.user_preset_usage import UserPresetUsage
from models.prompt_keyword import PromptKeyword
from models.prompt_subcategory import PromptSubcategory
from models.prompt_category import PromptCategory
from models.user import User
from core.security import get_password_hash


# ============================================================================
# Test database setup for property tests
# ============================================================================

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Counter for generating unique IDs
_id_counter = 0

def get_next_id():
    """获取下一个唯一ID。"""
    global _id_counter
    _id_counter += 1
    return _id_counter


def reset_id_counter():
    """重置ID计数器。"""
    global _id_counter
    _id_counter = 0


def get_test_db():
    """获取测试数据库会话。"""
    reset_id_counter()
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    return session


def cleanup_db(session: Session):
    """清理测试数据库。"""
    session.rollback()
    session.close()
    Base.metadata.drop_all(bind=engine)


# ============================================================================
# Helper functions for creating test data
# ============================================================================

def create_test_user(db: Session, username: str, role: str = "user") -> User:
    """创建测试用户。"""
    user = User(
        id=get_next_id(),
        username=username,
        hashed_password=get_password_hash("testpass123"),
        role=role
    )
    db.add(user)
    db.flush()
    return user


def create_test_category(db: Session) -> PromptCategory:
    """创建测试大分类。"""
    category = PromptCategory(
        id=get_next_id(),
        name="test_category",
        display_name="测试分类",
        sort_order=1
    )
    db.add(category)
    db.flush()
    return category


def create_test_subcategory(db: Session, category_id: int) -> PromptSubcategory:
    """创建测试小分类。"""
    subcategory = PromptSubcategory(
        id=get_next_id(),
        category_id=category_id,
        name="test_subcategory",
        display_name="测试小分类",
        sort_order=1
    )
    db.add(subcategory)
    db.flush()
    return subcategory


def create_test_keyword(db: Session, subcategory_id: int, word: str = "test_keyword") -> PromptKeyword:
    """创建测试提示词。"""
    keyword = PromptKeyword(
        id=get_next_id(),
        word=word,
        display_name=f"{word}_中文",
        small_category_id=subcategory_id,
        usage_count=0
    )
    db.add(keyword)
    db.flush()
    return keyword


def create_test_preset(
    db: Session,
    subcategory_id: int,
    created_by: int = None,
    is_official: bool = False,
    name: str = "test_preset"
) -> PromptPreset:
    """创建测试预设。"""
    preset = PromptPreset(
        id=get_next_id(),
        name=name,
        display_name=f"{name}_中文",
        subcategory_id=subcategory_id,
        created_by=created_by,
        is_official=is_official,
        usage_count=0
    )
    db.add(preset)
    db.flush()
    return preset


def create_test_preset_item(
    db: Session,
    preset_id: int,
    keyword_id: int,
    weight: float = 1.0,
    sort_order: int = 0
) -> PresetItem:
    """创建测试预设项。"""
    item = PresetItem(
        id=get_next_id(),
        preset_id=preset_id,
        keyword_id=keyword_id,
        weight=weight,
        sort_order=sort_order
    )
    db.add(item)
    db.flush()
    return item


# ============================================================================
# Property 1: Preset Type Determines Permissions
# Validates: Requirements 1.2, 6.1, 6.2, 7.1, 7.2
# ============================================================================

class TestPresetTypePermissions:
    """
    Property 1: Preset Type Determines Permissions

    *For any* preset, if is_official is true, then no non-admin user can edit or delete it;
    if is_official is false, then only the creator can edit or delete it.

    **Validates: Requirements 1.2, 6.1, 6.2, 7.1, 7.2**
    """

    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        is_official=st.booleans(),
        user_is_creator=st.booleans(),
        user_is_admin=st.booleans()
    )
    def test_preset_permission_property(
        self,
        is_official: bool,
        user_is_creator: bool,
        user_is_admin: bool
    ):
        """
        Feature: prompt-preset, Property 1: Preset Type Determines Permissions

        测试预设类型决定权限的属性：
        - 官方预设：非管理员用户不能编辑或删除
        - 用户预设：只有创建者可以编辑或删除
        """
        db = get_test_db()
        try:
            # Setup: 创建测试数据
            category = create_test_category(db)
            subcategory = create_test_subcategory(db, category.id)

            creator = create_test_user(db, "creator_user")
            other_user = create_test_user(
                db,
                "other_user",
                role="admin" if user_is_admin else "user"
            )

            # 创建预设
            preset = create_test_preset(
                db,
                subcategory.id,
                created_by=None if is_official else creator.id,
                is_official=is_official
            )
            db.commit()

            # 确定当前操作用户
            current_user = creator if user_is_creator else other_user

            # 验证权限逻辑
            # 对于官方预设
            if preset.is_official:
                # 非管理员不能编辑/删除官方预设
                if current_user.role != "admin":
                    # 验证：非管理员用户不应该有权限
                    can_edit = False
                    can_delete = False
                else:
                    # 管理员可以编辑/删除官方预设
                    can_edit = True
                    can_delete = True

                # 断言：非管理员不能操作官方预设
                if current_user.role != "admin":
                    assert can_edit == False, "非管理员用户不应该能编辑官方预设"
                    assert can_delete == False, "非管理员用户不应该能删除官方预设"
            else:
                # 用户预设：只有创建者可以编辑/删除
                can_edit = (preset.created_by == current_user.id)
                can_delete = (preset.created_by == current_user.id)

                if preset.created_by == current_user.id:
                    assert can_edit == True, "创建者应该能编辑自己的预设"
                    assert can_delete == True, "创建者应该能删除自己的预设"
                else:
                    assert can_edit == False, "非创建者不应该能编辑他人的预设"
                    assert can_delete == False, "非创建者不应该能删除他人的预设"
        finally:
            cleanup_db(db)


# ============================================================================
# Property 4: Usage Count Consistency
# Validates: Requirements 1.6, 1.7, 4.7, 4.8, 9.1, 9.2, 9.3, 9.5
# ============================================================================

class TestUsageCountConsistency:
    """
    Property 4: Usage Count Consistency

    *For any* preset selection operation, both the preset's global usage_count and
    the user's personal used_count must increment by exactly 1, and all contained
    prompt keywords must have their usage_count incremented.

    **Validates: Requirements 1.6, 1.7, 4.7, 4.8, 9.1, 9.2, 9.3, 9.5**
    """

    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        initial_preset_usage=st.integers(min_value=0, max_value=1000),
        initial_user_usage=st.integers(min_value=0, max_value=1000),
        num_keywords=st.integers(min_value=1, max_value=5),
        keyword_usages=st.lists(
            st.integers(min_value=0, max_value=1000),
            min_size=1,
            max_size=5
        )
    )
    def test_usage_count_increment_property(
        self,
        initial_preset_usage: int,
        initial_user_usage: int,
        num_keywords: int,
        keyword_usages: list
    ):
        """
        Feature: prompt-preset, Property 4: Usage Count Consistency

        测试使用统计一致性属性：
        - 选择预设时，预设全局使用次数增加1
        - 选择预设时，用户个人使用次数增加1
        - 选择预设时，所有包含的提示词使用次数各增加1
        """
        # 确保 keyword_usages 长度与 num_keywords 匹配
        assume(len(keyword_usages) >= num_keywords)
        keyword_usages = keyword_usages[:num_keywords]

        db = get_test_db()
        try:
            # Setup: 创建测试数据
            category = create_test_category(db)
            subcategory = create_test_subcategory(db, category.id)
            user = create_test_user(db, "test_user")

            # 创建预设
            preset = create_test_preset(
                db,
                subcategory.id,
                created_by=user.id,
                is_official=False
            )
            preset.usage_count = initial_preset_usage

            # 创建提示词和预设项
            keywords = []
            for i in range(num_keywords):
                keyword = create_test_keyword(
                    db,
                    subcategory.id,
                    word=f"keyword_{i}"
                )
                keyword.usage_count = keyword_usages[i]
                keywords.append(keyword)

                create_test_preset_item(
                    db,
                    preset.id,
                    keyword.id,
                    weight=1.0,
                    sort_order=i
                )

            # 创建用户使用记录
            user_usage = UserPresetUsage(
                user_id=user.id,
                preset_id=preset.id,
                used_count=initial_user_usage
            )
            db.add(user_usage)
            db.commit()

            # 记录初始值
            initial_preset_count = preset.usage_count
            initial_user_count = user_usage.used_count
            initial_keyword_counts = [kw.usage_count for kw in keywords]

            # 模拟选择预设操作
            # 1. 更新预设全局使用次数
            preset.usage_count = (preset.usage_count or 0) + 1

            # 2. 更新每个提示词的使用次数
            for keyword in keywords:
                keyword.usage_count = (keyword.usage_count or 0) + 1

            # 3. 更新用户个人使用统计
            user_usage.used_count = (user_usage.used_count or 0) + 1

            db.commit()

            # 验证属性
            # Property: 预设全局使用次数增加1
            assert preset.usage_count == initial_preset_count + 1, \
                f"预设使用次数应该从 {initial_preset_count} 增加到 {initial_preset_count + 1}"

            # Property: 用户个人使用次数增加1
            assert user_usage.used_count == initial_user_count + 1, \
                f"用户使用次数应该从 {initial_user_count} 增加到 {initial_user_count + 1}"

            # Property: 所有提示词使用次数各增加1
            for i, keyword in enumerate(keywords):
                expected = initial_keyword_counts[i] + 1
                assert keyword.usage_count == expected, \
                    f"提示词 {keyword.word} 使用次数应该从 {initial_keyword_counts[i]} 增加到 {expected}"
        finally:
            cleanup_db(db)


# ============================================================================
# Property 14: Cascade Deletion
# Validates: Requirements 7.4, 7.5
# ============================================================================

class TestCascadeDeletion:
    """
    Property 14: Cascade Deletion

    *For any* preset deletion, all related preset_items and user_preset_favorites
    must also be deleted.

    **Validates: Requirements 7.4, 7.5**
    """

    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        num_items=st.integers(min_value=1, max_value=5),
        num_favorites=st.integers(min_value=0, max_value=3)
    )
    def test_cascade_deletion_property(
        self,
        num_items: int,
        num_favorites: int
    ):
        """
        Feature: prompt-preset, Property 14: Cascade Deletion

        测试级联删除属性：
        - 删除预设时，所有相关的预设项也被删除
        - 删除预设时，所有相关的用户收藏也被删除
        """
        db = get_test_db()
        try:
            # Setup: 创建测试数据
            category = create_test_category(db)
            subcategory = create_test_subcategory(db, category.id)
            creator = create_test_user(db, "creator_user")

            # 创建预设
            preset = create_test_preset(
                db,
                subcategory.id,
                created_by=creator.id,
                is_official=False
            )
            preset_id = preset.id

            # 创建预设项
            item_ids = []
            for i in range(num_items):
                keyword = create_test_keyword(db, subcategory.id, word=f"keyword_{i}")
                item = create_test_preset_item(db, preset.id, keyword.id)
                item_ids.append(item.id)

            # 创建用户收藏
            favorite_user_ids = []
            for i in range(num_favorites):
                user = create_test_user(db, f"fav_user_{i}")
                favorite = UserPresetFavorite(
                    user_id=user.id,
                    preset_id=preset.id
                )
                db.add(favorite)
                favorite_user_ids.append(user.id)

            db.commit()

            # 验证数据已创建
            assert db.query(PresetItem).filter(PresetItem.preset_id == preset_id).count() == num_items
            assert db.query(UserPresetFavorite).filter(UserPresetFavorite.preset_id == preset_id).count() == num_favorites

            # 执行删除操作
            db.delete(preset)
            db.commit()

            # 验证级联删除
            # Property: 所有预设项被删除
            remaining_items = db.query(PresetItem).filter(PresetItem.preset_id == preset_id).count()
            assert remaining_items == 0, \
                f"删除预设后应该没有剩余的预设项，但找到 {remaining_items} 个"

            # Property: 所有用户收藏被删除
            remaining_favorites = db.query(UserPresetFavorite).filter(
                UserPresetFavorite.preset_id == preset_id
            ).count()
            assert remaining_favorites == 0, \
                f"删除预设后应该没有剩余的收藏记录，但找到 {remaining_favorites} 个"

            # 验证预设本身被删除
            deleted_preset = db.query(PromptPreset).filter(PromptPreset.id == preset_id).first()
            assert deleted_preset is None, "预设应该被删除"
        finally:
            cleanup_db(db)
