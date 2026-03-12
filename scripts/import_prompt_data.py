"""
导入提示词数据脚本

从 prompt.xlsx 文件读取数据并导入到数据库中：
- categories 和第一个 display_name -> prompt_categories 表
- subcategories 和第二个 display_name -> prompt_subcategories 表
- prompt 和第三个 display_name -> prompt_keywords 表

使用方法:
    python Backend/scripts/import_prompt_data.py
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
backend_path = project_root / "Backend"
sys.path.insert(0, str(backend_path))

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from Backend.core.config import settings
from Backend.models.prompt_category import PromptCategory
from Backend.models.prompt_subcategory import PromptSubcategory
from Backend.models.prompt_keyword import PromptKeyword


def read_excel_data(excel_path: str):
    """读取 Excel 文件数据"""
    print(f"正在读取 Excel 文件: {excel_path}")

    # 读取 Excel 文件
    df = pd.read_excel(excel_path)

    print(f"成功读取 {len(df)} 行数据")
    print(f"列名: {df.columns.tolist()}")

    return df


def import_data(df, db_session):
    """导入数据到数据库"""

    # 用于存储已创建的分类和子分类的映射
    category_map = {}  # {category_name: category_id}
    subcategory_map = {}  # {(category_name, subcategory_name): subcategory_id}

    # 统计信息
    stats = {
        'categories_created': 0,
        'subcategories_created': 0,
        'keywords_created': 0,
        'categories_skipped': 0,
        'subcategories_skipped': 0,
        'keywords_skipped': 0
    }

    print("\n开始导入数据...")

    for index, row in df.iterrows():
        try:
            # 获取数据（假设列名为 categories, subcategories, prompt, display_name）
            # 根据实际 Excel 列名调整
            category_name = str(row.get('categories', '')).strip()
            subcategory_name = str(row.get('subcategories', '')).strip()
            prompt_word = str(row.get('prompt', '')).strip()

            # 获取 display_name 列（可能有多个）
            # 假设有三个 display_name 列或者一个包含多个值的列
            display_names = []
            for col in df.columns:
                if 'display_name' in col.lower():
                    val = str(row.get(col, '')).strip()
                    if val and val != 'nan':
                        display_names.append(val)

            # 如果没有找到 display_name 列，尝试其他可能的列名
            if not display_names:
                # 尝试查找中文显示名称的列
                for col in df.columns:
                    if '显示' in col or '名称' in col or 'name' in col.lower():
                        val = str(row.get(col, '')).strip()
                        if val and val != 'nan' and val != category_name and val != subcategory_name and val != prompt_word:
                            display_names.append(val)

            # 分配 display_name
            category_display = display_names[0] if len(display_names) > 0 else category_name
            subcategory_display = display_names[1] if len(display_names) > 1 else subcategory_name
            keyword_display = display_names[2] if len(display_names) > 2 else prompt_word

            # 跳过空行
            if not category_name or category_name == 'nan':
                continue

            # 1. 处理大类 (prompt_categories)
            if category_name not in category_map:
                # 检查数据库中是否已存在
                existing_category = db_session.query(PromptCategory).filter(
                    PromptCategory.name == category_name
                ).first()

                if existing_category:
                    category_map[category_name] = existing_category.id
                    stats['categories_skipped'] += 1
                else:
                    # 创建新的大类
                    new_category = PromptCategory(
                        name=category_name,
                        display_name=category_display,
                        sort_order=len(category_map)
                    )
                    db_session.add(new_category)
                    db_session.flush()  # 获取 ID
                    category_map[category_name] = new_category.id
                    stats['categories_created'] += 1
                    print(f"  创建大类: {category_name} ({category_display})")

            category_id = category_map[category_name]

            # 2. 处理小类 (prompt_subcategories)
            if subcategory_name and subcategory_name != 'nan':
                subcategory_key = (category_name, subcategory_name)

                if subcategory_key not in subcategory_map:
                    # 检查数据库中是否已存在
                    existing_subcategory = db_session.query(PromptSubcategory).filter(
                        PromptSubcategory.category_id == category_id,
                        PromptSubcategory.name == subcategory_name
                    ).first()

                    if existing_subcategory:
                        subcategory_map[subcategory_key] = existing_subcategory.id
                        stats['subcategories_skipped'] += 1
                    else:
                        # 创建新的小类
                        new_subcategory = PromptSubcategory(
                            category_id=category_id,
                            name=subcategory_name,
                            display_name=subcategory_display,
                            sort_order=len([k for k in subcategory_map.keys() if k[0] == category_name])
                        )
                        db_session.add(new_subcategory)
                        db_session.flush()  # 获取 ID
                        subcategory_map[subcategory_key] = new_subcategory.id
                        stats['subcategories_created'] += 1
                        print(f"    创建小类: {subcategory_name} ({subcategory_display})")

                subcategory_id = subcategory_map[subcategory_key]
            else:
                subcategory_id = None

            # 3. 处理关键词 (prompt_keywords)
            if prompt_word and prompt_word != 'nan':
                # 检查数据库中是否已存在
                existing_keyword = db_session.query(PromptKeyword).filter(
                    PromptKeyword.word == prompt_word,
                    PromptKeyword.small_category_id == subcategory_id
                ).first()

                if existing_keyword:
                    stats['keywords_skipped'] += 1
                else:
                    # 创建新的关键词
                    new_keyword = PromptKeyword(
                        word=prompt_word,
                        display_name=keyword_display,
                        small_category_id=subcategory_id
                    )
                    db_session.add(new_keyword)
                    stats['keywords_created'] += 1
                    print(f"      创建关键词: {prompt_word} ({keyword_display})")

            # 每 50 行提交一次
            if (index + 1) % 50 == 0:
                db_session.commit()
                print(f"\n已处理 {index + 1} 行，提交到数据库...")

        except Exception as e:
            print(f"处理第 {index + 1} 行时出错: {e}")
            print(f"行数据: {row.to_dict()}")
            db_session.rollback()
            continue

    # 最终提交
    db_session.commit()

    print("\n" + "="*60)
    print("导入完成！统计信息：")
    print(f"  大类: 创建 {stats['categories_created']} 个, 跳过 {stats['categories_skipped']} 个")
    print(f"  小类: 创建 {stats['subcategories_created']} 个, 跳过 {stats['subcategories_skipped']} 个")
    print(f"  关键词: 创建 {stats['keywords_created']} 个, 跳过 {stats['keywords_skipped']} 个")
    print("="*60)


def main():
    """主函数"""
    # Excel 文件路径
    excel_path = project_root / "prompt.xlsx"

    if not excel_path.exists():
        print(f"错误: 找不到 Excel 文件: {excel_path}")
        print("请确保 prompt.xlsx 文件在项目根目录下")
        return

    # 读取 Excel 数据
    df = read_excel_data(str(excel_path))

    # 显示前几行数据供确认
    print("\n前 5 行数据预览:")
    print(df.head())
    print("\n")

    # 确认是否继续
    response = input("是否继续导入数据？(y/n): ")
    if response.lower() != 'y':
        print("取消导入")
        return

    # 创建数据库连接
    engine = create_engine(settings.DB_URL)
    SessionLocal = sessionmaker(bind=engine)
    db_session = SessionLocal()

    try:
        # 导入数据
        import_data(df, db_session)
    except Exception as e:
        print(f"\n导入过程中发生错误: {e}")
        db_session.rollback()
    finally:
        db_session.close()


if __name__ == "__main__":
    main()
