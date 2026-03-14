"""
测试连接端点 - 使用新的 /test-api-connection 路径
"""
import requests
import json

url = "http://localhost:4135/api/generation/test-api-connection"
data = {"provider": "tongyi"}

print(f"Testing endpoint: {url}")
print(f"Request data: {json.dumps(data, indent=2)}")

try:
    response = requests.post(url, json=data)
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
except Exception as e:
    print(f"\nError: {e}")
    print(f"Response text: {response.text if 'response' in locals() else 'N/A'}")
