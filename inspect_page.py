import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from config import BROWSER_DATA_DIR, ZHIPU_BASE_URL

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

        print("页面加载完成，等待5秒后自动发送消息...")
        await asyncio.sleep(5)

        # 自动发送消息
        input_box = await page.query_selector("textarea")
        if input_box:
            await input_box.click()
            await input_box.fill("你好")
            await asyncio.sleep(0.5)
            await page.keyboard.press("Enter")
            print("消息已发送，等待回复...")
            await asyncio.sleep(15)
        else:
            print("找不到输入框")

        # 获取页面结构
        html = await page.evaluate("""
            () => {
                const results = [];
                const selectors = [
                    '[class*="message"]',
                    '[class*="answer"]',
                    '[class*="response"]',
                    '[class*="markdown"]',
                    '[class*="content"]',
                    '[class*="bot"]',
                    '[class*="assistant"]',
                    '[class*="chat"]',
                    '[class*="think"]',
                    '[class*="Think"]',
                ];
                for (const sel of selectors) {
                    const els = document.querySelectorAll(sel);
                    els.forEach((el, i) => {
                        if (el.textContent && el.textContent.trim().length > 10) {
                            results.push({
                                selector: sel,
                                index: i,
                                className: el.className,
                                tagName: el.tagName,
                                textLength: el.textContent.trim().length,
                                text: el.textContent.trim().substring(0, 300),
                            });
                        }
                    });
                }
                return results;
            }
        """)

        print(f"\n找到 {len(html)} 个元素:\n")
        for item in html:
            print(f"Selector: {item['selector']}")
            print(f"  Tag: {item['tagName']}, Class: {item['className']}")
            print(f"  Text length: {item['textLength']}")
            print(f"  Text: {item['text'][:150]}...")
            print()

        await context.close()

asyncio.run(main())
