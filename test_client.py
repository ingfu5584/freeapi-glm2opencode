import asyncio
from auth import ensure_auth
from zhipu_client import zhipu_client


async def test_client():
    print("=" * 50)
    print("测试智谱 API 客户端")
    print("=" * 50)

    if not await ensure_auth():
        print("登录失败，退出")
        return

    print("\n1. 测试创建对话...")
    try:
        conv_id = await zhipu_client.create_conversation()
        print(f"   对话 ID: {conv_id}")
    except Exception as e:
        print(f"   失败: {e}")
        return

    print("\n2. 测试非流式发送...")
    try:
        messages = [{"role": "user", "content": "你好，请简单介绍一下自己"}]
        response = await zhipu_client.send_message(messages)
        print(f"   响应: {response}")
    except Exception as e:
        print(f"   失败: {e}")

    print("\n3. 测试流式发送...")
    try:
        messages = [{"role": "user", "content": "用一句话解释什么是人工智能"}]
        print("   流式响应: ", end="")
        async for chunk in zhipu_client.send_message_stream(messages):
            if chunk == "[DONE]":
                print("\n   [完成]")
                break
            print(chunk, end="", flush=True)
    except Exception as e:
        print(f"\n   失败: {e}")

    print("\n4. 测试获取对话列表...")
    try:
        conversations = await zhipu_client.get_conversations()
        print(f"   对话数量: {len(conversations)}")
        if conversations:
            print(f"   第一个对话: {conversations[0]}")
    except Exception as e:
        print(f"   失败: {e}")

    await zhipu_client.close()
    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(test_client())
