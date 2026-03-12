# 提示词数据导入指南

## 概述

此脚本用于从 `prompt.xlsx` Excel 文件导入提示词数据到数据库中。

## 数据映射规则

Excel 文件中的数据将按以下规则导入：

1. **大类 (prompt_categories)**
   - `categories` 列 → `name` 字段
   - 第一个 `display_name` 列 → `display_name` 字段

2. **小类 (prompt_subcategories)**
   - `subcategories` 列 → `name` 字段
   - 第二个 `display_name` 列 → `display_name` 字段
   - `category_id` 自动关联到对应的大类 ID

3. **关键词 (prompt_keywords)**
   - `prompt` 列 → `word` 字段
   - 第三个 `display_name` 列 → `display_name` 字段
   - `small_category_id` 自动关联到对应的小类 ID

## 使用步骤

### 1. 准备 Excel 文件

确保 `prompt.xlsx` 文件位于项目根目录下，文件应包含以下列：
- `categories`: 大类名称（英文）
- `subcategories`: 小类名称（英文）
- `prompt`: 提示词（英文）
- `display_name` 相关列: 中文显示名称（可能有多列）

### 2. 安装依赖

```bash
# 进入 Backend 目录
cd Backend

# 安装新增的依赖
pip install pandas openpyxl

# 或者重新安装所有依赖
pip install -r requirements.txt
```

### 3. 运行导入脚本

```bash
# 从项目根目录运行
python Backend/scripts/import_prompt_data.py

# 或者从 Backend 目录运行
cd Backend
python scripts/import_prompt_data.py
```

### 4. 确认导入

脚本会：
1. 显示 Excel 文件的前 5 行数据预览
2. 询问是否继续导入
3. 开始导入数据，显示进度
4. 完成后显示统计信息

## 功能特性

- ✅ **自动去重**: 检查数据库中是否已存在相同数据，避免重复导入
- ✅ **关系维护**: 自动建立大类、小类、关键词之间的关联关系
- ✅ **批量提交**: 每 50 行提交一次，提高性能
- ✅ **错误处理**: 单行错误不影响整体导入，会显示错误信息
- ✅ **统计报告**: 导入完成后显示详细的统计信息

## 输出示例

```
正在读取 Excel 文件: E:\WorkSpace\Project_Graduation\prompt.xlsx
成功读取 150 行数据
列名: ['categories', 'subcategories', 'prompt', 'display_name_1', 'display_name_2', 'display_name_3']

前 5 行数据预览:
  categories subcategories        prompt display_name_1 display_name_2 display_name_3
0   character        modern  young woman           人物           现代           年轻女性
1   character        modern    old man             人物           现代           老年男性
...

是否继续导入数据？(y/n): y

开始导入数据...
  创建大类: character (人物)
    创建小类: modern (现代)
      创建关键词: young woman (年轻女性)
      创建关键词: old man (老年男性)
...

已处理 50 行，提交到数据库...
已处理 100 行，提交到数据库...
已处理 150 行，提交到数据库...

============================================================
导入完成！统计信息：
  大类: 创建 5 个, 跳过 0 个
  小类: 创建 15 个, 跳过 0 个
  关键词: 创建 130 个, 跳过 0 个
============================================================
```

## 注意事项

1. **数据库连接**: 确保 `.env` 文件中的数据库配置正确
2. **Excel 格式**: 确保 Excel 文件格式正确，列名匹配
3. **重复运行**: 脚本支持重复运行，已存在的数据会被跳过
4. **备份数据**: 首次运行前建议备份数据库

## 故障排除

### 问题：找不到 Excel 文件
**解决方案**: 确保 `prompt.xlsx` 在项目根目录下

### 问题：列名不匹配
**解决方案**: 检查 Excel 文件的列名，必要时修改脚本中的列名映射

### 问题：数据库连接失败
**解决方案**: 检查 `.env` 文件中的 `DB_URL` 配置

### 问题：导入数据不正确
**解决方案**:
1. 检查 Excel 文件的数据格式
2. 查看脚本输出的错误信息
3. 检查数据库中的数据是否正确

## 扩展功能

如果需要修改导入逻辑，可以编辑 `import_prompt_data.py` 文件：

- 修改列名映射
- 调整数据验证规则
- 添加额外的数据处理逻辑
- 修改批量提交的行数

## 相关文件

- `Backend/models/prompt_category.py`: 大类模型
- `Backend/models/prompt_subcategory.py`: 小类模型
- `Backend/models/prompt_keyword.py`: 关键词模型
- `Backend/scripts/import_prompt_data.py`: 导入脚本
