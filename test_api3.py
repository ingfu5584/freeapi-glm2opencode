import httpx
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

BASE = "http://127.0.0.1:8000"

print("1. 测试普通对话")
r = httpx.post(
    f"{BASE}/v1/chat/completions",
    json={
        "model": "glm-4",
        "messages": [{"role": "user", "content": "你好，用一句话回答"}],
    },
    timeout=120,
)
print(f"   Status: {r.status_code}")
data = r.json()
content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
print(f"   回复: {content}")

print("\n2. 测试工具调用")
r = httpx.post(
    f"{BASE}/v1/chat/completions",
    json={
        "model": "glm-4",
        "messages": [{"role": "user", "content": "帮我查看当前目录的文件列表"}],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "bash",
                    "description": "执行 bash 命令",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "要执行的命令"}
                        },
                        "required": ["command"]
                    }
                }
            }
        ]
    },
    timeout=120,
)
print(f"   Status: {r.status_code}")
data = r.json()
msg = data.get("choices", [{}])[0].get("message", {})
print(f"   Content: {msg.get('content', 'None')}")
print(f"   Tool Calls: {json.dumps(msg.get('tool_calls', []), ensure_ascii=False, indent=2)}")
print(f"   Finish Reason: {data.get('choices', [{}])[0].get('finish_reason', '')}")
