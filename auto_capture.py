import asyncio
import json
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from config import BROWSER_DATA_DIR, ZHIPU_BASE_URL

stealth = Stealth()


async def main():
    captured = []

    async def on_request(request):
        if request.method == "POST" and "chatglm" in request.url:
            captured.append({
                "url": request.url,
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
        await asyncio.sleep(3)

        print("自动发送消息...")
        textarea = await page.query_selector("textarea")
        if textarea:
            await textarea.click()
            await textarea.fill("你好")
            await asyncio.sleep(0.5)
            await page.keyboard.press("Enter")
            print("消息已发送，等待回复...")
            await asyncio.sleep(15)
        else:
            print("找不到输入框")

        await context.close()

    print(f"\n捕获到 {len(captured)} 个 POST 请求:\n")
    for i, req in enumerate(captured, 1):
        url = req["url"]
        if "track" in url or "operation" in url or "feed" in url:
            continue
        print(f"--- Request {i} ---")
        print(f"URL: {url}")
        auth = req["headers"].get("authorization", "")
        if auth:
            print(f"Auth: {auth[:80]}...")
        if req["body"]:
            try:
                body = json.loads(req["body"])
                print(f"Body: {json.dumps(body, ensure_ascii=False, indent=2)[:500]}")
            except:
                print(f"Body: {req['body'][:300]}")
        print()


asyncio.run(main())
