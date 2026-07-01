import json
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse

from auth import ensure_auth
from zhipu_client import zhipu_client
from converter import (
    openai_to_zhipu_messages,
    zhipu_to_openai_response,
    zhipu_to_openai_stream_chunk,
    create_stream_end_chunk,
    parse_tool_calls,
    clean_response_text,
    generate_id,
)
from config import API_HOST, API_PORT


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_auth()
    await zhipu_client.start()
    yield
    await zhipu_client.stop()


app = FastAPI(title="智谱清言反向代理", version="1.0.0", lifespan=lifespan)


@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {"id": "glm-4", "object": "model"},
            {"id": "glm-4-flash", "object": "model"},
            {"id": "glm-4-long", "object": "model"},
            {"id": "glm-5", "object": "model"},
        ],
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
    model = body.get("model", "glm-4")
    stream = body.get("stream", False)
    tools = body.get("tools", None)

    zhipu_messages = openai_to_zhipu_messages(messages, tools)

    if stream:
        async def stream_generator():
            stream_id = generate_id()
            created_time = int(time.time())
            full_text = ""

            # send_message_stream 内部会等待完整响应，所以这里拿到的是完整文本
            async for chunk in zhipu_client.send_message_stream(zhipu_messages, model, tools=tools):
                if chunk.get("done"):
                    break
                openai_chunk = zhipu_to_openai_stream_chunk(chunk, model, stream_id, created_time)
                if openai_chunk:
                    content = openai_chunk["choices"][0]["delta"].get("content", "")
                    if content:
                        full_text += content

            # 始终尝试解析工具调用（支持裸JSON、```tool_call块、tool_call行三种格式）
            tool_calls = parse_tool_calls(full_text)

            if tool_calls:
                # 有工具调用：清理文本中的工具调用部分，发送剩余内容
                clean_content = clean_response_text(full_text)
                if clean_content:
                    content_chunk = zhipu_to_openai_stream_chunk(
                        {"result": {"content": clean_content}},
                        model, stream_id, created_time
                    )
                    if content_chunk:
                        yield f"data: {json.dumps(content_chunk, ensure_ascii=False)}\n\n"
                # 发送工具调用结束块
                end_chunk = create_stream_end_chunk(model, stream_id, created_time, tool_calls)
            else:
                # 无工具调用：发送完整文本
                if full_text:
                    content_chunk = zhipu_to_openai_stream_chunk(
                        {"result": {"content": full_text}},
                        model, stream_id, created_time
                    )
                    if content_chunk:
                        yield f"data: {json.dumps(content_chunk, ensure_ascii=False)}\n\n"
                end_chunk = create_stream_end_chunk(model, stream_id, created_time, None)

            yield f"data: {json.dumps(end_chunk, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(stream_generator(), media_type="text/event-stream")
    else:
        try:
            response = await zhipu_client.send_message(zhipu_messages, model, tools=tools)
            openai_response = zhipu_to_openai_response(response, model)
            return JSONResponse(content=openai_response)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JSONResponse(
                status_code=500,
                content={"error": {"message": str(e), "type": "server_error"}},
            )


@app.get("/health")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT)
