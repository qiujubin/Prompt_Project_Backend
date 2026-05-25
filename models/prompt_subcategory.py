from sqlalchemy import Column, BigInteger, Integer, String, ForeignKey
from sqlalchemy.sql import text
from database import Base

class PromptSubcategory(Base):
    """提示词小类模型。

    对应表：`prompt_subcategories`
    归属某个大类，用于细分提示词分类。
    """
    __tablename__ = "prompt_subcategories"
    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    category_id = Column(BigInteger, ForeignKey("prompt_categories.id"), nullable=False)
    name = Column(String(128), nullable=False)
    display_name = Column(String(256), nullable=False)
    sort_order = Column(Integer, nullable=True, server_default=text("0"))
    is_hidden = Column(Integer, nullable=True, server_default=text("0"))

