# 腾讯云 COS 集成文档

本文档详细说明了如何配置和使用腾讯云 COS（对象存储服务）进行图片存储。

## 目录

- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [功能特性](#功能特性)
- [API 使用](#api-使用)
- [数据迁移](#数据迁移)
- [故障排查](#故障排查)
- [最佳实践](#最佳实践)

## 快速开始

### 1. 创建 COS Bucket

1. 登录 [腾讯云控制台](https://console.cloud.tencent.com/cos)
2. 创建新的 Bucket
   - 名称：自定义（如 `my-images-1234567890`）
   - 地域：选择离用户最近的地域（如 `ap-guangzhou`）
   - 访问权限：公有读私有写
3. 记录 Bucket 名称和地域

### 2. 获取 API 密钥

1. 访问 [API 密钥管理](https://console.cloud.tencent.com/cam/capi)
2. 创建新密钥或使用现有密钥
3. 记录 SecretId 和 SecretKey

### 3. 配置环境变量

在 `Backend/.env` 文件中添加：

```env
COS_SECRET_ID=your_secret_id_here
COS_SECRET_KEY=your_secret_key_here
COS_BUCKET=your_bucket_name_here
COS_REGION=ap-guangzhou
```

### 4. 安装依赖

```bash
pip install cos-python-sdk-v5
```

### 5. 启动服务

```bash
python -m uvicorn Backend.main:app --reload
```

## 配置说明

### 环境变量

| 变量名 | 说明 | 示例 | 必填 |
|--------|------|------|------|
| `COS_SECRET_ID` | 腾讯云 API 密钥 ID | `AKIDxxxxx` | 是 |
| `COS_SECRET_KEY` | 腾讯云 API 密钥 Key | `xxxxx` | 是 |
| `COS_BUCKET` | COS Bucket 名称 | `my-bucket-1234567890` | 是 |
| `COS_REGION` | COS 地域 | `ap-guangzhou` | 是 |

### 支持的地域

- `ap-guangzhou`: 广州
- `ap-shanghai`: 上海
- `ap-beijing`: 北京
- `ap-chengdu`: 成都
- `ap-chongqing`: 重庆
- `ap-hongkong`: 香港
- 更多地域请参考 [腾讯云文档](https://cloud.tencent.com/document/product/436/6224)

## 功能特性

### 自动上传

图片生成完成后，系统会自动：

1. 下载图片到本地临时目录
2. 生成缩略图（最大边长 400px）
3. 上传原图到 COS
4. 上传缩略图到 COS
5. 更新数据库记录
6. 更新用户存储统计
7. 清理本地临时文件

### 存储路径结构

```
ai-drawing-platform/images/
├── {user_id}/
│   ├── {drawing_id}_{timestamp}.png          # 原图
│   ├── {drawing_id}_{timestamp}_thumb.png    # 缩略图
│   └── ...
```

示例：
```
ai-drawing-platform/images/123/456_20260213120000.png
ai-drawing-platform/images/123/456_20260213120000_thumb.png
```

### 缩略图生成

- **最大尺寸**: 400px（宽或高）
- **保持宽高比**: 是
- **质量**: 85%
- **格式**: 与原图相同（PNG/JPEG）

### 重试机制

- **最大重试次数**: 3 次
- **重试策略**: 指数退避（1s, 2s, 4s）
- **失败处理**: 记录日志，不影响图片生成

### 存储统计

系统实时追踪每个用户的存储使用情况：

- **总图片数**: 用户上传的图片总数
- **已用空间**: 所有图片的总大小（字节）
- **平均大小**: 平均每张图片的大小

## API 使用

### 获取存储统计

```bash
GET /api/v1/users/me/storage
Authorization: Bearer {token}
```

响应：
```json
{
  "code": 200,
  "msg": "OK",
  "data": {
    "total_images": 42,
    "storage_used": 104857600,
    "storage_used_mb": 100.0,
    "average_size": 2496552
  }
}
```

### 同步存储统计

如果存储统计不准确，可以手动同步：

```bash
POST /api/v1/users/me/storage/sync
Authorization: Bearer {token}
```

响应：
```json
{
  "code": 200,
  "msg": "存储统计已同步",
  "data": {
    "old_storage": 100000000,
    "new_storage": 104857600,
    "difference": 4857600
  }
}
```

### 删除图片

删除图片时会自动删除 COS 中的文件：

```bash
DELETE /api/v1/drawings/{drawing_id}
Authorization: Bearer {token}
```

### 批量删除

```bash
POST /api/v1/drawings/batch-delete
Authorization: Bearer {token}
Content-Type: application/json

{
  "drawing_ids": [1, 2, 3, 4, 5]
}
```

响应：
```json
{
  "code": 200,
  "msg": "批量删除完成",
  "data": {
    "deleted": 5,
    "failed": 0,
    "errors": []
  }
}
```

## 数据迁移

### 迁移现有图片

如果你有现有的本地图片需要迁移到 COS：

#### 1. 试运行

先进行试运行，查看会迁移哪些文件：

```bash
python -m Backend.scripts.migrate_images_to_cos --dry-run
```

#### 2. 正式迁移

```bash
python -m Backend.scripts.migrate_images_to_cos --batch-size 100
```

参数说明：
- `--batch-size`: 每批处理的图片数量（默认 100）
- `--resume-from`: 从指定的 drawing_id 开始恢复
- `--dry-run`: 试运行，不实际上传

#### 3. 断点续传

如果迁移中断，可以从指定 ID 恢复：

```bash
python -m Backend.scripts.migrate_images_to_cos --resume-from 1000
```

#### 4. 查看迁移报告

迁移完成后会显示详细报告：

```
============================================================
Migration Report
============================================================
Total images: 1000
Migrated: 950
Skipped: 30
Failed: 20
Duration: 1234.56 seconds
============================================================
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

## 故障排查

### 问题 1: COS 上传失败

**症状**: 图片生成成功，但 COS 上传失败

**可能原因**:
1. COS 配置错误
2. 网络连接问题
3. 权限不足
4. Bucket 不存在

**解决方案**:

1. 检查配置：
```bash
# 查看配置是否正确
cat Backend/.env | grep COS
```

2. 测试连接：
```python
from Backend.services.cos import config_service

# 测试配置是否有效
if config_service.is_valid():
    print("配置有效")
    client = config_service.get_cos_client()
    print("客户端创建成功")
else:
    print("配置无效")
```

3. 检查权限：
   - 确保 SecretId/SecretKey 有 `PutObject` 权限
   - 在腾讯云控制台检查 Bucket 策略

4. 查看日志：
```bash
tail -f logs/app.log | grep COS
```

### 问题 2: 图片无法访问

**症状**: 图片上传成功，但无法在浏览器中访问

**可能原因**:
1. Bucket 权限设置为私有
2. CORS 配置不正确
3. URL 格式错误

**解决方案**:

1. 设置 Bucket 为公有读：
   - 登录腾讯云控制台
   - 进入 Bucket 设置
   - 权限管理 → 公有读私有写

2. 配置 CORS：
```json
[
  {
    "AllowedOrigins": ["*"],
    "AllowedMethods": ["GET", "HEAD"],
    "AllowedHeaders": ["*"],
    "ExposeHeaders": [],
    "MaxAgeSeconds": 3600
  }
]
```

3. 检查 URL 格式：
```
正确: https://bucket-name.cos.region.myqcloud.com/path/to/file.png
错误: http://bucket-name.cos.region.myqcloud.com/path/to/file.png (协议错误)
```

### 问题 3: 存储统计不准确

**症状**: 用户存储统计与实际不符

**解决方案**:

运行同步命令：
```bash
curl -X POST http://localhost:4135/api/v1/users/me/storage/sync \
  -H "Authorization: Bearer YOUR_TOKEN"
```

或者在 Python 中：
```python
from Backend.services.cos import StorageManager
from Backend.database import SessionLocal

db = SessionLocal()
result = StorageManager.sync_user_storage(user_id=123, db=db)
print(result)
```

### 问题 4: 迁移脚本失败

**症状**: 迁移脚本运行失败或中断

**解决方案**:

1. 使用断点续传：
```bash
# 查看最后成功的 drawing_id
# 然后从该 ID 继续
python -m Backend.scripts.migrate_images_to_cos --resume-from LAST_ID
```

2. 减小批次大小：
```bash
python -m Backend.scripts.migrate_images_to_cos --batch-size 50
```

3. 查看详细错误：
```bash
python -m Backend.scripts.migrate_images_to_cos 2>&1 | tee migration.log
```

## 最佳实践

### 1. 性能优化

#### CDN 加速

为 COS Bucket 配置 CDN 加速域名：

1. 登录腾讯云控制台
2. 进入 CDN 服务
3. 添加加速域名
4. 绑定到 COS Bucket
5. 更新代码使用 CDN 域名

#### 图片格式优化

使用 WebP 格式可减少 30-50% 文件大小：

```python
from PIL import Image

# 转换为 WebP
img = Image.open("image.png")
img.save("image.webp", "WEBP", quality=85)
```

#### 懒加载

前端实现图片懒加载：

```javascript
// 使用 Intersection Observer
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      const img = entry.target;
      img.src = img.dataset.src;
      observer.unobserve(img);
    }
  });
});

document.querySelectorAll('img[data-src]').forEach(img => {
  observer.observe(img);
});
```

### 2. 安全建议

#### 使用子账号

不要使用主账号的 SecretId/SecretKey，创建子账号：

1. 登录腾讯云控制台
2. 访问 CAM（访问管理）
3. 创建子用户
4. 授予最小权限（仅 COS 上传/删除）
5. 使用子账号密钥

#### 定期轮换密钥

建议每 90 天轮换一次 API 密钥。

#### 监控异常访问

在腾讯云控制台启用日志审计，监控异常访问。

### 3. 成本优化

#### 使用生命周期规则

设置生命周期规则自动删除或归档旧文件：

```json
{
  "Rules": [
    {
      "Status": "Enabled",
      "Filter": {
        "Prefix": "ai-drawing-platform/images/"
      },
      "Transition": [
        {
          "Days": 90,
          "StorageClass": "STANDARD_IA"
        }
      ]
    }
  ]
}
```

#### 监控存储用量

定期检查存储用量和费用：

```bash
# 获取所有用户的存储统计
curl http://localhost:4135/api/v1/admin/storage/stats \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

#### 清理无用文件

定期清理已删除用户的文件：

```python
# 清理孤立文件（数据库中不存在的 COS 文件）
python -m Backend.scripts.cleanup_orphaned_files
```

### 4. 监控和告警

#### 设置告警

在腾讯云控制台设置告警：

- 存储用量超过阈值
- 请求失败率超过阈值
- 带宽使用超过阈值

#### 日志分析

定期分析日志，发现潜在问题：

```bash
# 统计上传失败次数
grep "Failed to upload" logs/app.log | wc -l

# 查看最近的错误
grep "ERROR" logs/app.log | tail -20
```

## 参考资料

- [腾讯云 COS 官方文档](https://cloud.tencent.com/document/product/436)
- [Python SDK 文档](https://cloud.tencent.com/document/product/436/12269)
- [API 文档](https://cloud.tencent.com/document/product/436/7751)
- [最佳实践](https://cloud.tencent.com/document/product/436/38074)

## 支持

如有问题，请：

1. 查看本文档的故障排查部分
2. 查看项目 Issues
3. 联系技术支持
