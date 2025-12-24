"""数据分析接口。

提供基于真实数据的图表统计，包括提示词排名、绘图趋势等。
"""
from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, extract
from typing import List, Dict, Any
import datetime

from database import get_db
from schemas.analytics import ChartData
from models.prompt_log import PromptLog
from models.prompt_keyword import PromptKeyword
from models.drawing import Drawing
from models.user import User
from models.prompt_subcategory import PromptSubcategory
from models.copy_log import CopyLog
from models.weight_log import WeightLog
from api.v1.users import get_current_user

router = APIRouter(prefix="/userCenter")

@router.post("/log_weight_adjustment")
def log_weight_adjustment(
    data: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    记录权重调整日志
    """
    keyword_id = data.get("keyword_id")
    old_weight = data.get("old_weight")
    new_weight = data.get("new_weight")
    
    # 简单的验证
    if new_weight is None:
        return {"code": 400, "msg": "Missing new_weight"}

    log = WeightLog(
        user_id=current_user.id,
        keyword_id=keyword_id,
        old_weight=old_weight,
        new_weight=new_weight
    )
    db.add(log)
    db.commit()
    return {"code": 200, "msg": "OK"}

@router.post("/increment_copy_stats")
def increment_copy_stats(
    data: Dict[str, Any] = Body(...), 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """
    增加复制统计 (记录流水)
    """
    stats_type = data.get("type")
    count = data.get("count", 0)
    
    if stats_type in ["positive", "negative"] and count > 0:
        new_log = CopyLog(
            user_id=current_user.id,
            copy_type=stats_type,
            item_count=count
        )
        db.add(new_log)
        db.commit()
        
    return {"code": 200, "msg": "OK"}

@router.get("/getUserStats")
def get_user_stats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    获取用户个人统计数据：
    1. 复制正面提示词次数 (positive_count) - 从 CopyLog 聚合
    2. 复制负面提示词次数 (negative_count) - 从 CopyLog 聚合
    3. 已选提示词总数 (total_selected)
    4. 权重调整次数 (weight_adjusted)
    """
    # Base query for this user
    base_query = db.query(PromptLog).filter(PromptLog.user_id == current_user.id)
    
    total_selected = base_query.count()
    
    # Aggregate from CopyLog
    positive_count = db.query(func.sum(CopyLog.item_count)).filter(
        CopyLog.user_id == current_user.id,
        CopyLog.copy_type == 'positive'
    ).scalar() or 0
    
    negative_count = db.query(func.sum(CopyLog.item_count)).filter(
        CopyLog.user_id == current_user.id,
        CopyLog.copy_type == 'negative'
    ).scalar() or 0
    
    # Weight adjustment count from WeightLog
    weight_adjusted = db.query(WeightLog).filter(WeightLog.user_id == current_user.id).count()
    
    return {
        "code": 200, 
        "msg": "OK", 
        "data": {
            "positive_count": positive_count,
            "negative_count": negative_count,
            "total_selected": total_selected,
            "weight_adjusted": weight_adjusted
        }
    }

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

@router.get("/getMyModelUsage")
def get_my_model_usage(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    用户个人常用模型分布
    """
    results = db.query(
        Drawing.model_name,
        func.count(Drawing.id).label('count')
    ).filter(
        Drawing.user_id == current_user.id
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

@router.get("/getMyDrawingTimeDistribution")
def get_my_drawing_time_distribution(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    用户绘图时段分布 (0-23点)
    """
    results = db.query(
        extract('hour', Drawing.created_at).label('hour'),
        func.count(Drawing.id).label('count')
    ).filter(
        Drawing.user_id == current_user.id
    ).group_by(
        extract('hour', Drawing.created_at)
    ).all()
    
    # Initialize 0-23 hours with 0
    hour_map = {i: 0 for i in range(24)}
    
    for h, count in results:
        if h is not None:
            hour_map[int(h)] = float(count)
        
    categories = [f"{i:02d}:00" for i in range(24)]
    values = [hour_map[i] for i in range(24)]
    
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

@router.get("/getMyPositiveMaxData")
def get_my_positive_max_data(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    用户个人常用正向提示词 Top 10
    """
    results = db.query(
        PromptLog.prompt_id,
        func.count(PromptLog.prompt_id).label('count')
    ).filter(
        (PromptLog.is_negative == False) | (PromptLog.is_negative == None),
        PromptLog.user_id == current_user.id
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

@router.get("/getMyNegativeMaxData")
def get_my_negative_max_data(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    用户个人常用反向提示词 Top 10
    """
    results = db.query(
        PromptLog.prompt_id,
        func.count(PromptLog.prompt_id).label('count')
    ).filter(
        PromptLog.is_negative == True,
        PromptLog.user_id == current_user.id
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

@router.get("/getMySubcategoryUsage")
def get_my_subcategory_usage(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    用户个人常用提示词分类 Top 10
    """
    results = db.query(
        PromptLog.small_category_id,
        func.count(PromptLog.id).label('count')
    ).filter(
        PromptLog.user_id == current_user.id
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

@router.get("/getMyDailyDrawings")
def get_my_daily_drawings(days: int = 7, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    获取用户个人最近 N 天的每日绘图数量趋势。
    """
    today = datetime.date.today()
    date_list = [today - datetime.timedelta(days=x) for x in range(days)]
    date_list.reverse()
    
    categories = [d.strftime("%m-%d") for d in date_list]
    
    start_date = date_list[0]
    results = db.query(
        func.date(Drawing.created_at).label('date'),
        func.count(Drawing.id).label('count')
    ).filter(
        Drawing.created_at >= start_date,
        Drawing.user_id == current_user.id
    ).group_by(
        func.date(Drawing.created_at)
    ).all()
    
    data_map = {str(r[0]): r[1] for r in results}
    values = []
    
    for d in date_list:
        key = str(d)
        values.append(float(data_map.get(key, 0)))
        
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
