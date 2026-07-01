import asyncio
import json
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from config import BROWSER_DATA_DIR, ZHIPU_BASE_URL

stealth = Stealth()

async def main():
    BROWSER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    captured = []

    async def on_request(request):
        method = request.method
        url = request.url
        if method == "POST" and ("mainchat" in url or "chat" in url or "message" in url or "send" in url):
            captured.append({
                "method": method,
                "url": url,
                "headers": dict(request.headers),
                "body": request.post_data,
            })

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_DATA_DIR),
            headless=False,
            viewport={"width": 1920, "height": 1080},
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await stealth.apply_stealth_async(page)
        page.on("request", on_request)

        await page.goto(ZHIPU_BASE_URL, wait_until="networkidle")

        print("=" * 60)
        print("请在浏览器中发送一条消息（比如'你好'）")
        print("等回复完成后，回到这里按回车")
        print("=" * 60)

        await asyncio.get_event_loop().run_in_executor(None, input)

        print(f"\n捕获到 {len(captured)} 个 POST 请求:\n")
        for i, req in enumerate(captured, 1):
            print(f"--- Request {i} ---")
            print(f"URL: {req['url']}")
            print(f"Body: {req['body'][:500] if req['body'] else 'None'}")
            print()

        await context.close()

asyncio.run(main())
