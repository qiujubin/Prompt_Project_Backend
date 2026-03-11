# 外部 API 提供商配置系统

## 概述

外部 API 提供商配置系统允许用户选择预设的 AI 图像生成服务提供商，或使用自定义配置。系统支持从环境变量读取预设提供商的配置，简化用户操作。

## 架构设计

### 提供商类型

1. **预设提供商**：系统预配置的 AI 服务提供商
   - 通义千问 (tongyi)
   - 百度文心 (baidu)
   - DeepSeek (deepseek)
   - OpenAI DALL-E (openai)

2. **自定义提供商** (custom)：用户自行配置 API Key 和 URL

### 配置来源

- **预设提供商**：从环境变量读取配置（`.env` 文件）
- **自定义提供商**：用户在前端界面输入配置

## 后端实现

### 1. 提供商配置模块

**文件**: `Backend/services/ai/providers_config.py`

```python
class ProviderConfig(BaseModel):
    """提供商配置模型"""
    id: str
    name: str
    description: str
    api_key: Optional[str] = None
    api_url: Optional[str] = None
    secret_key: Optional[str] = None
    is_configured: bool = False
    requires_secret_key: bool = False
    supported_models: List[str] = []

def load_provider_configs() -> Dict[str, ProviderConfig]:
    """从环境变量加载提供商配置"""
    # 读取环境变量并构建配置字典
    pass

def get_provider_config(provider_id: str) -> Optional[ProviderConfig]:
    """获取指定提供商的配置"""
    pass
```

### 2. API 端点

**文件**: `Backend/api/v1/generation.py`

#### 获取提供商列表

```
GET /api/v1/generation/providers
```

**响应示例**:
```json
{
  "code": 200,
  "msg": "OK",
  "data": [
    {
      "id": "tongyi",
      "name": "通义千问",
      "description": "阿里云通义千问 AI 绘图",
      "is_configured": true,
      "requires_secret_key": false,
      "supported_models": ["wanx-v1", "wanx-sketch-v1"]
    },
    {
      "id": "custom",
      "name": "自定义",
      "description": "使用自定义 API 配置",
      "is_configured": true,
      "requires_secret_key": false,
      "supported_models": []
    }
  ]
}
```

#### 获取提供商模型列表

```
GET /api/v1/generation/models/{provider}
```

**响应示例**:
```json
{
  "code": 200,
  "msg": "OK",
  "data": {
    "provider": "tongyi",
    "models": ["wanx-v1", "wanx-sketch-v1"]
  }
}
```

#### 测试连接

```
POST /api/v1/generation/test-connection
```

**请求参数**:
- `provider`: 提供商 ID（必需）
- `api_key`: API Key（自定义提供商必需）
- `api_url`: API URL（可选）
- `secret_key`: Secret Key（可选，百度等需要）

**响应示例**:
```json
{
  "code": 200,
  "msg": "连接成功",
  "data": {
    "status": "connected"
  }
}
```

### 3. 生成逻辑更新

**文件**: `Backend/api/v1/generation.py`

```python
# 如果是自定义提供商，使用用户提供的配置
if provider == "custom":
    if req.api_key:
        params['api_key'] = req.api_key
    if req.api_url:
        params['api_url'] = req.api_url
    if req.secret_key:
        params['secret_key'] = req.secret_key
else:
    # 预设提供商，从环境变量读取配置
    config = get_provider_config(provider)
    if config and config.is_configured:
        params['api_key'] = config.api_key
        if config.api_url:
            params['api_url'] = config.api_url
        if config.secret_key:
            params['secret_key'] = config.secret_key
```

## 前端实现

### 1. API 调用

**文件**: `Frontend/src/api/api.ts`

```typescript
// 获取外部 API 提供商列表
getExternalProviders() {
  return request({
    url: "/generation/providers",
    method: "get"
  });
}

// 获取指定提供商支持的模型列表
getProviderModels(provider: string) {
  return request({
    url: `/generation/models/${provider}`,
    method: "get"
  });
}

// 测试外部 API 连接
testExternalConnection(data: any) {
  return request({
    url: "/generation/test-connection",
    method: "post",
    data
  });
}
```

### 2. 界面逻辑

**文件**: `Frontend/src/views/DrawingInterface.vue`

#### 数据结构

```typescript
// 外部 API 配置
const externalApiConfig = reactive({
  provider: '',
  model: '',
  // 自定义配置（仅当 provider === 'custom' 时使用）
  apiKey: '',
  apiUrl: '',
  secretKey: ''
})

// 外部 API 提供商列表
const externalProviders = ref<any[]>([])

// 外部 API 模型列表
const externalModels = ref<string[]>([])
```

#### 监听提供商变化

```typescript
watch(() => externalApiConfig.provider, async (newProvider) => {
  if (newProvider && newProvider !== 'custom') {
    try {
      const response = await api.getProviderModels(newProvider)
      externalModels.value = response.data?.models || []
      // 如果只有一个模型，自动选择
      if (externalModels.value.length === 1) {
        externalApiConfig.model = externalModels.value[0]
      }
    } catch (error) {
      console.warn('Failed to load models for provider:', newProvider, error)
      externalModels.value = []
    }
  } else {
    externalModels.value = []
  }
})
```

#### UI 布局

```vue
<!-- 提供商选择 -->
<el-form-item label="提供商" required>
  <el-select v-model="externalApiConfig.provider" placeholder="选择 API 提供商">
    <el-option
      v-for="provider in externalProviders"
      :key="provider.id"
      :label="provider.name"
      :value="provider.id"
    />
  </el-select>
</el-form-item>

<!-- 模型选择（非自定义时显示） -->
<el-form-item v-if="externalApiConfig.provider && externalApiConfig.provider !== 'custom'" label="模型" required>
  <el-select v-model="externalApiConfig.model" placeholder="选择模型">
    <el-option
      v-for="model in externalModels"
      :key="model"
      :label="model"
      :value="model"
    />
  </el-select>
</el-form-item>

<!-- 自定义配置区域（仅当选择"自定义"时显示） -->
<template v-if="externalApiConfig.provider === 'custom'">
  <el-form-item label="API Key" required>
    <el-input v-model="externalApiConfig.apiKey" type="password" placeholder="输入 API Key" />
  </el-form-item>
  <el-form-item label="API URL" required>
    <el-input v-model="externalApiConfig.apiUrl" placeholder="输入 API 地址" />
  </el-form-item>
  <el-form-item label="Secret Key">
    <el-input v-model="externalApiConfig.secretKey" type="password" placeholder="可选，部分 API 需要" />
  </el-form-item>
</template>
```

## 环境变量配置

**文件**: `Backend/.env.example`

```env
# 阿里云通义千问配置
TONGYI_API_KEY=
TONGYI_API_URL=https://dashscope.aliyuncs.com/api/v1

# 百度文心一言配置
BAIDU_API_KEY=
BAIDU_SECRET_KEY=
BAIDU_API_URL=https://aip.baidubce.com

# DeepSeek 配置
DEEPSEEK_API_KEY=
DEEPSEEK_API_URL=https://api.deepseek.com

# OpenAI DALL-E 配置
OPENAI_API_KEY=
OPENAI_API_URL=https://api.openai.com/v1
```

## 使用流程

### 预设提供商

1. 管理员在 `.env` 文件中配置提供商的 API Key
2. 用户在前端选择提供商（如"通义千问"）
3. 系统自动加载该提供商支持的模型列表
4. 用户选择模型
5. 点击"测试连接"验证配置
6. 开始生成图像

### 自定义提供商

1. 用户在前端选择"自定义"提供商
2. 输入 API Key、API URL 和 Secret Key（可选）
3. 点击"测试连接"验证配置
4. 开始生成图像

## 优势

1. **简化配置**：预设提供商无需用户输入 API Key
2. **灵活性**：支持自定义提供商满足特殊需求
3. **安全性**：敏感信息存储在服务器端环境变量
4. **可扩展**：易于添加新的提供商支持
5. **用户友好**：清晰的 UI 引导和错误提示

## 测试

运行测试脚本验证提供商配置系统：

```bash
cd Backend
python test_providers.py
```

## 注意事项

1. 预设提供商的 API Key 必须在服务器端配置
2. 自定义提供商的配置仅在当前会话有效
3. 测试连接会实际调用 API，可能产生费用
4. 部分提供商需要 Secret Key（如百度）
5. 模型列表根据提供商动态加载
