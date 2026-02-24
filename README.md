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


## COS 图片存储集成

本项目已集成腾讯云 COS（对象存储服务）用于图片存储，提供高可用、高性能的图片存储和访问能力。

### 配置 COS

在 `.env` 文件中添加以下配置：

```env
# 腾讯云 COS 配置
COS_SECRET_ID=your_secret_id_here
COS_SECRET_KEY=your_secret_key_here
COS_BUCKET=your_bucket_name_here
COS_REGION=ap-guangzhou
```

### 功能特性

- **自动上传**: 图片生成完成后自动上传到 COS
- **缩略图生成**: 自动生成 400px 缩略图，提升加载速度
- **存储统计**: 实时追踪用户存储空间使用情况
- **批量删除**: 支持批量删除图片和 COS 文件
- **重试机制**: 上传失败自动重试（最多 3 次）
- **优雅降级**: COS 上传失败不影响图片生成

### API 端点

#### 存储统计
```bash
# 获取当前用户存储统计
GET /api/v1/users/me/storage

# 同步存储使用量（修复统计不准确）
POST /api/v1/users/me/storage/sync
```

#### 图片管理
```bash
# 删除图片（自动删除 COS 文件）
DELETE /api/v1/drawings/{drawing_id}

# 批量删除图片
POST /api/v1/drawings/batch-delete
Body: {"drawing_ids": [1, 2, 3]}
```

### 数据迁移

如果你有现有的本地图片需要迁移到 COS：

```bash
# 试运行（不实际上传）
python -m Backend.scripts.migrate_images_to_cos --dry-run

# 正式迁移
python -m Backend.scripts.migrate_images_to_cos --batch-size 100

# 从指定 ID 恢复迁移
python -m Backend.scripts.migrate_images_to_cos --resume-from 1000
```

### 临时文件清理

定期清理过期的临时文件：

```bash
# 清理超过 24 小时的临时文件
python -m Backend.scripts.cleanup_temp_files

# 清理超过 48 小时的临时文件
python -m Backend.scripts.cleanup_temp_files --max-age 48

# 试运行
python -m Backend.scripts.cleanup_temp_files --dry-run
```

### 故障排查

#### COS 上传失败

1. **检查配置**: 确保 `.env` 中的 COS 配置正确
2. **检查权限**: 确保 SecretId/SecretKey 有上传权限
3. **检查网络**: 确保服务器能访问 COS 服务
4. **查看日志**: 检查日志文件中的详细错误信息

#### 存储统计不准确

运行同步命令修复：

```bash
curl -X POST http://localhost:8000/api/v1/users/me/storage/sync \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### 图片无法访问

1. **检查 Bucket 权限**: 确保 Bucket 允许公共读取
2. **检查 URL 格式**: 确保 URL 格式正确
3. **检查 CORS 配置**: 如果前端跨域访问，需配置 COS CORS

### 性能优化建议

- **CDN 加速**: 为 COS Bucket 配置 CDN 加速域名
- **图片格式**: 使用 WebP 格式可减少 30-50% 文件大小
- **缩略图**: 列表页使用缩略图，详情页使用原图
- **懒加载**: 前端实现图片懒加载
