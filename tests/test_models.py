"""数据模型测试。

测试新增的内容发现优化相关数据模型。
"""
import pytest
from sqlalchemy.orm import Session
from models.tag import Tag, ContentTag
from models.user_preference import UserPreference, UserInteraction
from models.search_log import SearchLog, ContentFeature
from models.user import User
from models.drawing import Drawing

def test_tag_model_creation(db_session: Session):
    """测试标签模型创建。"""
    tag = Tag(
        name="风景画",
        category="theme",
        usage_count=10
    )
    db_session.add(tag)
    db_session.commit()

    assert tag.id is not None
    assert tag.name == "风景画"
    assert tag.category == "theme"
    assert tag.usage_count == 10

def test_user_preference_model_creation(db_session: Session):
    """测试用户偏好模型创建。"""
    # 先创建用户
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_password"
    )
    db_session.add(user)
    db_session.commit()

    # 创建用户偏好
    preference = UserPreference(
        user_id=user.id,
        preference_type="tag",
        preference_value="风景画",
        weight=1.5
    )
    db_session.add(preference)
    db_session.commit()

    assert preference.id is not None
    assert preference.user_id == user.id
    assert preference.preference_type == "tag"
    assert preference.weight == 1.5

def test_search_log_model_creation(db_session: Session):
    """测试搜索日志模型创建。"""
    # 先创建用户
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_password"
    )
    db_session.add(user)
    db_session.commit()

    # 创建搜索日志
    search_log = SearchLog(
        user_id=user.id,
        query="风景画",
        filters={"category": "theme"},
        result_count=15,
        clicked_results=[1, 2, 3]
    )
    db_session.add(search_log)
    db_session.commit()

    assert search_log.id is not None
    assert search_log.user_id == user.id
    assert search_log.query == "风景画"
    assert search_log.result_count == 15

def test_content_feature_model_creation(db_session: Session):
    """测试内容特征模型创建。"""
    # 先创建用户和作品
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_password"
    )
    db_session.add(user)
    db_session.commit()

    drawing = Drawing(
        user_id=user.id,
        prompt="beautiful landscape",
        model_name="test_model"
    )
    db_session.add(drawing)
    db_session.commit()

    # 创建内容特征
    feature = ContentFeature(
        content_id=drawing.id,
        feature_vector=[0.1, 0.2, 0.3],
        dominant_colors=["#FF0000", "#00FF00"],
        style_scores={"realistic": 0.8, "cartoon": 0.2},
        complexity_score=0.75
    )
    db_session.add(feature)
    db_session.commit()

    assert feature.content_id == drawing.id
    assert feature.complexity_score == 0.75

def test_model_relationships(db_session: Session):
    """测试模型关系。"""
    # 创建用户
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_password"
    )
    db_session.add(user)
    db_session.commit()

    # 创建作品
    drawing = Drawing(
        user_id=user.id,
        prompt="test prompt",
        model_name="test_model"
    )
    db_session.add(drawing)
    db_session.commit()

    # 创建标签
    tag = Tag(name="测试标签", category="theme")
    db_session.add(tag)
    db_session.commit()

    # 创建内容标签关联
    content_tag = ContentTag(
        content_id=drawing.id,
        tag_id=tag.id,
        confidence=0.9,
        source="auto"
    )
    db_session.add(content_tag)
    db_session.commit()

    # 测试关系
    assert len(tag.content_tags) == 1
    assert tag.content_tags[0].content_id == drawing.id
