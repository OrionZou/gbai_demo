"""
Token Counting Usage Demo

演示如何使用LLM客户端的token计数功能
"""

import sys
import os
import asyncio

# 添加src路径到sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agent_runtime.clients.openai_llm_client import LLM
from agent_runtime.stats.token_counter import TokenCounter


async def demo_basic_usage():
    """演示基本用法"""
    print("📋 Demo: Basic Token Counting Usage")

    # 1. 创建LLM客户端
    llm = LLM()

    # 2. 创建token计数器
    token_counter = TokenCounter()

    # 3. 准备消息
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"}
    ]

    print(f"初始状态: {token_counter}")

    # 4. 调用LLM并传入token_counter
    # response = await llm.ask(messages, token_counter=token_counter)

    # 模拟调用（实际使用时会自动计数）
    token_counter.add_call(input_tokens=25, output_tokens=8)

    print(f"调用后状态: {token_counter}")
    print(f"总token使用量: {token_counter.total_tokens}")
    print(f"调用次数: {token_counter.llm_calling_times}")
    print()


async def demo_multiple_calls():
    """演示多次调用的统计"""
    print("📋 Demo: Multiple Calls Token Counting")

    llm = LLM()
    token_counter = TokenCounter()

    # 模拟多次LLM调用
    calls_data = [
        {"input": 30, "output": 12},
        {"input": 45, "output": 20},
        {"input": 60, "output": 25},
    ]

    print(f"开始时: {token_counter}")

    for i, call_data in enumerate(calls_data, 1):
        # 模拟调用
        token_counter.add_call(
            input_tokens=call_data["input"],
            output_tokens=call_data["output"]
        )
        print(f"第{i}次调用后: {token_counter}")

    print(f"\n累计统计:")
    print(f"  总调用次数: {token_counter.llm_calling_times}")
    print(f"  总输入tokens: {token_counter.total_input_token}")
    print(f"  总输出tokens: {token_counter.total_output_token}")
    print(f"  总tokens: {token_counter.total_tokens}")
    print()


async def demo_tool_calling_with_counting():
    """演示工具调用的token计数"""
    print("📋 Demo: Tool Calling with Token Counting")

    llm = LLM()
    token_counter = TokenCounter()

    # 准备工具调用相关数据
    messages = [
        {"role": "user", "content": "What's the weather in Beijing?"}
    ]

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get current weather information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city name"
                        }
                    },
                    "required": ["location"]
                }
            }
        }
    ]

    print(f"工具调用前: {token_counter}")

    # 模拟工具调用
    # message = await llm.ask_tool(
    #     messages=messages,
    #     tools=tools,
    #     token_counter=token_counter
    # )

    # 模拟工具调用的token消耗
    token_counter.add_call(input_tokens=80, output_tokens=35)

    print(f"工具调用后: {token_counter}")
    print(f"工具调用token消耗: {token_counter.total_tokens}")
    print()


async def demo_structured_output_counting():
    """演示结构化输出的token计数"""
    print("📋 Demo: Structured Output with Token Counting")

    llm = LLM()
    token_counter = TokenCounter()

    messages = [
        {
            "role": "user",
            "content": "Generate a JSON object with user information including name, age, and email."
        }
    ]

    print(f"结构化输出前: {token_counter}")

    # 模拟结构化输出调用
    # result = await llm.structured_output_old(
    #     messages=messages,
    #     token_counter=token_counter
    # )

    # 模拟结构化输出的token消耗
    token_counter.add_call(input_tokens=50, output_tokens=25)

    print(f"结构化输出后: {token_counter}")
    print(f"结构化输出token消耗: {token_counter.total_tokens}")
    print()


def demo_counter_management():
    """演示计数器管理功能"""
    print("📋 Demo: Token Counter Management")

    counter = TokenCounter()

    # 添加一些调用记录
    counter.add_call(100, 50)
    counter.add_call(150, 75)
    print(f"累计后: {counter}")

    # 获取总计信息
    print(f"总token数: {counter.total_tokens}")
    print(f"平均输入tokens: {counter.total_input_token / counter.llm_calling_times:.1f}")
    print(f"平均输出tokens: {counter.total_output_token / counter.llm_calling_times:.1f}")

    # 重置计数器
    counter.reset()
    print(f"重置后: {counter}")
    print()


async def demo_integration_with_agents():
    """演示与Agent系统的集成"""
    print("📋 Demo: Integration with Agent Systems")

    # 创建session级别的token计数器
    session_counter = TokenCounter()

    print("模拟Agent会话中的token使用:")

    # 模拟不同agent的调用
    agents = [
        {"name": "StateSelectAgent", "input": 40, "output": 15},
        {"name": "SelectActionsAgent", "input": 120, "output": 45},
        {"name": "RewardAgent", "input": 80, "output": 30},
    ]

    for agent in agents:
        session_counter.add_call(
            input_tokens=agent["input"],
            output_tokens=agent["output"]
        )
        print(f"  {agent['name']}: input={agent['input']}, output={agent['output']}")

    print(f"\n会话总计: {session_counter}")
    print(f"会话总成本预估: {session_counter.total_tokens} tokens")
    print()


async def main():
    """运行所有演示"""
    print("🚀 Token Counting Usage Demos\n")

    await demo_basic_usage()
    await demo_multiple_calls()
    await demo_tool_calling_with_counting()
    await demo_structured_output_counting()
    demo_counter_management()
    await demo_integration_with_agents()

    print("🎯 所有演示完成!")
    print("\n💡 使用要点:")
    print("1. 在调用LLM方法时传入token_counter参数")
    print("2. TokenCounter会自动统计输入输出token数")
    print("3. 可以在会话级别或请求级别进行token统计")
    print("4. 使用reset()方法重置计数器")
    print("5. 通过total_tokens属性获取总token消耗")


if __name__ == "__main__":
    asyncio.run(main())