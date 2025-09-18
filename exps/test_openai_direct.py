"""
直接测试OpenAI API连接
"""

import asyncio
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()


async def test_openai_connection():
    """测试OpenAI API连接"""

    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1/").strip()
    model = os.getenv("LLM_MODEL", "gpt-4o")

    if model == "gpt-4.1":
        model = "gpt-4o"

    print(f"API Key: {api_key[:20]}..." if api_key else "No API Key")
    print(f"Base URL: {base_url}")
    print(f"Model: {model}")

    if not api_key or api_key == "your_api_key_here":
        print("错误: 未配置有效的API key")
        return

    try:
        client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )

        # 测试简单文本消息
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": "Hello, please respond with 'API test successful'"}
            ],
            max_tokens=50
        )

        print(f"✓ API连接成功")
        print(f"响应: {response.choices[0].message.content}")

    except Exception as e:
        print(f"✗ API连接失败: {str(e)}")


if __name__ == "__main__":
    asyncio.run(test_openai_connection())