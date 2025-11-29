class WechatService:
    """微信开放平台服务占位。

    负责与微信接口交互（扫码登录、用户信息、token 刷新等）。
    实际实现需配置 appid/secret 并处理回调。
    """

    def exchange_code(self, code: str):
        """用临时 code 换取 access_token 与用户标识。"""
        raise NotImplementedError
