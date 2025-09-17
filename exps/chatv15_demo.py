"""
ChatV15Service vs v2_core.chat 对比演示

展示重构前后的使用方式和优势
"""

import asyncio
import sys
import os

# 添加src路径到sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agent_runtime.services.chat_v1_5_service import ChatService
from agent_runtime.interface.api_models import Setting, Memory, chat
from agent_runtime.stats import TokenCounter


async def demo_old_vs_new():
    """演示新旧接口的对比"""
    print("🎯 ChatService vs v2_core.chat 对比演示")
    print("=" * 45)

    # 创建通用设置
    settings = Setting(
        api_key="demo-key",
        chat_model="gpt-4o-mini",
        agent_name="demo_agent",
        vector_db_url="http://localhost:8080"
    )

    print("\n📖 方式1: 使用原始的 v2_core.chat 函数")
    print("-" * 35)
    try:
        memory1 = Memory()
        token_counter1 = TokenCounter()

        result_memory1, result_counter1 = await chat(
            settings=settings,
            memory=memory1,
            request_tools=[],
            token_counter=token_counter1
        )

        print("✅ v2_core.chat 调用成功")
        print(f"   步骤数: {len(result_memory1.history)}")
        print(f"   Token: {result_counter1.llm_calling_times}")

    except Exception as e:
        print(f"❌ v2_core.chat 失败: {e}")

    print("\n🚀 方式2: 使用新的 ChatService")
    print("-" * 35)
    try:
        # 创建服务实例
        chat_service = ChatService()

        memory2 = Memory()
        token_counter2 = TokenCounter()

        result_memory2, result_counter2 = await chat_service.chat(
            settings=settings,
            memory=memory2,
            request_tools=[],
            token_counter=token_counter2
        )

        print("✅ ChatService 调用成功")
        print(f"   步骤数: {len(result_memory2.history)}")
        print(f"   Token: {result_counter2.llm_calling_times}")

        # 显示服务统计
        stats = chat_service.get_stats()
        print(f"   服务统计: {stats['service_type']}")

    except Exception as e:
        print(f"❌ ChatService 失败: {e}")


async def demo_service_advantages():
    """演示服务化的优势"""
    print("\n🎁 ChatService 的优势")
    print("=" * 25)

    chat_service = ChatService()

    print("1. 🏗️  更好的模块化结构")
    print("   - 分离的初始化、执行、状态选择逻辑")
    print("   - 每个步骤都有独立的方法")
    print("   - 更容易进行单元测试")

    print("\n2. 📊 服务统计和监控")
    stats = chat_service.get_stats()
    for key, value in stats.items():
        print(f"   - {key}: {value}")

    print("\n3. 🔧 更容易扩展和定制")
    print("   - 可以继承ChatService来创建专门的服务")
    print("   - 可以重写特定方法来定制行为")
    print("   - 保持向后兼容性")

    print("\n4. 🧪 更好的测试能力")
    print("   - 可以模拟服务的各个组件")
    print("   - 独立测试每个步骤")
    print("   - 更精确的错误定位")


class CustomChatService(ChatService):
    """自定义聊天服务示例"""

    async def _initialize_memory_if_needed(self, settings, memory, send_message_to_user, token_counter):
        """自定义的记忆初始化"""
        print("🎨 使用自定义记忆初始化逻辑")
        return await super()._initialize_memory_if_needed(
            settings, memory, send_message_to_user, token_counter
        )

    def get_stats(self):
        """扩展的统计信息"""
        base_stats = super().get_stats()
        base_stats["custom_features"] = ["enhanced_memory", "custom_init"]
        return base_stats


async def demo_customization():
    """演示自定义服务"""
    print("\n🎨 自定义服务演示")
    print("=" * 20)

    try:
        custom_service = CustomChatService()

        settings = Setting(
            api_key="custom-key",
            chat_model="gpt-4o-mini",
            agent_name="custom_agent",
            vector_db_url="http://localhost:8080"
        )

        memory = Memory()

        print("📝 使用自定义ChatService:")
        result_memory, result_counter = await custom_service.chat(
            settings=settings,
            memory=memory,
            request_tools=[]
        )

        print("✅ 自定义服务调用成功")

        # 显示扩展的统计信息
        custom_stats = custom_service.get_stats()
        print(f"🔍 自定义统计: {custom_stats}")

    except Exception as e:
        print(f"❌ 自定义服务失败: {e}")


def demo_migration_guide():
    """迁移指南"""
    print("\n📚 迁移指南")
    print("=" * 15)

    print("🔄 从 v2_core.chat 迁移到 ChatService:")
    print()

    print("旧代码:")
    print("```python")
    print("from agent_runtime.data_format.v2_core import chat")
    print()
    print("result = await chat(")
    print("    settings=settings,")
    print("    memory=memory,")
    print("    request_tools=tools")
    print(")")
    print("```")

    print("\n新代码:")
    print("```python")
    print("from agent_runtime.services.chat_v1_5_service import ChatService")
    print()
    print("chat_service = ChatService()")
    print("result = await chat_service.chat(")
    print("    settings=settings,")
    print("    memory=memory,")
    print("    request_tools=tools")
    print(")")
    print("```")

    print("\n✨ 好处:")
    print("- 🏗️ 更清晰的架构")
    print("- 📊 内置统计功能")
    print("- 🔧 更容易扩展")
    print("- 🧪 更好的测试性")
    print("- 🔄 完全向后兼容")


if __name__ == "__main__":
    print("ChatService 重构演示")
    print("========================")
    print("这个演示展示了从v2_core.chat重构到ChatService的优势")
    print()

    # 运行对比演示
    asyncio.run(demo_old_vs_new())

    # 展示服务优势
    asyncio.run(demo_service_advantages())

    # 演示自定义能力
    asyncio.run(demo_customization())

    # 显示迁移指南
    demo_migration_guide()

    print("\n🎉 重构演示完成！")
    print("ChatService提供了更好的架构和更强的功能，")
    print("同时保持了完全的向后兼容性。")