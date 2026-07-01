import uvicorn
from main import app
from config import API_HOST, API_PORT

if __name__ == "__main__":
    print(f"正在启动智谱清言反向代理...")
    print(f"服务地址: http://{API_HOST}:{API_PORT}")
    print(f"API 文档: http://{API_HOST}:{API_PORT}/docs")
    print(f"\n使用方式 (Agent 配置):")
    print(f'  base_url: http://{API_HOST}:{API_PORT}/v1')
    print(f'  api_key: anything')
    print(f"\n浏览器将自动打开，请先登录智谱清言")
    print("-" * 50)

    uvicorn.run(app, host=API_HOST, port=API_PORT)
