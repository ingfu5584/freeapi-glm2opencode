import asyncio
import json
from playwright.async_api import async_playwright
from config import BROWSER_DATA_DIR, ZHIPU_BASE_URL


async def capture_message_api():
    BROWSER_DATA_DIR.mkdir(parents=True, exist_ok=True)

    captured_requests = []

    async def handle_request(request):
        url = request.url
        if "mainchat" in url or "sse" in url or "message" in url:
            req_data = {
                "method": request.method,
                "url": url,
                "headers": dict(request.headers),
                "post_data": request.post_data,
            }
            captured_requests.append(req_data)
            print(f"\n{'='*60}")
            print(f"[REQUEST] {request.method} {url}")
            if request.post_data:
                print(f"Body: {request.post_data}")

    async def handle_response(response):
        url = response.url
        if "mainchat" in url or "sse" in url or "message" in url:
            print(f"\n[RESPONSE] {response.status} {url}")
            try:
                body = await response.text()
                print(f"Body: {body[:2000]}")
            except:
                pass

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_DATA_DIR),
            headless=False,
            viewport={"width": 1280, "height": 800},
        )

        page = context.pages[0] if context.pages else await context.new_page()

        page.on("request", handle_request)
        page.on("response", handle_response)

        await page.goto(ZHIPU_BASE_URL, wait_until="networkidle")

        print("=" * 60)
        print("步骤:")
        print("1. 请先在浏览器中登录你的智谱清言账号")
        print("2. 登录成功后，在输入框输入 '你好' 并发送")
        print("3. 等待回复完成后按 Ctrl+C 退出")
        print("=" * 60)

        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass

        print("\n\n" + "=" * 60)
        print(f"共捕获 {len(captured_requests)} 个请求")
        print("=" * 60)

        for i, req in enumerate(captured_requests, 1):
            print(f"\n--- Request {i} ---")
            print(f"Method: {req['method']}")
            print(f"URL: {req['url']}")
            if req['post_data']:
                print(f"Body: {req['post_data']}")
            print("Key Headers:")
            for key in ['authorization', 'content-type', 'x-sign', 'x-timestamp', 'x-nonce', 'x-device-id', 'x-exp-groups', 'x-request-id']:
                if key in req['headers']:
                    print(f"  {key}: {req['headers'][key][:200]}")

        await context.close()


if __name__ == "__main__":
    asyncio.run(capture_message_api())
