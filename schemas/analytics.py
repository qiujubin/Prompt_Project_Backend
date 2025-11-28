from pydantic import BaseModel
from typing import List

class ChartData(BaseModel):
    categories: List[str]
    values: List[float]