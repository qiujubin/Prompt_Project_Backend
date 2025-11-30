# API 文档（v1）

## 认证与绑定 `/api/auth/*`
- `POST /auth/register` 注册用户（账户+密码）
- `POST /auth/login` 账户密码登录，返回 `{ code, msg, data: { access_token, token_type } }`
- `POST /auth/send_email_code` 发送邮箱验证码（示例）
- `POST /auth/send_sms_code` 发送短信验证码（示例）
- `POST /auth/login_with_email_code` 邮箱验证码登录（不存在则自动注册）
- `POST /auth/login_with_sms_code` 手机验证码登录（不存在则自动注册）
- `POST /auth/bind_email` 绑定邮箱到用户（需验证码与唯一性校验）
- `POST /auth/bind_phone` 绑定手机号到用户（需验证码与唯一性校验）
- `POST /auth/bind_wechat` 绑定微信 `openid` 到用户（唯一性校验）

## 用户 `/api/users/*`
- `GET /users/` 获取用户列表（仅管理员，分页+搜索）
- `GET /users/me` 获取当前登录用户信息（需 `Authorization: Bearer <token>`）
- `DELETE /users/{id}` 根据ID删除用户（仅管理员）
- `POST /users/update_username` 修改用户名（参数：user_id, username）
- `POST /users/update_avatar` 修改头像（参数：user_id, avatar_url）
- `POST /users/update_phone` 用户添加或修改手机号（参数：user_id, phone）
- `POST /users/update_email` 用户添加或修改邮箱（参数：user_id, email）
- `POST /users/update_password` 用户修改密码（参数：user_id, password）

## 提示词层级 `/api/prompts/*`
- `GET /prompts/categories` 获取所有大分类
- `GET /prompts/categories/{id}/subcategories` 获取指定大分类下的小分类
- `GET /prompts/subcategories/{id}/keywords` 获取指定小分类下的提示词
- `GET /prompts/categories/{id}/tree` 获取指定大分类下的完整树结构（小分类+提示词）
- `POST /prompts/keywords` 添加提示词（参数：user_id, small_category_id, word）
- `DELETE /prompts/keywords/{id}` 删除提示词（参数：user_id，需权限验证）
- `POST /prompts/logs` 记录提示词使用日志（参数：user_id, small_category_id, weight, is_negative, drawing_id）
- `GET /prompts/logs` 获取提示词使用日志（可选 `user_id`，分页）

## 首页与菜单 `/api/home/*`
- `GET /home/getPromptCatagory` 返回分类树：`{ code, msg, data: { promptCatagory: [...] } }`
- `POST /home/getDropdown` 返回动态菜单：`{ code, msg, data: { role, token, dropdownList } }`

## 绘图 `/api/drawings/*`
- `POST /drawings/create` 创建绘图记录（默认状态 'finish'）
- `PUT /drawings/{id}/public` 修改绘图公开状态（参数：is_public）
- `PUT /drawings/{id}/status` 修改绘图状态（参数：status）
- `GET /drawings/` 获取绘图记录列表（可选 `user_id`，分页）

## 分析数据 `/api/userCenter/*`
- `GET /userCenter/getPositiveMaxData` 返回正向分析数据（Top 10 提示词）
- `GET /userCenter/getNegativeMaxData` 返回反向分析数据（Top 10 提示词）
- `GET /userCenter/getDailyDrawings` 返回最近7天绘图趋势（可选 `?days=`）
- `GET /userCenter/getModelUsage` 返回模型使用分布（Top 10）
- `GET /userCenter/getUserGrowth` 返回最近7天用户增长趋势（可选 `?days=`）
- `GET /userCenter/getActiveUsers` 返回活跃用户排行（Top 10 绘图数）
- `GET /userCenter/getSubcategoryUsage` 返回热门提示词分类（Top 10）

## 管理端通用 CRUD `/api/admin/*`
- `GET /admin/<resource>?page=&size=&q=` 分页列表与模糊查
- `GET /admin/<resource>/{id}` 详情
- `POST /admin/<resource>` 创建
- `PUT /admin/<resource>/{id}` 全量更新
- `PATCH /admin/<resource>/{id}` 部分更新
- `DELETE /admin/<resource>/{id}` 删除

支持资源：
- `users`、`social_accounts`、`drawings`、`prompt_logs`、`prompt_categories`、`prompt_subcategories`、`prompt_keywords`

请求体示例：
```json
POST /api/admin/prompt_categories
{
  "name": "style",
  "display_name": "风格",
  "sort_order": 0
}
```

## 复合主键资源
- 收藏 `/api/admin/user_favorites`
  - `GET /` 列表（可选 `?user_id=`），返回包含提示词详情
  - `POST /?user_id=&keyword_id=` 创建或覆盖（兼容旧接口）
  - `POST /add?user_id=&keyword_id=` 添加收藏（新接口，自动去重）
  - `POST /remove?user_id=&keyword_id=` 取消收藏
  - `DELETE /?user_id=&keyword_id=` 删除
- 使用统计 `/api/admin/user_prompt_keywords`
  - `GET /` 列表（可选 `?user_id=`），返回包含提示词详情
  - `POST /increment` 记录使用：不存在则创建(count=1)，存在则+1（参数：user_id, keyword_id）
  - `POST /?user_id=&keyword_id=&used_count=` 创建或覆盖
  - `PUT /?user_id=&keyword_id=&used_count=` 更新使用次数
  - `DELETE /?user_id=&keyword_id=` 删除

## 统一返回结构
- 成功：`{ "code": 200, "msg": "OK", "data": ... }`
- 失败：HTTP 状态码 + `detail` 字段描述错误原因

## 认证说明
- 使用 JWT Bearer 令牌访问受限接口：
  - 请求头：`Authorization: Bearer <token>`
  - 令牌获取：通过 `/auth/login` 或验证码登录接口

## 错误码与异常
- 登录失败：`401` + `detail: "认证失败"`
- 资源不存在：`404` + `detail: "Not found"`
- 绑定冲突：`400` + `detail: 如 "邮箱已被使用"`

## 备注
- 验证码接口为示例实现，生产环境需接入真实短信/邮件服务并持久化存储
- 建议为 `/api/admin/*` 接口增加角色权限控制与审计日志
