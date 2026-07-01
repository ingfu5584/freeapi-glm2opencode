import httpx
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

BASE = "http://127.0.0.1:8000"

print("测试 /v1/chat/completions (非流式)")
r = httpx.post(
    f"{BASE}/v1/chat/completions",
    json={
        "model": "glm-4",
        "messages": [{"role": "user", "content": "你好"}],
    },
    timeout=120,
)
print(f"Status: {r.status_code}")
data = r.json()
content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
print(f"回复内容: {content}")
