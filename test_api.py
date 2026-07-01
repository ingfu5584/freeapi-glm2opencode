import httpx
import json

BASE = "http://127.0.0.1:8000"

print("1. 测试 /v1/models")
r = httpx.get(f"{BASE}/v1/models")
print(f"   Status: {r.status_code}")
print(f"   Response: {r.json()}")

print("\n2. 测试 /v1/chat/completions (非流式)")
r = httpx.post(
    f"{BASE}/v1/chat/completions",
    json={
        "model": "glm-4",
        "messages": [{"role": "user", "content": "你好，用一句话回答"}],
    },
    timeout=60,
)
print(f"   Status: {r.status_code}")
print(f"   Response text: {r.text[:500]}")
