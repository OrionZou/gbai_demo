"""
Token统计功能演示

演示如何使用TokenCounter模块统计LLM API调用的token消耗。
"""

import asyncio
import os
from dotenv import load_dotenv

from agent_runtime.utils.token_counter import get_token_counter
from agent_runtime.clients.openai_llm_client import LLM
from agent_runtime.config.loader import LLMSetting

load_dotenv()


async def demo_basic_token_counting():
    """基本的token统计演示"""
    print("=== 基本Token统计演示 ===\n")

    # 获取TokenCounter单例
    token_counter = get_token_counter()

    # 创建会话
    session_id = token_counter.create_session("demo_session")
    print(f"创建会话: {session_id}")

    # 模拟记录token使用
    token_counter.record_usage(
        input_tokens=100,
        output_tokens=50,
        model="gpt-4o",
        session_id=session_id
    )
    print("记录第一次API调用: 输入100 tokens, 输出50 tokens")

    token_counter.record_usage(
        input_tokens=200,
        output_tokens=150,
        model="gpt-4o",
        session_id=session_id
    )
    print("记录第二次API调用: 输入200 tokens, 输出150 tokens")

    # 获取统计
    stats = token_counter.get_session_stats(session_id)
    if stats:
        print(f"\n会话统计:")
        print(f"  总输入tokens: {stats.input_tokens}")
        print(f"  总输出tokens: {stats.output_tokens}")
        print(f"  总tokens: {stats.total_tokens}")
        print(f"  API调用次数: {stats.total_requests}")

    # 获取摘要
    summary = token_counter.get_summary(session_id)
    print(f"\n会话摘要:")
    print(f"  平均输入tokens: {summary['average_input_tokens']:.1f}")
    print(f"  平均输出tokens: {summary['average_output_tokens']:.1f}")


async def demo_llm_with_token_counting():
    """LLM集成token统计演示"""
    print("\n=== LLM集成Token统计演示 ===\n")

    # 配置
    api_key = os.getenv("LLM_API_KEY", "your_api_key")
    model = os.getenv("LLM_MODEL", "gpt-4o")
    if model == "gpt-4.1":
        model = "gpt-4o"
    base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1/").strip()

    if api_key == "your_api_key" or "your_api_key" in api_key:
        print("跳过实际API调用（需要有效的API key）")
        return

    # 创建LLM设置
    llm_setting = LLMSetting(
        model=model,
        base_url=base_url,
        api_key=api_key,
        temperature=0.7
    )

    # 创建带session_id的LLM实例
    session_id = "llm_demo_session"
    llm = LLM(llm_setting=llm_setting, session_id=session_id)

    # 获取token计数器并创建会话
    token_counter = get_token_counter()
    token_counter.create_session(session_id)

    try:
        # 调用LLM
        messages = [
            {"role": "user", "content": "写一个简短的笑话"}
        ]

        print(f"调用LLM模型: {model}")
        response = await llm.ask(messages=messages)
        print(f"LLM响应: {response[:100]}...")

        # 获取token统计
        stats = token_counter.get_session_stats(session_id)
        if stats:
            print(f"\nToken统计:")
            print(f"  输入tokens: {stats.input_tokens}")
            print(f"  输出tokens: {stats.output_tokens}")
            print(f"  总tokens: {stats.total_tokens}")

    except Exception as e:
        print(f"LLM调用失败: {e}")


async def demo_global_stats():
    """全局统计演示"""
    print("\n=== 全局统计演示 ===\n")

    token_counter = get_token_counter()

    # 获取全局统计
    global_stats = token_counter.get_global_stats()
    print(f"全局统计:")
    print(f"  总输入tokens: {global_stats.input_tokens}")
    print(f"  总输出tokens: {global_stats.output_tokens}")
    print(f"  总API调用次数: {global_stats.total_requests}")

    # 获取所有会话
    all_sessions = token_counter.get_all_sessions()
    print(f"\n活跃会话数: {len(all_sessions)}")
    for sid, stats in all_sessions.items():
        print(f"  会话 {sid[:20]}...: {stats.total_tokens} tokens")


async def demo_cleanup():
    """清理演示"""
    print("\n=== 清理演示 ===\n")

    token_counter = get_token_counter()

    # 清理旧会话（保留最近1小时的）
    removed = token_counter.cleanup_old_sessions(hours=1)
    print(f"清理了 {removed} 个旧会话")

    # 重置特定会话
    token_counter.reset_session("demo_session")
    print("重置了 demo_session")

    # 重置全局统计
    token_counter.reset_global()
    print("重置了全局统计")


async def main():
    """主函数"""
    print("Token统计模块演示\n")
    print("=" * 50)

    # 运行各个演示
    await demo_basic_token_counting()
    await demo_llm_with_token_counting()
    await demo_global_stats()
    await demo_cleanup()

    print("\n演示完成！")
    print("\nTokenCounter特性:")
    print("✓ 单例模式，全局共享")
    print("✓ 线程安全")
    print("✓ 会话级别统计")
    print("✓ 全局统计")
    print("✓ 自动集成到LLM客户端")
    print("✓ 支持清理和重置")


if __name__ == "__main__":
    asyncio.run(main())