"""
调试认证问题的测试脚本
"""
import sys
sys.path.insert(0, ".")

from core.security import decode_token, create_access_token
from database import get_db
from models.user import User

def test_token_generation():
    """测试 token 生成"""
    print("=" * 60)
    print("测试 Token 生成")
    print("=" * 60)

    # 创建一个测试 token
    test_data = {"sub": "testuser"}
    token = create_access_token(test_data, expires_minutes=43200)

    print(f"\n生成的 Token:")
    print(token)
    print(f"\nToken 长度: {len(token)}")

    # 尝试解码
    try:
        payload = decode_token(token)
        print(f"\n解码成功!")
        print(f"Payload: {payload}")
    except Exception as e:
        print(f"\n解码失败: {e}")

def test_existing_user_token():
    """测试现有用户的 token"""
    print("\n" + "=" * 60)
    print("测试现有用户 Token")
    print("=" * 60)

    db = next(get_db())

    # 获取第一个用户
    user = db.query(User).first()

    if not user:
        print("\n数据库中没有用户")
        return

    print(f"\n找到用户: {user.username} (ID: {user.id})")

    # 为这个用户生成 token
    token = create_access_token({"sub": user.username}, expires_minutes=43200)

    print(f"\n为用户 {user.username} 生成的 Token:")
    print(token)
    print(f"\nToken 长度: {len(token)}")

    # 测试解码
    try:
        payload = decode_token(token)
        print(f"\n解码成功!")
        print(f"Username from token: {payload.get('sub')}")
        print(f"Expires at: {payload.get('exp')}")
    except Exception as e:
        print(f"\n解码失败: {e}")

    print("\n" + "=" * 60)
    print("测试建议:")
    print("=" * 60)
    print("1. 复制上面的 token")
    print("2. 在浏览器控制台执行:")
    print(f"   localStorage.setItem('token', JSON.stringify('{token}'))")
    print("3. 刷新页面")
    print("4. 尝试生成图片")

if __name__ == "__main__":
    test_token_generation()
    test_existing_user_token()
