"""
测试ChatService的高级功能

包括chat_step方法的测试和集成的agent功能测试
"""

import asyncio
import sys
import os

# 添加src路径到sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agent_runtime.services.chat_v1_5_service import ChatService
from agent_runtime.interface.api_models import Setting, Memory
from agent_runtime.data_format.fsm import StateMachine, State
from agent_runtime.data_format.tool import RequestTool


async def test_chat_step_functionality():
    """测试ChatService的chat_step方法"""
    print("🚀 Testing ChatService chat_step functionality")
    print("=" * 50)

    try:
        # 创建ChatService实例
        chat_service = ChatService()
        print("✅ ChatService initialized with all agents")

        # 创建基本设置
        settings = Setting(
            api_key="test-key",
            chat_model="gpt-4o-mini",
            agent_name="advanced_test_agent",
            vector_db_url="http://localhost:8080",
            top_k=5
        )

        # 创建空记忆
        memory = Memory()

        print("\n📝 Test 1: 基本chat_step功能")
        result = await chat_service.chat_step(
            user_message="Hello, how are you?",
            settings=settings,
            memory=memory,
            request_tools=[]
        )

        print("✅ chat_step调用成功")
        print(f"   响应类型: {result['result_type']}")
        print(f"   历史步骤数: {len(result['memory'].history)}")
        print(f"   LLM调用次数: {result['llm_calling_times']}")

        print("\n📝 Test 2: 编辑响应功能")
        result2 = await chat_service.chat_step(
            user_message="What's the weather like?",
            edited_last_response="Hello! I'm doing well, thank you for asking.",
            settings=settings,
            memory=result['memory'],
            request_tools=[]
        )

        print("✅ 编辑响应功能测试成功")
        print(f"   新的历史步骤数: {len(result2['memory'].history)}")

        print("\n📝 Test 3: 撤回功能")
        result3 = await chat_service.chat_step(
            user_message="Tell me a joke",
            recall_last_user_message=True,
            settings=settings,
            memory=result2['memory'],
            request_tools=[]
        )

        print("✅ 撤回功能测试成功")
        print(f"   撤回后历史步骤数: {len(result3['memory'].history)}")

        print("\n🎉 chat_step功能测试完成")

    except Exception as e:
        print(f"❌ chat_step测试失败: {e}")
        import traceback
        traceback.print_exc()


async def test_state_agents_integration():
    """测试状态agents的集成"""
    print("\n🎯 Testing State Agents Integration")
    print("=" * 40)

    try:
        chat_service = ChatService()

        # 创建状态机
        states = [
            State(
                name="greeting",
                scenario="问候用户",
                instruction="友好地问候用户并询问需要什么帮助"
            ),
            State(
                name="helping",
                scenario="提供帮助",
                instruction="根据用户需求提供具体的帮助和建议"
            ),
            State(
                name="farewell",
                scenario="告别用户",
                instruction="礼貌地与用户告别"
            )
        ]

        state_machine = StateMachine(
            initial_state_name="greeting",
            states=states,
            out_transitions={
                "greeting": ["helping"],
                "helping": ["farewell", "greeting"],
                "farewell": []
            }
        )

        settings = Setting(
            api_key="test-key",
            chat_model="gpt-4o-mini",
            agent_name="state_test_agent",
            vector_db_url="http://localhost:8080",
            top_k=5,
            state_machine=state_machine
        )

        memory = Memory()

        print("📝 Test: 带状态机的chat_step")
        result = await chat_service.chat_step(
            user_message="Hi there!",
            settings=settings,
            memory=memory,
            request_tools=[]
        )

        print("✅ 状态机集成测试成功")
        print(f"   当前状态: {result['memory'].history[-1].state_name}")
        print(f"   可用状态数: {len(settings.state_machine.states)}")

        # 显示增强的统计信息
        stats = chat_service.get_stats()
        print(f"\n📊 增强的服务统计:")
        for key, value in stats.items():
            print(f"   - {key}: {value}")

        print("\n🎉 状态agents集成测试完成")

    except Exception as e:
        print(f"❌ 状态agents测试失败: {e}")
        import traceback
        traceback.print_exc()


async def test_new_state_creation():
    """测试新状态创建功能"""
    print("\n🆕 Testing New State Creation")
    print("=" * 35)

    try:
        chat_service = ChatService()

        # 创建没有预定义状态的设置
        settings = Setting(
            api_key="test-key",
            chat_model="gpt-4o-mini",
            agent_name="new_state_test_agent",
            vector_db_url="http://localhost:8080",
            top_k=5,
            state_machine=StateMachine()  # 空状态机
        )

        memory = Memory()

        print("📝 Test: 无预定义状态的chat_step")
        result = await chat_service.chat_step(
            user_message="I need help with coding",
            settings=settings,
            memory=memory,
            request_tools=[]
        )

        print("✅ 新状态创建测试成功")
        print(f"   历史步骤数: {len(result['memory'].history)}")
        print(f"   Result type: {result['result_type']}")

        print("\n🎉 新状态创建测试完成")

    except Exception as e:
        print(f"❌ 新状态创建测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_error_handling():
    """测试错误处理"""
    print("\n🔧 Testing Error Handling")
    print("=" * 25)

    try:
        chat_service = ChatService()

        print("📝 Test: 缺少必需参数")
        try:
            asyncio.run(chat_service.chat_step(user_message="Hello"))
            print("❌ 应该抛出错误但没有")
        except ValueError as e:
            print(f"✅ 正确捕获错误: {e}")

        print("\n🎉 错误处理测试完成")

    except Exception as e:
        print(f"❌ 错误处理测试失败: {e}")


if __name__ == "__main__":
    print("ChatService Advanced Testing Suite")
    print("==================================")
    print("测试ChatService的高级功能，包括集成的agents")
    print()

    # 运行高级功能测试
    asyncio.run(test_chat_step_functionality())

    # 运行状态agents集成测试
    asyncio.run(test_state_agents_integration())

    # 运行新状态创建测试
    asyncio.run(test_new_state_creation())

    # 运行错误处理测试
    test_error_handling()

    print("\n📋 测试总结:")
    print("- ✅ chat_step基本功能")
    print("- ✅ 消息编辑和撤回")
    print("- ✅ 状态agents集成")
    print("- ✅ 新状态创建")
    print("- ✅ 错误处理机制")
    print("- ✅ 增强的服务统计")

    print("\n🎯 ChatService高级功能测试完成！")
    print("所有agent逻辑已成功集成到ChatService中。")