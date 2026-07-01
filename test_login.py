import asyncio
from auth import ensure_auth, get_auth_headers, is_token_valid


async def test_login():
    print("=" * 60)
    print("测试登录流程")
    print("=" * 60)

    print(f"\n当前登录状态: {is_token_valid()}")

    if await ensure_auth():
        print("\n登录成功！")
        headers = get_auth_headers()
        print(f"\n获取到的 Headers:")
        for key, value in headers.items():
            if key == "Cookie":
                print(f"  {key}: {value[:100]}...")
            else:
                print(f"  {key}: {value}")
    else:
        print("\n登录失败")


if __name__ == "__main__":
    asyncio.run(test_login())
