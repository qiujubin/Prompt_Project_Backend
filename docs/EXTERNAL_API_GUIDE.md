# 外部 AI API 画图接口使用指南

## 概述

本系统现在支持多种外部 AI 服务进行图像生成，包括：
- OpenAI DALL-E
- 阿里云通义千问万相
- 百度文心一言
- 腾讯混元

## 支持的 API 提供商

### 1. OpenAI DALL-E
- **提供商 ID**: `openai`
- **所需参数**: API Key
- **支持尺寸**: 512x512, 1024x1024, 1024x1792, 1792x1024
- **异步支持**: 否（同步返回）
- **配置示例**:
  ```env
  AI_API_KEY=sk-your-openai-api-key
  AI_API_URL=https://api.openai.com/v1
  ```

### 2. 阿里云通义千问万相
- **提供商 ID**: `tongyi`
- **所需参数**: API Key
- **支持尺寸**: 512x512, 768x768, 1024x1024
- **异步支持**: 是（支持任务队列）
- **配置示例**:
  ```env
  TONGYI_API_KEY=your-dashscope-api-key
  TONGYI_API_URL=https://dashscope.aliyuncs.com/api/v1
  ```

### 3. 百度文心一言
- **提供商 ID**: `baidu`
- **所需参数**: API Key + Secret Key
- **支持尺寸**: 512x512, 768x768, 1024x1024
- **异步支持**: 否（同步返回 base64）
- **配置示例**:
  ```env
  BAIDU_AI_API_KEY=your-baidu-api-key
  BAIDU_AI_SECRET_KEY=your-baidu-secret-key
  BAIDU_AI_API_URL=https://aip.baidubce.com
  ```

### 4. 腾讯混元
- **提供商 ID**: `tencent`
- **所需参数**: API Key
- **支持尺寸**: 512x512, 768x768, 1024x1024
- **异步支持**: 否（同步返回 base64）
- **配置示例**:
  ```env
  TENCENT_API_KEY=your-tencent-api-key
  TENCENT_API_URL=https://hunyuan.tencentcloudapi.com
  ```

## API 接口

### 1. 获取支持的提供商列表
```http
GET /api/v1/generation/providers
```

**响应示例**:
```json
{
  "code": 200,
  "msg": "OK",
  "data": [
    {
      "id": "openai",
      "name": "OpenAI DALL-E",
      "description": "OpenAI 的 DALL-E 图像生成模型",
      "supported_sizes": ["512x512", "1024x1024"],
      "requires_secret": false,
      "async_support": false,
      "default_model": "dall-e-3"
    }
  ]
}
```

### 2. 测试 API 连接
```http
POST /api/v1/generation/test-connection
Content-Type: application/json

{
  "provider": "openai",
  "api_key": "your-api-key",
  "api_url": "https://api.openai.com/v1",
  "secret_key": "optional-secret-key"
}
```

### 3. 生成图像
```http
POST /api/v1/generation/draw
Content-Type: application/json

{
  "prompt": "a beautiful sunset",
  "negative_prompt": "blurry, low quality",
  "backend": "external",
  "provider": "openai",
  "api_key": "your-api-key",
  "width": 1024,
  "height": 1024,
  "seed": -1
}
```

### 4. 查询任务状态（异步 API）
```http
GET /api/v1/generation/status/external/{task_id}?provider=tongyi&api_key=your-key
```

## 前端使用

### 1. 后端选择
在画图界面中，用户可以选择：
- **ComfyUI 本地**: 使用本地 ComfyUI 服务
- **外部 API**: 使用云端 AI 服务

### 2. 外部 API 配置
选择外部 API 后，需要配置：
- **提供商**: 选择 AI 服务提供商
- **API Key**: 输入 API 密钥
- **API URL**: 可选，自定义服务地址
- **Secret Key**: 百度 API 需要
- **风格**: 部分 API 支持风格参数

### 3. 连接测试
配置完成后，点击"测试连接"按钮验证配置是否正确。

## 成本控制

### 积分消耗策略
- **ComfyUI 本地**: 消耗 2 积分
- **外部 API（系统配置）**: 消耗 2 积分
- **外部 API（用户自定义）**: 可配置为免费或优惠价格

### 失败退款
- API 调用失败时自动退还已扣除的积分
- 网络错误、超时等临时问题会自动重试

## 错误处理

### 常见错误类型
1. **CONNECTION_ERROR**: 网络连接失败
2. **TIMEOUT_ERROR**: 请求超时
3. **INVALID_API_KEY**: API 密钥无效
4. **QUOTA_EXCEEDED**: API 配额不足
5. **CONTENT_POLICY**: 内容违反政策

### 重试机制
- 临时错误（网络、超时）: 自动重试最多 3 次
- 永久错误（密钥、配额）: 立即返回错误
- 使用指数退避策略避免频繁请求

## 安全性

### 数据保护
- API Key 使用加密存储
- 传输过程使用 HTTPS
- 日志中不记录敏感信息

### 隐私保护
- 用户提示词不会被系统记录
- 生成的图像遵循各 API 提供商的隐私政策

## 故障排除

### 1. 连接测试失败
- 检查 API Key 是否正确
- 确认网络连接正常
- 验证 API URL 是否正确

### 2. 生成失败
- 检查提示词是否符合内容政策
- 确认 API 配额是否充足
- 查看错误信息获取具体原因

### 3. 异步任务超时
- 通义千问等异步 API 可能需要较长时间
- 系统会自动轮询任务状态
- 超时后会自动退还积分

## 开发者指南

### 添加新的 API 提供商

1. 在 `ExternalAIGenerator` 中添加新的生成方法
2. 更新 `get_external_providers` 接口
3. 在前端添加相应的配置选项
4. 编写测试用例验证功能

### 自定义参数映射
不同 API 提供商的参数格式可能不同，系统会自动进行参数转换和适配。

## 更新日志

### v1.0.0 (2024-03-10)
- 初始版本发布
- 支持 OpenAI、通义千问、百度、腾讯四家 API 提供商
- 实现统一的生成接口和状态查询
- 添加连接测试和错误处理功能
