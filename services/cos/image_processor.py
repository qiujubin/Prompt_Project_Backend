"""图片处理服务

负责图片处理操作，包括缩略图生成、尺寸获取、文件下载等。
"""

import os
from utils.httpx_compat import httpx_compat as httpx
from typing import Tuple
from io import BytesIO
from PIL import Image
from core.logger import get_logger

logger = get_logger(__name__)


class ImageProcessorError(Exception):
    """图片处理错误异常"""
    pass


class ImageProcessor:
    """图片处理服务

    提供图片处理相关功能：
    - 缩略图生成
    - 图片尺寸获取
    - 文件大小获取
    - 远程图片下载

    Requirements: 3.1, 3.2
    """

    THUMBNAIL_MAX_SIZE = 400  # 缩略图最大边长（像素）

    @staticmethod
    def generate_thumbnail(
        image_path: str,
        max_size: int = THUMBNAIL_MAX_SIZE
    ) -> bytes:
        """生成缩略图

        保持原始宽高比，将图片缩放到最大边长不超过 max_size。

        Args:
            image_path: 原始图片路径
            max_size: 最大边长（像素），默认 400

        Returns:
            缩略图二进制数据

        Raises:
            ImageProcessorError: 如果图片处理失败

        Requirements: 3.1, 3.2
        """
        try:
            # 打开图片
            with Image.open(image_path) as img:
                # 获取原始尺寸
                original_width, original_height = img.size

                # 如果图片已经很小，不需要缩放
                if original_width <= max_size and original_height <= max_size:
                    # 直接返回原图
                    buffer = BytesIO()
                    img.save(buffer, format=img.format or 'PNG')
                    return buffer.getvalue()

                # 计算缩放比例（保持宽高比）
                if original_width > original_height:
                    new_width = max_size
                    new_height = int(original_height * (max_size / original_width))
                else:
                    new_height = max_size
                    new_width = int(original_width * (max_size / original_height))

                # 缩放图片（使用高质量重采样）
                img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                # 转换为字节
                buffer = BytesIO()
                # 保持原始格式，如果无法确定则使用 PNG
                save_format = img.format or 'PNG'
                img_resized.save(buffer, format=save_format, quality=85)

                logger.info(
                    f"Thumbnail generated: {original_width}x{original_height} -> "
                    f"{new_width}x{new_height}"
                )

                return buffer.getvalue()

        except Exception as e:
            logger.error(f"Failed to generate thumbnail: {e}")
            raise ImageProcessorError(f"Failed to generate thumbnail: {str(e)}")

    @staticmethod
    def get_image_size(image_path: str) -> Tuple[int, int]:
        """获取图片尺寸

        Args:
            image_path: 图片文件路径

        Returns:
            (width, height) 元组

        Raises:
            ImageProcessorError: 如果无法读取图片
        """
        try:
            with Image.open(image_path) as img:
                return img.size
        except Exception as e:
            logger.error(f"Failed to get image size: {e}")
            raise ImageProcessorError(f"Failed to get image size: {str(e)}")

    @staticmethod
    def get_file_size(file_path: str) -> int:
        """获取文件大小（字节）

        Args:
            file_path: 文件路径

        Returns:
            文件大小（字节）

        Raises:
            ImageProcessorError: 如果文件不存在
        """
        try:
            return os.path.getsize(file_path)
        except Exception as e:
            logger.error(f"Failed to get file size: {e}")
            raise ImageProcessorError(f"Failed to get file size: {str(e)}")

    @staticmethod
    async def download_image(url: str, save_path: str) -> str:
        """下载远程图片到本地

        Args:
            url: 图片 URL
            save_path: 保存路径

        Returns:
            本地文件路径

        Raises:
            ImageProcessorError: 如果下载失败
        """
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(url)
                response.raise_for_status()

                # 确保目录存在
                os.makedirs(os.path.dirname(save_path), exist_ok=True)

                # 保存文件
                with open(save_path, 'wb') as f:
                    f.write(response.content)

                logger.info(f"Image downloaded: {url} -> {save_path}")
                return save_path

        except Exception as e:
            logger.error(f"Failed to download image from {url}: {e}")
            raise ImageProcessorError(f"Failed to download image: {str(e)}")
