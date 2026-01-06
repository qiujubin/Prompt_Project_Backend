"""基础数据模型测试。

测试新增的内容发现优化相关数据模型的基本功能。
"""
import pytest
from sqlalchemy.orm import Session
from models.tag import Tag
from models.search_log import SearchLog

def test_tag_model_basic(db_session: Session):
    """测试标签模型基本功能。"""
    # 创建标签
    tag = Tag(
        name="风景画",
        category="theme",
        usage_count=10
    )
    db_session.add(tag)
    db_session.commit()

    # 验证标签创建成功
    assert tag.id is not None
    assert tag.name == "风景画"
    assert tag.category == "theme"
    assert tag.usage_count == 10
    assert tag.created_at is not None
    assert tag.updated_at is not None

def test_search_log_model_basic(db_session: Session):
    """测试搜索日志模型基本功能。"""
    # 创建搜索日志（不关联用户）
    search_log = SearchLog(
        query="风景画",
        filters={"category": "theme"},
        result_count=15,
        clicked_results=[1, 2, 3],
        session_id="test_session_123"
    )
    db_session.add(search_log)
    db_session.commit()

    # 验证搜索日志创建成功
    assert search_log.id is not None
    assert search_log.query == "风景画"
    assert search_log.filters == {"category": "theme"}
    assert search_log.result_count == 15
    assert search_log.clicked_results == [1, 2, 3]
    assert search_log.session_id == "test_session_123"
    assert search_log.created_at is not None

def test_tag_unique_constraint(db_session: Session):
    """测试标签名称唯一约束。"""
    # 创建第一个标签
    tag1 = Tag(name="测试标签", category="theme")
    db_session.add(tag1)
    db_session.commit()

    # 尝试创建同名标签，应该失败
    tag2 = Tag(name="测试标签", category="style")
    db_session.add(tag2)

    with pytest.raises(Exception):  # 应该抛出唯一约束异常
        db_session.commit()
