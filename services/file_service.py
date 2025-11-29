class FileService:
    """文件存储服务抽象。

    可实现本地存储或接入 OSS/云存储，统一文件读写接口。
    """

    def save_image(self, data: bytes, filename: str):
        """保存图片数据并返回可访问的 URL 或路径。"""
        raise NotImplementedError
