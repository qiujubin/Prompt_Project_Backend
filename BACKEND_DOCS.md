# AI 绘图平台 - 后端工程文档

## 项目概述
本项目是 AI 绘图平台的**后端部分**，基于 FastAPI 构建，提供高性能的 RESTful API 服务。系统负责处理用户认证、积分交易、AI 任务调度（ComfyUI 对接）以及数据持久化。

## 技术栈
*   **Web 框架**: FastAPI (Python 3.10+)
*   **ORM**: SQLAlchemy (Async/Sync 混合)
*   **数据库**: PostgreSQL
*   **数据验证**: Pydantic v2
*   **AI 服务**: ComfyUI (通过 WebSocket/HTTP 交互)

## 核心功能与架构

### 1. 异步 AI 任务调度
*   **架构**: 采用“提交-轮询”模式解耦 HTTP 请求与耗时 AI 生成。
*   **流程**:
    1.  接收前端请求 -> 校验积分 -> 扣费。
    2.  向 ComfyUI 提交工作流 -> 获取 `prompt_id`。
    3.  立即在数据库创建 `queued` 状态的记录（关联 `prompt_id`）。
    4.  提供 `/status` 接口供前端查询，任务完成后自动回填图片 URL 并更新状态为 `finish`。

### 2. 积分与经济系统
*   **事务安全**: 积分扣除与日志记录在同一数据库事务中完成。
*   **智能退款**: 在 `api/v1/generation.py` 中实现了自动退款机制。若 AI 服务调用失败，系统会自动回滚已扣除的积分，防止用户损失。

### 3. 数据库设计
主要模型 (`models/`)：
*   `User`: 用户账户、积分余额、角色。
*   `Drawing`: 绘图记录，包含 `prompt`, `image_url`, `status`, `prompt_id` 等。
*   `CreditLog`: 积分变动流水，用于审计与对账。
*   `PromptKeyword` / `PromptLog`: 提示词库与使用统计。

## 安全性设计
*   **认证**: 基于 OAuth2 Password Bearer 的 JWT 认证。
*   **权限**: 依赖注入 `get_current_user` 与 `get_admin_user` 严格控制接口访问权限。
*   **数据完整性**: 引入 `prompt_id` 索引，确保异步任务结果能准确匹配到数据库记录。
*   **访问控制**: 严格限制 `list` 接口，确保普通用户只能访问自己的数据，管理员可访问所有数据。
*   **敏感信息**: 强制使用环境变量配置敏感密钥，并在启动时进行安全检查。

## 文件结构说明

位于 `backend/` 目录下：

*   **api/v1/**: 路由控制器
    *   `generation.py`: **核心**，处理绘图请求、队列管理与状态查询。
    *   `users.py`: 用户管理接口。
    *   `credits.py`: 积分系统接口。
    *   `analytics.py`: 数据看板接口。
    *   `drawings.py`: 绘图记录管理接口。
    *   `community.py`: 社区动态接口。
*   **core/**: 系统配置
    *   `config.py`: 环境变量加载 (DB URL, Secret Key)。
*   **models/**: 数据库模型 (ORM)
    *   `drawing.py`: 绘图表定义 (新增 `prompt_id` 字段)。
    *   `user.py`: 用户表定义。
*   **services/**: 业务服务层
    *   **ai/**: AI 适配层
        *   `comfyui.py`: ComfyUI 客户端实现。
        *   `base.py`: 生成器抽象基类。
*   `main.py`: 应用入口，CORS 配置。
*   `database.py`: 数据库连接池管理。

## 最近更改 (2025-12-03)
1.  **安全性修复与增强**:
    *   **权限控制**: 修复了 `api/v1/prompts.py` 和 `api/v1/drawings.py` 中 `list` 接口的权限漏洞，强制验证 `user_id` 归属或管理员权限。
    *   **密钥管理**: 增加了 `.env.example` 模板，并在 `core/config.py` 中添加了针对默认 `SECRET_KEY` 的启动警告，防止生产环境误用。
    *   **调试清理**: 移除了 `api/v1/auth.py` 中泄露验证码的 `print` 调试语句。
    *   **认证中间件**: 在 `api/v1/users.py` 中新增 `get_current_user_optional` 辅助函数，统一了 `community.py` 等模块的可选认证逻辑。
2.  **代码质量优化**:
    *   **依赖注入**: 统一了 `create_drawing` 接口的用户获取方式，直接从 `token` 解析 `current_user`，不再依赖不可信的前端参数。
    *   **逻辑复用**: 重构了 `community.py`，复用 `users` 模块的认证逻辑，减少代码冗余。
3.  **数据库 Schema 变更** (Previous):
    *   `Drawing` 表新增 `prompt_id` (VARCHAR, Index) 字段。
    *   目的：用于关联 ComfyUI 返回的任务 ID，实现异步任务状态追踪。
