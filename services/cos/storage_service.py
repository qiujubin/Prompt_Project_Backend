"""COS 存储服务

负责文件上传、删除和查询操作。
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, List
from io import BytesIO
from qcloud_cos import CosServiceError
from .config_service import config_service, COSConfigError
from core.logger import get_logger

logger = get_logger(__name__)


class COSStorageError(Exception):
    """COS 存储错误异常"""
    pass


class COSStorageService:
    """COS 存储服务

    提供文件上传、删除和查询功能：
    - 简单上传（< 5MB）
    - 分片上传（>= 5MB）
    - 文件删除
    - 批量删除
    - 文件存在性检查

    Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 6.1, 6.2, 6.3, 6.4
    """

    MULTIPART_THRESHOLD = 5 * 1024 * 1024  # 5MB
    MAX_RETRY_ATTEMPTS = 3
    BASE_PATH = "ai-drawing-platform/images"
    AVATAR_BASE_PATH = "ai-drawing-platform/avatars"

    def __init__(self):
        self.config_service = config_service

    def _build_object_key(
        self,
        user_id: int,
        drawing_id: int,
        timestamp: str,
        is_thumbnail: bool = False,
        is_avatar: bool = False
    ) -> str:
        """构建 COS 对象键

        Format: ai-drawing-platform/images/{user_id}/{drawing_id}_{timestamp}.png
        Thumbnail: ai-drawing-platform/images/{user_id}/{drawing_id}_{timestamp}_thumb.png
        Avatar: ai-drawing-platform/avatars/{user_id}/{timestamp}.png

        Args:
            user_id: 用户 ID
            drawing_id: 作品 ID
            timestamp: 时间戳
            is_thumbnail: 是否为缩略图
            is_avatar: 是否为头像

        Returns:
            COS 对象键字符串

        Requirements: 2.2
        """
        if is_avatar:
            return f"{self.AVATAR_BASE_PATH}/{user_id}/{timestamp}.png"

        suffix = "_thumb" if is_thumbnail else ""
        filename = f"{drawing_id}_{timestamp}{suffix}.png"
        return f"{self.BASE_PATH}/{user_id}/{filename}"

    async def upload_image(
        self,
        file_path: str,
        user_id: int,
        drawing_id: int,
        is_thumbnail: bool = False,
        is_avatar: bool = False
    ) -> Dict[str, Any]:
        """上传图片到 COS

        根据文件大小自动选择简单上传或分片上传。
        支持重试机制（最多 3 次，指数退避）。

        Args:
            file_path: 本地文件路径
            user_id: 用户 ID
            drawing_id: 作品 ID
            is_thumbnail: 是否为缩略图
            is_avatar: 是否为头像

        Returns:
            {
                "cos_key": "对象键",
                "cos_url": "公共访问 URL",
                "file_size": 文件大小（字节）
            }

        Raises:
            COSStorageError: 如果上传失败

        Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6
        """
        try:
            client = self.config_service.get_cos_client()
            bucket = self.config_service.get_bucket()
            config = self.config_service.get_config()

            # 生成对象键
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            cos_key = self._build_object_key(user_id, drawing_id, timestamp, is_thumbnail, is_avatar)

            # 获取文件大小
            import os
            file_size = os.path.getsize(file_path)

            # 重试逻辑
            for attempt in range(self.MAX_RETRY_ATTEMPTS):
                try:
                    # 根据文件大小选择上传方式
                    if file_size >= self.MULTIPART_THRESHOLD:
                        logger.info(f"Using multipart upload for {file_path} ({file_size} bytes)")
                        await self._multipart_upload(client, bucket, cos_key, file_path, file_size)
                    else:
                        logger.info(f"Using simple upload for {file_path} ({file_size} bytes)")
                        with open(file_path, 'rb') as f:
                            client.put_object(
                                Bucket=bucket,
                                Body=f,
                                Key=cos_key,
                                EnableMD5=True
                            )

                    # 生成公共 URL
                    cos_url = self.get_public_url(cos_key)

                    logger.info(f"Successfully uploaded to COS: {cos_key}")

                    return {
                        "cos_key": cos_key,
                        "cos_url": cos_url,
                        "file_size": file_size
                    }

                except CosServiceError as e:
                    if attempt < self.MAX_RETRY_ATTEMPTS - 1:
                        # 指数退避
                        delay = 2 ** attempt
                        logger.warning(
                            f"Upload attempt {attempt + 1} failed, retrying in {delay}s: {e.get_error_msg()}"
                        )
                        await asyncio.sleep(delay)
                    else:
                        raise

        except COSConfigError as e:
            raise COSStorageError(f"COS configuration error: {str(e)}")
        except CosServiceError as e:
            raise COSStorageError(f"COS upload failed: {e.get_error_msg()}")
        except Exception as e:
            raise COSStorageError(f"Upload failed: {str(e)}")

    async def _multipart_upload(
        self,
        client,
        bucket: str,
        key: str,
        file_path: str,
        file_size: int
    ) -> None:
        """分片上传大文件

        Args:
            client: COS 客户端
            bucket: Bucket 名称
            key: 对象键
            file_path: 文件路径
            file_size: 文件大小

        Requirements: 2.3
        """
        part_size = 5 * 1024 * 1024  # 5MB per part

        # 创建分片上传
        response = client.create_multipart_upload(
            Bucket=bucket,
            Key=key
        )
        upload_id = response['UploadId']

        parts = []
        part_number = 1

        try:
            with open(file_path, 'rb') as f:
                while True:
                    data = f.read(part_size)
                    if not data:
                        break

                    # 上传分片
                    part_response = client.upload_part(
                        Bucket=bucket,
                        Key=key,
                        Body=data,
                        PartNumber=part_number,
                        UploadId=upload_id
                    )

                    parts.append({
                        'PartNumber': part_number,
                        'ETag': part_response['ETag']
                    })
                    part_number += 1

            # 完成分片上传
            client.complete_multipart_upload(
                Bucket=bucket,
                Key=key,
                UploadId=upload_id,
                MultipartUpload={'Part': parts}
            )

        except Exception as e:
            # 失败时中止分片上传
            try:
                client.abort_multipart_upload(
                    Bucket=bucket,
                    Key=key,
                    UploadId=upload_id
                )
            except:
                pass
            raise e

    async def delete_image(self, cos_key: str) -> bool:
        """从 COS 删除图片

        Args:
            cos_key: COS 对象键

        Returns:
            True 如果删除成功

        Raises:
            COSStorageError: 如果删除失败

        Requirements: 6.1, 6.2, 6.3
        """
        try:
            client = self.config_service.get_cos_client()
            bucket = self.config_service.get_bucket()

            # 检查文件是否存在
            try:
                client.head_object(Bucket=bucket, Key=cos_key)
            except CosServiceError as e:
                if e.get_error_code() == 'NoSuchKey':
                    logger.warning(f"File not found in COS: {cos_key}")
                    return False
                raise

            # 删除文件
            client.delete_object(Bucket=bucket, Key=cos_key)
            logger.info(f"Successfully deleted from COS: {cos_key}")
            return True

        except COSConfigError as e:
            raise COSStorageError(f"COS configuration error: {str(e)}")
        except CosServiceError as e:
            raise COSStorageError(f"COS delete failed: {e.get_error_msg()}")
        except Exception as e:
            raise COSStorageError(f"Delete failed: {str(e)}")

    async def batch_delete_images(self, cos_keys: List[str]) -> Dict[str, Any]:
        """批量删除图片

        Args:
            cos_keys: COS 对象键列表

        Returns:
            {
                "deleted": 成功删除的数量,
                "failed": 失败的数量,
                "errors": 错误列表
            }

        Requirements: 6.4
        """
        deleted = 0
        failed = 0
        errors = []

        for cos_key in cos_keys:
            try:
                await self.delete_image(cos_key)
                deleted += 1
            except Exception as e:
                failed += 1
                errors.append({"key": cos_key, "error": str(e)})
                logger.error(f"Failed to delete {cos_key}: {e}")

        return {
            "deleted": deleted,
            "failed": failed,
            "errors": errors
        }

    def get_public_url(self, cos_key: str) -> str:
        """生成公共访问 URL

        Args:
            cos_key: COS 对象键

        Returns:
            公共访问 URL

        Requirements: 5.1
        """
        config = self.config_service.get_config()
        bucket = config.bucket
        region = config.region
        return f"https://{bucket}.cos.{region}.myqcloud.com/{cos_key}"

    async def file_exists(self, cos_key: str) -> bool:
        """检查文件是否存在

        Args:
            cos_key: COS 对象键

        Returns:
            True 如果文件存在
        """
        try:
            client = self.config_service.get_cos_client()
            bucket = self.config_service.get_bucket()
            client.head_object(Bucket=bucket, Key=cos_key)
            return True
        except CosServiceError as e:
            if e.get_error_code() == 'NoSuchKey':
                return False
            return False
        except Exception:
            return False
