import asyncio
import json
import sys
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from config import BROWSER_DATA_DIR, ZHIPU_BASE_URL

sys.stdout.reconfigure(encoding='utf-8')
stealth = Stealth()


async def main():
    captured_req = None
    captured_resp = None

    async def on_request(request):
        nonlocal captured_req
        if "assistant/stream" in request.url:
            captured_req = {
                "url": request.url,
                "method": request.method,
                "headers": dict(request.headers),
                "body": request.post_data,
            }

    async def on_response(response):
        nonlocal captured_resp
        if "assistant/stream" in response.url:
            try:
                body = await response.text()
                captured_resp = {"status": response.status, "body": body[:2000]}
            except:
                pass

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_DATA_DIR),
            headless=False,
            viewport={"width": 1920, "height": 1080},
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await stealth.apply_stealth_async(page)
        page.on("request", on_request)
        page.on("response", on_response)
        await page.goto(ZHIPU_BASE_URL, wait_until="networkidle")
        await asyncio.sleep(3)

        print("发送消息...")
        textarea = await page.query_selector("textarea")
        if textarea:
            await textarea.click()
            await textarea.fill("你好，用一句话回答")
            await asyncio.sleep(0.5)
            await page.keyboard.press("Enter")
            await asyncio.sleep(15)

        await context.close()

    if captured_req:
        print("\n=== 实际请求 ===")
        print(f"URL: {captured_req['url']}")
        print(f"Headers:")
        for k, v in captured_req['headers'].items():
            if k.startswith('x-') or k == 'authorization' or k == 'cookie':
                print(f"  {k}: {v[:100]}...")
        print(f"\nBody (完整):")
        body = json.loads(captured_req['body'])
        print(json.dumps(body, ensure_ascii=False, indent=2))

    if captured_resp:
        print(f"\n=== 实际响应 ===")
        print(f"Status: {captured_resp['status']}")
        print(f"Body: {captured_resp['body']}")


asyncio.run(main())
