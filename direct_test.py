import httpx
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

store = json.load(open('token_store.json', 'r', encoding='utf-8'))
auth = store.get('captured_authorization', '')

headers = {
    "Authorization": auth,
    "Content-Type": "application/json;charset=UTF-8",
    "Origin": "https://chatglm.cn",
    "Referer": "https://chatglm.cn/main/alltoolschat",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

payload = {
    "assistant_id": "65940acff94777010aa6b796",
    "conversation_id": "",
    "project_id": "",
    "chat_type": "user_chat",
    "meta_data": {
        "cogview": {"rm_label_watermark": False},
        "is_test": False,
        "input_question_type": "xxxx",
        "channel": "",
        "draft_id": "",
        "chat_mode": "thinking",
        "is_networking": True,
        "quote_log_id": "",
        "platform": "pc",
    },
    "messages": [
        {
            "role": "user",
            "content": [{"type": "text", "text": "你好"}],
        }
    ],
}

print(f"URL: https://chatglm.cn/chatglm/backend-api/assistant/stream")
print(f"Auth: {auth[:80]}...")
print(f"Payload: {json.dumps(payload, ensure_ascii=False)[:300]}")
print()

resp = httpx.post(
    "https://chatglm.cn/chatglm/backend-api/assistant/stream",
    headers=headers,
    json=payload,
    timeout=30,
)
print(f"Status: {resp.status_code}")
print(f"Response: {resp.text[:500]}")
