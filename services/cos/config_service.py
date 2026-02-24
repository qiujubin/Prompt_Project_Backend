"""COS 配置服务

负责加载、验证和管理腾讯云 COS 配置，创建 COS 客户端实例。
使用单例模式确保全局只有一个配置和客户端实例。
"""

import os
from typing import Optional
from dotenv import load_dotenv
from qcloud_cos import CosConfig, CosS3Client
from pydantic import BaseModel
from core.logger import get_logger

logger = get_logger(__name__)


class COSConfigError(Exception):
    """COS 配置错误异常"""
    pass


class COSConfigModel(BaseModel):
    """COS 配置模型"""
    secret_id: str
    secret_key: str
    bucket: str
    region: str


class COSConfigService:
    """COS 配置服务（单例模式）

    负责：
    - 从环境变量加载 COS 配置
    - 验证配置有效性
    - 创建和缓存 COS 客户端实例

    Requirements: 1.1, 1.2, 1.3, 1.4
    """

    _instance: Optional['COSConfigService'] = None
    _config: Optional[COSConfigModel] = None
    _cos_client: Optional[CosS3Client] = None

    def __new__(cls):
        """单例模式：确保全局只有一个配置实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化配置服务"""
        if self._config is None:
            self._load_config()

    def _load_config(self) -> None:
        """从环境变量加载配置

        Requirements: 1.1
        """
        load_dotenv()

        secret_id = os.getenv('COS_SECRET_ID', '')
        secret_key = os.getenv('COS_SECRET_KEY', '')
        bucket = os.getenv('COS_BUCKET', '')
        region = os.getenv('COS_REGION', '')

        self._config = COSConfigModel(
            secret_id=secret_id,
            secret_key=secret_key,
            bucket=bucket,
            region=region
        )

        logger.info(f"COS configuration loaded - Region: {region}, Bucket: {bucket}")

    @staticmethod
    def validate_config(config: COSConfigModel) -> bool:
        """验证 COS 配置有效性

        Args:
            config: COS 配置模型

        Returns:
            True 如果配置有效，False 否则

        Requirements: 1.4
        """
        if not config.secret_id or not config.secret_id.strip():
            return False
        if not config.secret_key or not config.secret_key.strip():
            return False
        if not config.bucket or not config.bucket.strip():
            return False
        if not config.region or not config.region.strip():
            return False
        return True

    def get_config(self) -> COSConfigModel:
        """获取当前 COS 配置

        Returns:
            COS 配置模型实例
        """
        if self._config is None:
            self._load_config()
        return self._config

    def is_valid(self) -> bool:
        """检查当前配置是否有效

        Returns:
            True 如果配置有效
        """
        return self.validate_config(self.get_config())

    def get_cos_client(self) -> CosS3Client:
        """获取或创建 COS 客户端实例

        使用单例模式，全局复用同一个客户端实例。

        Returns:
            CosS3Client 实例

        Raises:
            COSConfigError: 如果配置无效

        Requirements: 1.2, 1.3, 1.4
        """
        # 验证配置
        if not self.is_valid():
            raise COSConfigError(
                "Invalid COS configuration. Please check your .env file. "
                "Required: COS_SECRET_ID, COS_SECRET_KEY, COS_BUCKET, COS_REGION"
            )

        # 如果客户端已存在，直接返回（单例）
        if self._cos_client is not None:
            return self._cos_client

        # 创建新的客户端实例
        config = self.get_config()
        cos_config = CosConfig(
            Region=config.region,
            SecretId=config.secret_id,
            SecretKey=config.secret_key,
        )
        self._cos_client = CosS3Client(cos_config)

        logger.info("COS client instance created successfully")
        return self._cos_client

    def get_bucket(self) -> str:
        """获取配置的 bucket 名称

        Returns:
            Bucket 名称字符串

        Raises:
            COSConfigError: 如果配置无效
        """
        if not self.is_valid():
            raise COSConfigError(
                "Invalid COS configuration. Please check your .env file."
            )
        return self.get_config().bucket

    def reset(self) -> None:
        """重置配置和客户端（主要用于测试）"""
        self._config = None
        self._cos_client = None
        self._load_config()
        logger.info("COS configuration reset")


# 全局配置服务实例
config_service = COSConfigService()
