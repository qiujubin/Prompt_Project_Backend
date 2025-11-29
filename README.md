# 后端系统说明

本后端基于 FastAPI + SQLAlchemy + PostgreSQL 构建，提供用户认证、分类与提示词管理、绘图记录、游客模式、通用 CRUD、日志与性能监控等能力，面向前端 `Vue3 + Element Plus` 项目进行接口对接。

## 技术栈
- Web 框架：FastAPI
- ORM：SQLAlchemy (2.x)
- 数据库：PostgreSQL (`psycopg` 驱动)
- 校验与模型：Pydantic (v2)
- 安全：JWT (`python-jose`)、bcrypt (`passlib`)
- 文档：Swagger/OpenAPI (`/docs`)

## 目录结构
```
Backend/
├── main.py                 # 应用入口
├── core/                   # 核心配置与安全、日志
│   ├── config.py           # 环境变量与配置项
│   ├── security.py         # JWT 认证、密码哈希
│   └── logger.py           # 日志配置
├── database.py             # 数据库连接与会话、连接池
├── middleware.py           # 性能监控中间件
├── models/                 # ORM 模型（与 PostgreSQL 表结构对齐）
├── schemas/                # Pydantic 模型（请求/响应体）
├── api/                    # 路由与业务逻辑
│   └── v1/                 # v1 版本接口
├── services/               # 业务服务层（验证码、微信、AI、文件）
├── utils/                  # 通用工具（CRUD 路由生成器）
└── requirements.txt        # 依赖清单
```

## 环境变量
- `DB_URL`：数据库连接串，默认 `postgresql+psycopg://postgres:123456@localhost/graduation`
- `SECRET_KEY`：JWT 密钥，默认 `dev-secret`
- `ACCESS_TOKEN_EXPIRE_MINUTES`：token 过期分钟数，默认 `60`
- `CORS_ORIGINS`：逗号分隔的跨域来源，默认 `http://localhost:5173`
- `VERIFICATION_CODE_EXPIRE_SECONDS`：验证码过期秒数，默认 `300`
- `VERIFICATION_CODE_MAX_ATTEMPTS`：最大尝试次数，默认 `5`
- `VERIFICATION_CODE_RESEND_INTERVAL`：最小重发间隔秒数，默认 `60`

## 启动
```bash
pip install -r Backend/requirements.txt
python -m uvicorn Backend.main:app --reload --port 8000
```
接口文档访问：`http://localhost:8000/docs`

## 跨域与前端对接
- 已开启 CORS，允许来自 `CORS_ORIGINS` 的跨域请求
- 前端建议配置代理：`/api -> http://localhost:8000`

## 核心功能
- 认证与绑定：账户密码、邮箱/短信验证码登录，邮箱/手机号/微信绑定
- 分类与提示词：从数据库生成分类树，关键词管理
- 绘图记录：记录提示词、模型名称、图片地址、尺寸、耗时、是否公开
- 游客模式：返回游客可见菜单与部分数据接口
- 通用 CRUD：按 `admin/*` 前缀提供各模型的增删改查与分页筛选
- 日志与监控：请求耗时日志中间件

## 重要路由前缀
- 业务接口：`/api/home/*`、`/api/auth/*`、`/api/users/*`、`/api/drawings/*`、`/api/userCenter/*`
- 管理接口（CRUD）：`/api/admin/*`

## 示例请求
- 注册：
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"123456"}'
```
- 登录：
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"123456"}'
```
- 获取分类树：
```bash
curl http://localhost:8000/api/home/getPromptCatagory
```
- 管理端分页查询关键词：
```bash
curl "http://localhost:8000/api/admin/prompt_keywords?page=1&size=10&q=风格"
```

## 扩展建议
- 引入 Alembic 进行数据库迁移管理
- 将验证码与会话存储迁移到 Redis/数据库
- 接入实际短信/邮件服务与微信登录流程
- 完善角色与权限体系，收敛 `admin/*` 接口访问

---
更多接口详情见 `Backend/docs/API.md`。
