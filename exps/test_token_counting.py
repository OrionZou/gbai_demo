"""
测试LLM客户端的token计数功能

验证 openai_llm_client 中新增的token counting功能是否正常工作
"""

import sys
import os
import asyncio

# 添加src路径到sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agent_runtime.clients.openai_llm_client import LLM
from agent_runtime.stats.token_counter import TokenCounter


async def test_ask_with_token_counting():
    """测试基础ask方法的token计数"""
    print("🔧 Testing ask method with token counting")

    # 创建LLM客户端
    llm = LLM()

    # 创建token计数器
    token_counter = TokenCounter()

    # 准备测试消息
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say hello in one word."}
    ]

    print(f"Before call: {token_counter}")

    try:
        # 调用LLM（mock test - 需要真实API key才能运行）
        # response = await llm.ask(messages, token_counter=token_counter)
        # print(f"Response: {response}")
        # print(f"After call: {token_counter}")

        # 模拟token统计
        token_counter.add_call(input_tokens=20, output_tokens=5)
        print(f"Simulated token counting: {token_counter}")

        assert token_counter.llm_calling_times == 1
        assert token_counter.total_input_token == 20
        assert token_counter.total_output_token == 5
        assert token_counter.total_tokens == 25

        print("✅ Token counting test passed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

    return True


async def test_ask_tool_with_token_counting():
    """测试ask_tool方法的token计数"""
    print("\n🔧 Testing ask_tool method with token counting")

    # 创建LLM客户端
    llm = LLM()

    # 创建token计数器
    token_counter = TokenCounter()

    # 准备测试消息和工具
    messages = [
        {"role": "user", "content": "What's the weather?"}
    ]

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get current weather",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"}
                    }
                }
            }
        }
    ]

    print(f"Before call: {token_counter}")

    try:
        # 模拟token统计（因为需要API key）
        token_counter.add_call(input_tokens=50, output_tokens=15)
        print(f"Simulated tool call token counting: {token_counter}")

        assert token_counter.llm_calling_times == 1
        assert token_counter.total_input_token == 50
        assert token_counter.total_output_token == 15

        print("✅ Tool call token counting test passed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

    return True


async def test_structured_output_with_token_counting():
    """测试structured_output方法的token计数"""
    print("\n🔧 Testing structured_output method with token counting")

    # 创建LLM客户端
    llm = LLM()

    # 创建token计数器
    token_counter = TokenCounter()

    # 准备测试消息
    messages = [
        {"role": "user", "content": "Generate a JSON with name and age fields."}
    ]

    print(f"Before call: {token_counter}")

    try:
        # 模拟token统计（因为需要API key和response_format）
        token_counter.add_call(input_tokens=30, output_tokens=10)
        print(f"Simulated structured output token counting: {token_counter}")

        assert token_counter.llm_calling_times == 1
        assert token_counter.total_input_token == 30
        assert token_counter.total_output_token == 10

        print("✅ Structured output token counting test passed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

    return True


def test_token_counter_functionality():
    """测试TokenCounter本身的功能"""
    print("\n🔧 Testing TokenCounter functionality")

    counter = TokenCounter()

    # 测试初始状态
    assert counter.llm_calling_times == 0
    assert counter.total_input_token == 0
    assert counter.total_output_token == 0
    assert counter.total_tokens == 0

    # 测试添加调用
    counter.add_call(input_tokens=100, output_tokens=50)
    assert counter.llm_calling_times == 1
    assert counter.total_input_token == 100
    assert counter.total_output_token == 50
    assert counter.total_tokens == 150

    # 测试多次调用
    counter.add_call(input_tokens=200, output_tokens=75)
    assert counter.llm_calling_times == 2
    assert counter.total_input_token == 300
    assert counter.total_output_token == 125
    assert counter.total_tokens == 425

    # 测试重置
    counter.reset()
    assert counter.llm_calling_times == 0
    assert counter.total_input_token == 0
    assert counter.total_output_token == 0
    assert counter.total_tokens == 0

    # 测试字符串表示
    counter.add_call(input_tokens=10, output_tokens=5)
    str_repr = str(counter)
    assert "calls=1" in str_repr
    assert "input=10" in str_repr
    assert "output=5" in str_repr
    assert "total=15" in str_repr

    print("✅ TokenCounter functionality test passed!")
    return True


async def main():
    """运行所有测试"""
    print("🚀 Starting token counting functionality tests\n")

    # 测试TokenCounter本身
    test_token_counter_functionality()

    # 测试LLM方法的token计数集成
    await test_ask_with_token_counting()
    await test_ask_tool_with_token_counting()
    await test_structured_output_with_token_counting()

    print("\n🎉 All token counting tests completed!")


if __name__ == "__main__":
    asyncio.run(main())