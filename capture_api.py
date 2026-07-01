import asyncio
import json
from playwright.async_api import async_playwright
from config import BROWSER_DATA_DIR, ZHIPU_BASE_URL


async def capture_api_calls():
    BROWSER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    captured_requests = []

    async def handle_request(request):
        url = request.url
        if "backend-api" in url or "api" in url:
            captured_requests.append({
                "method": request.method,
                "url": url,
                "headers": dict(request.headers),
                "post_data": request.post_data,
            })
            print(f"\n[请求] {request.method} {url}")
            if request.post_data:
                print(f"  Body: {request.post_data[:200]}")

    async def handle_response(response):
        url = response.url
        if "backend-api" in url or "api" in url:
            print(f"\n[响应] {response.status} {url}")
            try:
                body = await response.text()
                print(f"  Body: {body[:300]}")
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
        print("浏览器已打开，请在页面中发送一条消息")
        print("程序会捕获所有 API 请求")
        print("按 Ctrl+C 退出")
        print("=" * 60)

        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass

        print("\n\n" + "=" * 60)
        print("捕获到的 API 请求汇总:")
        print("=" * 60)
        
        for i, req in enumerate(captured_requests, 1):
            print(f"\n--- 请求 {i} ---")
            print(f"Method: {req['method']}")
            print(f"URL: {req['url']}")
            if req['post_data']:
                print(f"Body: {req['post_data']}")
            print(f"Headers: {json.dumps(req['headers'], indent=2, ensure_ascii=False)}")

        await context.close()


if __name__ == "__main__":
    asyncio.run(capture_api_calls())
