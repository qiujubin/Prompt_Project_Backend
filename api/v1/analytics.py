"""数据分析接口（示例）。

提供两类图表数据，兼容前端契约。"""
from fastapi import APIRouter
from schemas.analytics import ChartData

router = APIRouter(prefix="/userCenter")

@router.get("/getPositiveMaxData")
def get_positive_max_data():
    """正向提示词分析数据。"""
    data = ChartData(categories=["A", "B", "C"], values=[10.0, 20.0, 15.0])
    return {"code": 200, "msg": "OK", "data": data.dict()}

@router.get("/getNegativeMaxData")
def get_negative_max_data():
    """反向提示词分析数据。"""
    data = ChartData(categories=["X", "Y", "Z"], values=[5.0, 8.0, 3.0])
    return {"code": 200, "msg": "OK", "data": data.dict()}
