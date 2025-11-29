class AiClient:
    """AI 绘图客户端抽象。

    建议封装不同模型/供应商（通义、豆包、SD 等）以统一调用接口。
    """

    def generate(self, prompt: str, negative_prompt: str | None = None):
        """根据提示词生成图片并返回路径或二进制数据。"""
        raise NotImplementedError
