"""内容发现API测试。

测试内容发现优化功能的API端点。
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

def test_get_tags_endpoint(client: TestClient):
    """测试获取标签端点。"""
    response = client.get("/api/v1/content-discovery/tags")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data

def test_get_tag_suggestions_endpoint(client: TestClient):
    """测试获取标签建议端点。"""
    response = client.get("/api/v1/content-discovery/tags/suggestions?query=风景")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data

def test_search_content_endpoint(client: TestClient):
    """测试搜索内容端点。"""
    response = client.get("/api/v1/content-discovery/search?query=风景画")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data

def test_get_search_suggestions_endpoint(client: TestClient):
    """测试获取搜索建议端点。"""
    response = client.get("/api/v1/content-discovery/search/suggestions?query=风景")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data

def test_get_categories_endpoint(client: TestClient):
    """测试获取分类端点。"""
    response = client.get("/api/v1/content-discovery/categories")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data

def test_get_trending_content_endpoint(client: TestClient):
    """测试获取热门趋势内容端点。"""
    response = client.get("/api/v1/content-discovery/trending")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data

def test_get_trending_tags_endpoint(client: TestClient):
    """测试获取热门标签端点。"""
    response = client.get("/api/v1/content-discovery/trending/tags")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
