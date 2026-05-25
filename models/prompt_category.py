from sqlalchemy import Column, BigInteger, Integer, String
from sqlalchemy.sql import text
from database import Base

class PromptCategory(Base):
    """提示词大类模型。

    对应表：`prompt_categories`
    例如：食物、饮料、风格等顶层分类。
    """
    __tablename__ = "prompt_categories"
    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    display_name = Column(String(256), nullable=False)
    icon = Column(String(64), nullable=True, default="Box")
    sort_order = Column(Integer, nullable=True, server_default=text("0"))
    is_hidden = Column(Integer, nullable=True, server_default=text("0"))

