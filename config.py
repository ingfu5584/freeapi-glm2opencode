import json
from pathlib import Path

BASE_DIR = Path(__file__).parent
TOKEN_STORE_PATH = BASE_DIR / "token_store.json"
BROWSER_DATA_DIR = BASE_DIR / "browser_data"

ZHIPU_BASE_URL = "https://chatglm.cn"
ZHIPU_API_BASE = "https://chatglm.cn/chatglm/mainchat-api"

API_HOST = "127.0.0.1"
API_PORT = 8000

LOGIN_TIMEOUT = 300
LOGIN_CHECK_INTERVAL = 2


def load_token_store() -> dict:
    if TOKEN_STORE_PATH.exists():
        with open(TOKEN_STORE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_token_store(data: dict):
    with open(TOKEN_STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
