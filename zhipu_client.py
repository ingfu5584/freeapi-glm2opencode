import asyncio
import json
import time
from typing import AsyncGenerator, Optional
from playwright.async_api import async_playwright, Page, BrowserContext
from playwright_stealth import Stealth
from config import ZHIPU_BASE_URL, BROWSER_DATA_DIR
from system_prompt import SYSTEM_PROMPT, SIMPLE_TOOL_PROMPT, format_tools_for_prompt

stealth = Stealth()


class ZhipuClient:
    def __init__(self):
        self.playwright = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._lock = asyncio.Lock()
        self._last_response = None
        self._response_event = None
        self._initialized = False
        self._msg_count = 0

    async def start(self):
        if self.page and not self.page.is_closed():
            try:
                await self.page.evaluate("1")
                return
            except Exception:
                await self._cleanup()

        self.playwright = await async_playwright().start()
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_DATA_DIR),
            headless=False,
            viewport={"width": 1920, "height": 1080},
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
        await stealth.apply_stealth_async(self.page)
        self.page.on("response", self._on_response)
        await self.page.goto(ZHIPU_BASE_URL, wait_until="networkidle")
        await asyncio.sleep(2)
        print("浏览器已启动，正在发送系统提示词...")
        await self._send_system_prompt()

    async def _on_response(self, response):
        url = response.url
        if "assistant/stream" in url:
            try:
                body = await response.text()
                if len(body) > 100:
                    print(f"[DEBUG] AI响应捕获，长度: {len(body)}")
                    self._last_response = body
                    if self._response_event:
                        self._response_event.set()
            except Exception:
                pass

    async def _cleanup(self):
        try:
            if self.context:
                await self.context.close()
        except Exception:
            pass
        try:
            if self.playwright:
                await self.playwright.stop()
        except Exception:
            pass
        self.page = None
        self.context = None
        self.playwright = None

    async def stop(self):
        await self._cleanup()

    def _format_history(self, messages: list) -> str:
        """将 opencode 的 messages 数组格式化为历史记录文本"""
        parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if not content:
                continue

            if role == "system":
                parts.append(f"[系统] {content}")
            elif role == "user":
                parts.append(f"用户: {content}")
            elif role == "assistant":
                parts.append(f"助手: {content}")
            elif role == "tool":
                tool_call_id = msg.get("tool_call_id", "")
                parts.append(f"[工具调用结果] {content}")

        return "\n\n".join(parts)

    def _save_history_to_file(self, history: str) -> str:
        """将历史记录保存到 txt 文件"""
        import os
        work_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(work_dir, "chat_history.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(history)

        return file_path

    async def _send_system_prompt(self):
        print("正在发送系统提示词...")
        await asyncio.sleep(3)

        input_box = await self._find_input_box()
        if not input_box:
            print("找不到输入框，跳过系统提示词")
            return

        self._last_response = None
        self._response_event = asyncio.Event()

        await input_box.click()
        await input_box.fill("")
        await asyncio.sleep(0.5)
        await input_box.fill(SYSTEM_PROMPT)
        await asyncio.sleep(1)

        send_btn = await self._find_send_button()
        if send_btn:
            await send_btn.click()
        else:
            await self.page.keyboard.press("Enter")

        print("系统提示词已发送，等待AI处理...")
        try:
            await asyncio.wait_for(self._response_event.wait(), timeout=600)
        except asyncio.TimeoutError:
            print("等待系统提示词响应超时，继续...")
        await asyncio.sleep(5)

        self._last_response = None
        self._response_event = None
        print("系统提示词处理完成，已丢弃首次响应")

    async def _ensure_page(self):
        if not self.page or self.page.is_closed():
            await self.start()
            return
        try:
            await self.page.evaluate("1")
        except Exception:
            await self.start()

    async def _find_input_box(self):
        selectors = ["textarea", "[contenteditable='true']"]
        for sel in selectors:
            try:
                el = await self.page.query_selector(sel)
                if el and await el.is_visible():
                    return el
            except Exception:
                continue
        return None

    async def _find_send_button(self):
        selectors = [
            "button[class*='send']",
            "button[class*='Send']",
            "[class*='send']",
        ]
        for sel in selectors:
            try:
                el = await self.page.query_selector(sel)
                if el and await el.is_visible():
                    return el
            except Exception:
                continue
        return None

    def _parse_sse_response(self, text: str) -> str:
        last_text = ""
        for line in text.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith(":"):
                continue
            if line.startswith("data: "):
                data = line[6:]
                if data == "[DONE]":
                    continue
                try:
                    obj = json.loads(data)
                    parts = obj.get("parts", [])
                    for part in parts:
                        for content in part.get("content", []):
                            content_type = content.get("type", "")
                            if content_type == "text":
                                text_val = content.get("text", "")
                                if text_val:
                                    last_text = text_val
                except json.JSONDecodeError:
                    pass
        return last_text

    async def send_message(self, messages: list, model: str = "glm-4", tools: list = None) -> dict:
        async with self._lock:
            await self._ensure_page()

            user_msg = ""
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    user_msg = msg.get("content", "")
                    break

            if not user_msg:
                return {"result": {"content": "没有找到用户消息"}}

            self._msg_count += 1

            # 根据tools参数生成工具提示词
            if tools:
                tool_hint = "\n\n##可用工具列表：\n"
                for tool in tools:
                    func = tool.get("function", {})
                    name = func.get("name", "")
                    desc = func.get("description", "")
                    params = func.get("parameters", {})
                    tool_hint += f"\n### {name}\n描述: {desc}\n"
                    if params:
                        props = params.get("properties", {})
                        required = params.get("required", [])
                        for pname, pinfo in props.items():
                            req = " (必填)" if pname in required else " (可选)"
                            tool_hint += f"  - {pname}: {pinfo.get('description', '')}{req}\n"
                tool_hint += "\n##如需调用工具，请输出完整json格式调用请求，如{\n  \"name\": \"read\",\n  \"arguments\": {\n    \"filePath\": \"test.txt\"\n  }\n}"
            else:
                tool_hint = '\n\n##如需调用工具，请输出完整json格式调用请求，如{\n  "name": "read",\n  "arguments": {\n    "filePath": "test.txt"\n  }\n}'

            if not self._initialized:
                history = self._format_history(messages)

                full_msg = SYSTEM_PROMPT
                if history:
                    file_path = self._save_history_to_file(history)
                    full_msg += f"\n\n请先读取文件 {file_path} 了解之前的对话历史。"
                full_msg += f"\n\n当前用户请求：{user_msg}{tool_hint}"

                self._initialized = True
                print(f"[DEBUG] 首次请求，消息总数: {len(messages)}")
                print(f"[DEBUG] 历史记录已保存到文件")
            else:
                full_msg = f"{user_msg}{tool_hint}"

            self._last_response = None
            self._response_event = asyncio.Event()

            input_box = await self._find_input_box()
            if not input_box:
                return {"result": {"content": "找不到输入框"}}

            await input_box.click()
            await input_box.fill("")
            await asyncio.sleep(0.3)
            await input_box.fill(full_msg)
            await asyncio.sleep(0.5)

            send_btn = await self._find_send_button()
            if send_btn:
                await send_btn.click()
            else:
                await self.page.keyboard.press("Enter")

            try:
                await asyncio.wait_for(self._response_event.wait(), timeout=600)

                stable_count = 0
                last_len = 0
                max_wait = 600
                waited = 0
                while stable_count < 5 and waited < max_wait:
                    await asyncio.sleep(1)
                    waited += 1
                    current_len = len(self._last_response or "")
                    if current_len == last_len:
                        stable_count += 1
                    else:
                        stable_count = 0
                    last_len = current_len

                if self._last_response:
                    content = self._parse_sse_response(self._last_response)
                    return {"result": {"content": content}}
                else:
                    return {"result": {"content": "未收到响应"}}
            except asyncio.TimeoutError:
                if self._last_response:
                    content = self._parse_sse_response(self._last_response)
                    return {"result": {"content": content}}
                return {"result": {"content": "响应超时（5分钟）"}}

            return {"result": {"content": "未收到响应"}}

    async def send_message_stream(self, messages: list, model: str = "glm-4", tools: list = None) -> AsyncGenerator[dict, None]:
        result = await self.send_message(messages, model, tools=tools)
        content = result.get("result", {}).get("content", "")
        if content:
            yield {"result": {"content": content}}
        yield {"done": True}

    async def get_conversations(self) -> list:
        return []


zhipu_client = ZhipuClient()
