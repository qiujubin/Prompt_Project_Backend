"""
ComfyUI Integration Configuration
"""
from typing import Optional
from pydantic import BaseModel, Field
import os
from dotenv import load_dotenv

load_dotenv()


class ComfyUISettings(BaseModel):
    """ComfyUI 连接配置"""

    # 基础连接配置
    host: str = Field(default="127.0.0.1", description="ComfyUI 服务器地址")
    port: int = Field(default=8188, description="ComfyUI 服务器端口")
    protocol: str = Field(default="http", description="协议类型 (http/https)")

    # WebSocket 配置
    websocket_path: str = Field(default="/ws", description="WebSocket 路径")

    # HTTP API 配置
    api_path: str = Field(default="/api", description="HTTP API 路径")

    # 连接超时配置
    connect_timeout: int = Field(default=30, description="连接超时时间（秒）")
    request_timeout: int = Field(default=300, description="请求超时时间（秒）")

    # 重试配置
    max_retry_attempts: int = Field(default=3, description="最大重试次数")
    retry_delay: float = Field(default=1.0, description="重试延迟（秒）")
    retry_max_delay: float = Field(default=30.0, description="最大重试延迟（秒）")
    retry_exponential_base: float = Field(default=2.0, description="指数退避基数")

    # 队列配置
    max_queue_size: int = Field(default=100, description="最大队列大小")
    task_timeout: int = Field(default=600, description="任务超时时间（秒）")
    cleanup_interval: int = Field(default=300, description="任务清理间隔（秒）")

    # 连接池配置
    pool_size: int = Field(default=5, description="WebSocket 连接池大小")
    pool_max_idle_time: int = Field(default=300, description="连接最大空闲时间（秒）")
    pool_health_check_interval: int = Field(default=60, description="连接健康检查间隔（秒）")

    # HTTP 客户端池配置
    http_pool_size: int = Field(default=10, description="HTTP 连接池大小")
    http_keepalive_expiry: int = Field(default=30, description="HTTP Keep-Alive 过期时间（秒）")

    @property
    def base_url(self) -> str:
        """获取基础 URL"""
        return f"{self.protocol}://{self.host}:{self.port}"

    @property
    def websocket_url(self) -> str:
        """获取 WebSocket URL"""
        ws_protocol = "wss" if self.protocol == "https" else "ws"
        return f"{ws_protocol}://{self.host}:{self.port}{self.websocket_path}"

    @property
    def api_url(self) -> str:
        """获取 API URL"""
        return f"{self.base_url}{self.api_path}"


class ComfyUIWorkflowSettings(BaseModel):
    """ComfyUI 工作流配置"""

    # 默认工作流模板路径
    default_workflow_path: str = Field(
        default="workflows/default_txt2img.json",
        description="默认工作流模板路径"
    )

    # 自定义工作流目录
    custom_workflows_dir: str = Field(
        default="workflows/custom",
        description="自定义工作流目录"
    )

    # 工作流验证
    validate_workflow: bool = Field(default=True, description="是否验证工作流")

    # 默认生成参数
    default_width: int = Field(default=512, description="默认图像宽度")
    default_height: int = Field(default=512, description="默认图像高度")
    default_steps: int = Field(default=20, description="默认采样步数")
    default_cfg: float = Field(default=7.0, description="默认 CFG 值")
    default_sampler: str = Field(default="euler", description="默认采样器")
    default_scheduler: str = Field(default="normal", description="默认调度器")


class ComfyUIStorageSettings(BaseModel):
    """ComfyUI 存储配置"""

    # 图像存储路径
    output_dir: str = Field(default="static/comfyui_outputs", description="输出图像目录")

    # 临时文件路径
    temp_dir: str = Field(default="temp/comfyui", description="临时文件目录")

    # 文件命名格式
    filename_format: str = Field(
        default="{timestamp}_{prompt_id}_{node_id}.png",
        description="文件命名格式"
    )

    # 存储限制
    max_file_size: int = Field(default=50 * 1024 * 1024, description="最大文件大小（字节）")
    max_files_per_user: int = Field(default=1000, description="每用户最大文件数")

    # 清理配置
    auto_cleanup: bool = Field(default=True, description="是否自动清理")
    cleanup_interval: int = Field(default=24 * 3600, description="清理间隔（秒）")
    max_age: int = Field(default=7 * 24 * 3600, description="文件最大保存时间（秒）")


# 全局配置实例
comfyui_settings = ComfyUISettings(
    host=os.getenv("COMFYUI_HOST", "127.0.0.1"),
    port=int(os.getenv("COMFYUI_PORT", "8188")),
    protocol=os.getenv("COMFYUI_PROTOCOL", "http"),
    connect_timeout=int(os.getenv("COMFYUI_CONNECT_TIMEOUT", "30")),
    request_timeout=int(os.getenv("COMFYUI_REQUEST_TIMEOUT", "300")),
    max_retry_attempts=int(os.getenv("COMFYUI_MAX_RETRY", "3")),
    pool_size=int(os.getenv("COMFYUI_POOL_SIZE", "5")),
    http_pool_size=int(os.getenv("COMFYUI_HTTP_POOL_SIZE", "10")),
)

workflow_settings = ComfyUIWorkflowSettings()
storage_settings = ComfyUIStorageSettings()


def get_comfyui_settings() -> ComfyUISettings:
    """获取 ComfyUI 设置"""
    return comfyui_settings


def get_workflow_settings() -> ComfyUIWorkflowSettings:
    """获取工作流设置"""
    return workflow_settings


def get_storage_settings() -> ComfyUIStorageSettings:
    """获取存储设置"""
    return storage_settings
