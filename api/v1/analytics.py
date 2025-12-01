"""数据分析接口。

提供基于真实数据的图表统计，包括提示词排名、绘图趋势等。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Dict, Any
import datetime

from database import get_db
from schemas.analytics import ChartData
from models.prompt_log import PromptLog
from models.prompt_keyword import PromptKeyword
from models.drawing import Drawing
from models.user import User
from models.prompt_subcategory import PromptSubcategory

router = APIRouter(prefix="/userCenter")

@router.get("/getUserGrowth")
def get_user_growth(days: int = 7, db: Session = Depends(get_db)):
    """
    获取最近 N 天的用户增长趋势（每日注册量）。
    """
    today = datetime.date.today()
    date_list = [today - datetime.timedelta(days=x) for x in range(days)]
    date_list.reverse()
    
    categories = [d.strftime("%m-%d") for d in date_list]
    
    start_date = date_list[0]
    results = db.query(
        func.date(User.created_at).label('date'),
        func.count(User.id).label('count')
    ).filter(
        User.created_at >= start_date
    ).group_by(
        func.date(User.created_at)
    ).all()
    
    data_map = {str(r[0]): r[1] for r in results}
    values = []
    
    for d in date_list:
        key = str(d)
        values.append(float(data_map.get(key, 0)))
        
    data = ChartData(categories=categories, values=values)
    return {"code": 200, "msg": "OK", "data": data.dict()}

@router.get("/getActiveUsers")
def get_active_users(db: Session = Depends(get_db)):
    """
    获取活跃用户排行 (Top 10 绘图数量)。
    """
    results = db.query(
        Drawing.user_id,
        func.count(Drawing.id).label('count')
    ).group_by(
        Drawing.user_id
    ).order_by(
        desc('count')
    ).limit(10).all()
    
    if not results:
        return {"code": 200, "msg": "暂无数据", "data": {"categories": [], "values": []}}
        
    user_ids = [r[0] for r in results]
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    user_map = {u.id: u.username for u in users}
    
    categories = []
    values = []
    
    for uid, count in results:
        username = user_map.get(uid, f"User {uid}")
        categories.append(username)
        values.append(float(count))
        
    data = ChartData(categories=categories, values=values)
    return {"code": 200, "msg": "OK", "data": data.dict()}

@router.get("/getSubcategoryUsage")
def get_subcategory_usage(db: Session = Depends(get_db)):
    """
    获取热门提示词分类 (Top 10)。
    基于 prompt_logs 中的 small_category_id 统计。
    """
    results = db.query(
        PromptLog.small_category_id,
        func.count(PromptLog.id).label('count')
    ).group_by(
        PromptLog.small_category_id
    ).order_by(
        desc('count')
    ).limit(10).all()
    
    if not results:
        return {"code": 200, "msg": "暂无数据", "data": {"categories": [], "values": []}}
        
    cat_ids = [r[0] for r in results]
    subcats = db.query(PromptSubcategory).filter(PromptSubcategory.id.in_(cat_ids)).all()
    cat_map = {c.id: c.display_name for c in subcats}
    
    categories = []
    values = []
    
    for cid, count in results:
        name = cat_map.get(cid, f"Cat {cid}")
        categories.append(name)
        values.append(float(count))
        
    data = ChartData(categories=categories, values=values)
    return {"code": 200, "msg": "OK", "data": data.dict()}

@router.get("/getPositiveMaxData")
def get_positive_max_data(db: Session = Depends(get_db)):
    """
    正向提示词分析数据 (Top 10)。
    统计 prompt_logs 中 is_negative=False 的记录，按 prompt_id 分组计数。
    """
    # 聚合查询：统计每个 prompt_id 的出现次数
    results = db.query(
        PromptLog.prompt_id,
        func.count(PromptLog.prompt_id).label('count')
    ).filter(
        (PromptLog.is_negative == False) | (PromptLog.is_negative == None)
    ).group_by(
        PromptLog.prompt_id
    ).order_by(
        desc('count')
    ).limit(10).all()

    if not results:
        return {"code": 200, "msg": "暂无数据", "data": {"categories": [], "values": []}}

    # 获取对应的提示词文本
    prompt_ids = [r[0] for r in results]
    keywords = db.query(PromptKeyword).filter(PromptKeyword.id.in_(prompt_ids)).all()
    keyword_map = {k.id: k.word for k in keywords}

    categories = []
    values = []
    
    for pid, count in results:
        word = keyword_map.get(pid, f"Unknown({pid})")
        # 截断过长的提示词以便展示
        display_name = (word[:15] + '...') if len(word) > 15 else word
        categories.append(display_name)
        values.append(float(count))

    data = ChartData(categories=categories, values=values)
    return {"code": 200, "msg": "OK", "data": data.dict()}

@router.get("/getNegativeMaxData")
def get_negative_max_data(db: Session = Depends(get_db)):
    """
    反向提示词分析数据 (Top 10)。
    统计 prompt_logs 中 is_negative=True 的记录。
    """
    results = db.query(
        PromptLog.prompt_id,
        func.count(PromptLog.prompt_id).label('count')
    ).filter(
        PromptLog.is_negative == True
    ).group_by(
        PromptLog.prompt_id
    ).order_by(
        desc('count')
    ).limit(10).all()

    if not results:
        return {"code": 200, "msg": "暂无数据", "data": {"categories": [], "values": []}}

    prompt_ids = [r[0] for r in results]
    keywords = db.query(PromptKeyword).filter(PromptKeyword.id.in_(prompt_ids)).all()
    keyword_map = {k.id: k.word for k in keywords}

    categories = []
    values = []
    
    for pid, count in results:
        word = keyword_map.get(pid, f"Unknown({pid})")
        display_name = (word[:15] + '...') if len(word) > 15 else word
        categories.append(display_name)
        values.append(float(count))

    data = ChartData(categories=categories, values=values)
    return {"code": 200, "msg": "OK", "data": data.dict()}

@router.get("/getDailyDrawings")
def get_daily_drawings(days: int = 7, db: Session = Depends(get_db)):
    """
    获取最近 N 天的每日绘图数量趋势。
    """
    # 生成最近 N 天的日期列表
    today = datetime.date.today()
    date_list = [today - datetime.timedelta(days=x) for x in range(days)]
    date_list.reverse()  # 从旧到新
    
    categories = [d.strftime("%m-%d") for d in date_list]
    
    # 数据库查询：按日期分组统计
    # 注意：这里假设 created_at 是带时区的，func.date截取日期部分
    start_date = date_list[0]
    results = db.query(
        func.date(Drawing.created_at).label('date'),
        func.count(Drawing.id).label('count')
    ).filter(
        Drawing.created_at >= start_date
    ).group_by(
        func.date(Drawing.created_at)
    ).all()
    
    # 将查询结果映射到日期列表，补零
    data_map = {str(r[0]): r[1] for r in results}
    values = []
    
    for d in date_list:
        key = str(d)
        values.append(float(data_map.get(key, 0)))
        
    data = ChartData(categories=categories, values=values)
    return {"code": 200, "msg": "OK", "data": data.dict()}

@router.get("/getModelUsage")
def get_model_usage(db: Session = Depends(get_db)):
    """
    获取模型使用分布情况。
    """
    results = db.query(
        Drawing.model_name,
        func.count(Drawing.id).label('count')
    ).group_by(
        Drawing.model_name
    ).order_by(
        desc('count')
    ).limit(10).all()
    
    categories = []
    values = []
    
    for name, count in results:
        categories.append(name)
        values.append(float(count))
        
    data = ChartData(categories=categories, values=values)
    return {"code": 200, "msg": "OK", "data": data.dict()}
