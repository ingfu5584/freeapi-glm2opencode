import asyncio
import json
import sys
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from config import BROWSER_DATA_DIR, ZHIPU_BASE_URL

sys.stdout.reconfigure(encoding='utf-8')
stealth = Stealth()


async def main():
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_DATA_DIR),
            headless=False,
            viewport={"width": 1920, "height": 1080},
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await stealth.apply_stealth_async(page)
        await page.goto(ZHIPU_BASE_URL, wait_until="networkidle")
        await asyncio.sleep(3)

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

        print("在浏览器中调用 fetch API...")
        result = await page.evaluate("""
            async (payload) => {
                try {
                    const resp = await fetch('https://chatglm.cn/chatglm/backend-api/assistant/stream', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json;charset=UTF-8' },
                        body: JSON.stringify(payload),
                    });
                    const text = await resp.text();
                    return { status: resp.status, body: text.substring(0, 2000) };
                } catch (e) {
                    return { error: e.message };
                }
            }
        """, payload)

        print(f"Result: {json.dumps(result, ensure_ascii=False, indent=2)}")
        await context.close()


asyncio.run(main())
