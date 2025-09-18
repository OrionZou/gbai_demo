"""
测试简单的文本聊天API调用
"""

import asyncio
import os
from dotenv import load_dotenv
import httpx

from agent_runtime.interface.api_models import ChatRequest, Setting
from agent_runtime.data_format.fsm import Memory

load_dotenv()


async def test_simple_chat():
    """测试简单的文本聊天"""

    api_key = os.getenv("LLM_API_KEY", "your_api_key_here")
    model = os.getenv("LLM_MODEL", "gpt-4o")
    if model == "gpt-4.1":
        model = "gpt-4o"

    base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1/").strip()

    settings = Setting(
        api_key=api_key,
        chat_model=model,
        base_url=base_url,
        temperature=0.7,
        agent_name="SimpleTestDemo"
    )

    chat_request = ChatRequest(
        user_message="你好，请简单介绍一下你自己",
        settings=settings,
        memory=Memory(history=[])
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            request_data = chat_request.model_dump(mode="json")

            response = await client.post(
                "http://localhost:8011/v1.5/chat",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

            print(f"状态码: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"API响应: {result['response']}")
                print(f"Token使用: 输入{result.get('total_input_token', 0)}, "
                      f"输出{result.get('total_output_token', 0)}")
            else:
                print(f"错误详情: {response.text}")

    except Exception as e:
        print(f"API调用异常: {str(e)}")


if __name__ == "__main__":
    asyncio.run(test_simple_chat())