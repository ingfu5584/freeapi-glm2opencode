import asyncio
import json
import base64
import time
import shutil
import sys
import threading
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from config import (
    ZHIPU_BASE_URL,
    BROWSER_DATA_DIR,
    load_token_store,
    save_token_store,
)

stealth = Stealth()


def decode_jwt_payload(token: str) -> dict:
    try:
        parts = token.replace("Bearer ", "").split(".")
        if len(parts) != 3:
            return {}
        payload = parts[1]
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += "=" * padding
        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except Exception:
        return {}


def get_auth_headers() -> dict:
    store = load_token_store()
    if not store:
        return {}

    headers = {}
    cookies = store.get("cookies", [])
    if cookies:
        cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
        headers["Cookie"] = cookie_str

    if store.get("captured_authorization"):
        headers["Authorization"] = store["captured_authorization"]
    else:
        storage = store.get("storage", {})
        ls = storage.get("localStorage", {})
        token = ls.get("token") or ls.get("access_token") or ls.get("chat-token")
        if token:
            if not token.startswith("Bearer "):
                token = f"Bearer {token}"
            headers["Authorization"] = token

    return headers


def is_token_valid() -> bool:
    store = load_token_store()
    if not store:
        return False

    captured_auth = store.get("captured_authorization", "")
    if captured_auth:
        payload = decode_jwt_payload(captured_auth)
        if payload.get("is_guest") == True:
            return False
        exp = payload.get("exp", 0)
        if exp and time.time() >= exp:
            return False
        return True

    storage = store.get("storage", {})
    ls = storage.get("localStorage", {})
    token = ls.get("token") or ls.get("access_token")
    if token:
        payload = decode_jwt_payload(token)
        if payload.get("is_guest") == True:
            return False
        exp = payload.get("exp", 0)
        if exp and time.time() >= exp:
            return False
        return True

    return False


async def launch_browser_login() -> bool:
    if BROWSER_DATA_DIR.exists():
        shutil.rmtree(str(BROWSER_DATA_DIR), ignore_errors=True)
    BROWSER_DATA_DIR.mkdir(parents=True, exist_ok=True)

    captured_token = {"authorization": None}

    async def on_request(request):
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            captured_token["authorization"] = auth_header

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_DATA_DIR),
            headless=False,
            viewport={"width": 1920, "height": 1080},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )

        page = context.pages[0] if context.pages else await context.new_page()
        await stealth.apply_stealth_async(page)
        page.on("request", on_request)

        await page.goto(ZHIPU_BASE_URL, wait_until="domcontentloaded")

        print("=" * 50)
        print("浏览器已打开，请登录智谱清言")
        print("支持扫码登录或手机号登录")
        print("")
        print("登录完成后，请回到这里按回车键")
        print("=" * 50)

        await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)

        await asyncio.sleep(2)

        cookies = await context.cookies()
        storage = await page.evaluate("""
            () => {
                return {
                    localStorage: { ...localStorage },
                    sessionStorage: { ...sessionStorage }
                }
            }
        """)

        auth_data = {
            "cookies": cookies,
            "storage": storage,
            "timestamp": time.time(),
        }

        if captured_token["authorization"]:
            auth_data["captured_authorization"] = captured_token["authorization"]

        save_token_store(auth_data)

        has_auth = bool(captured_token["authorization"])
        print(f"Authorization 抓取: {'成功' if has_auth else '未抓取到'}")

        await context.close()

        if has_auth:
            payload = decode_jwt_payload(captured_token["authorization"])
            if payload.get("is_guest") == True:
                print("警告: 当前仍是游客账号，请确认是否真的登录了")
                return False

        if not has_auth and not any(
            c for c in cookies if c.get("name") in ["chatglm_token", "token"]
        ):
            print("警告: 未检测到有效登录凭证")
            return False

        print("登录数据已保存！")
        return True


async def ensure_auth() -> bool:
    if is_token_valid():
        print("已有有效登录，跳过登录流程")
        return True

    print("未检测到有效登录，需要登录...")
    return await launch_browser_login()


async def re_auth():
    print("Token 已失效，需要重新登录...")
    return await launch_browser_login()
