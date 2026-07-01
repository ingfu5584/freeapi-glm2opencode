import asyncio
import json
import sys
from mitmproxy import options
from mitmproxy.tools.dump import DumpMaster
from mitmproxy import http

captured = []

class CaptureAddon:
    def request(self, flow: http.HTTPFlow):
        url = flow.request.pretty_url
        if "chatglm" in url and flow.request.method == "POST":
            body = flow.request.get_text()
            headers = dict(flow.request.headers)
            captured.append({
                "url": url,
                "method": "POST",
                "body": body[:1000] if body else None,
                "auth": headers.get("authorization", ""),
            })
            print(f"\n[CAPTURED] POST {url}")
            if body:
                print(f"  Body: {body[:200]}")

async def start_proxy():
    opts = options.Options(listen_port=8080)
    m = DumpMaster(opts)
    m.addons.add(CaptureAddon())
    
    print("=" * 60)
    print("代理已启动: 127.0.0.1:8080")
    print("")
    print("请在你的浏览器中设置代理:")
    print("  地址: 127.0.0.1  端口: 8080")
    print("")
    print("然后打开 chatglm.cn，登录，发一条消息")
    print("发完消息后按 Ctrl+C 退出")
    print("=" * 60)
    
    try:
        await m.run()
    except KeyboardInterrupt:
        pass
    
    print(f"\n\n捕获到 {len(captured)} 个请求:")
    for i, req in enumerate(captured, 1):
        print(f"\n--- {i} ---")
        print(f"URL: {req['url']}")
        print(f"Auth: {req['auth'][:100]}...")
        if req['body']:
            print(f"Body: {req['body']}")

if __name__ == "__main__":
    asyncio.run(start_proxy())
