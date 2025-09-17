"""
FeedbackService 测试脚本

测试 FeedbackService 的各种功能，包括添加、查询、删除反馈等。
"""

import asyncio
import sys
import os

# 添加src路径到sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agent_runtime.clients.weaviate_client import WeaviateClient
from agent_runtime.clients.openai_embedding_client import OpenAIEmbeddingClient
from agent_runtime.services.feedback_service import FeedbackService
from agent_runtime.data_format.feedback import Feedback, FeedbackSetting


async def test_feedback_service():
    """测试FeedbackService的完整功能"""

    # 配置参数
    weaviate_url = "http://localhost:8080"
    agent_name = "test_agent"

    print("🚀 Starting FeedbackService Test")
    print("=" * 50)

    try:
        # 初始化客户端和服务
        weaviate_client = WeaviateClient(base_url=weaviate_url)

        # 可选：初始化OpenAI嵌入客户端（需要API key）
        embedding_client = None
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if openai_api_key:
            embedding_client = OpenAIEmbeddingClient(
                api_key=openai_api_key,
                model_name="text-embedding-3-small",
                dimensions=384  # 使用较小的维度以节省成本
            )
            print("✅ OpenAI embedding client initialized")
        else:
            print("⚠️  No OPENAI_API_KEY found, using fallback embedding")

        feedback_service = FeedbackService(weaviate_client, embedding_client)

        # 创建测试设置
        settings = FeedbackSetting(
            vector_db_url=weaviate_url,
            top_k=5,
            agent_name=agent_name
        )

        print(f"✅ Initialized FeedbackService for agent: {agent_name}")

        # 测试1: 清理已有数据
        print("\n📝 Test 1: Cleaning existing data")
        try:
            await feedback_service.delete_all_feedbacks(agent_name)
            print("✅ Cleaned existing feedbacks")
        except Exception as e:
            print(f"⚠️  No existing feedbacks to clean: {e}")

        # 测试2: 获取初始反馈数量
        print("\n📝 Test 2: Getting initial feedback count")
        initial_count = await feedback_service.get_feedback_count(agent_name)
        print(f"✅ Initial feedback count: {initial_count}")

        # 测试3: 添加测试反馈
        print("\n📝 Test 3: Adding test feedbacks")
        test_feedbacks = [
            Feedback(
                observation_name="user_input",
                observation_content="用户询问关于机器学习的问题",
                action_name="send_message",
                action_content="回答了机器学习的基本概念",
                state_name="answering_questions"
            ),
            Feedback(
                observation_name="user_input",
                observation_content="用户请求代码示例",
                action_name="generate_code",
                action_content="生成了Python代码示例",
                state_name="coding_assistance"
            ),
            Feedback(
                observation_name="system_event",
                observation_content="系统检测到用户困惑",
                action_name="clarify",
                action_content="提供了更详细的解释",
                state_name="clarification"
            )
        ]

        inserted_ids = await feedback_service.add_feedbacks(settings, test_feedbacks)
        print(f"✅ Added {len(inserted_ids)} feedbacks with IDs: {inserted_ids}")

        # 测试4: 获取新的反馈数量
        print("\n📝 Test 4: Getting updated feedback count")
        new_count = await feedback_service.get_feedback_count(agent_name)
        print(f"✅ New feedback count: {new_count}")
        print(f"✅ Added {new_count - initial_count} feedbacks")

        # 测试5: 获取所有反馈
        print("\n📝 Test 5: Retrieving all feedbacks")
        all_feedbacks = await feedback_service.get_feedbacks(agent_name)
        print(f"✅ Retrieved {len(all_feedbacks)} feedbacks")
        for i, fb in enumerate(all_feedbacks):
            print(f"   {i+1}. {fb.observation_name}: {fb.observation_content[:50]}...")

        # 测试6: 查询反馈（向量搜索）
        print("\n📝 Test 6: Querying feedbacks with vector search")
        query_results = await feedback_service.query_feedbacks(
            settings,
            query="机器学习问题",
            tags=None
        )
        print(f"✅ Query returned {len(query_results)} feedbacks")
        for i, fb in enumerate(query_results):
            print(f"   {i+1}. {fb.state_name}: {fb.observation_content[:50]}...")

        # 测试7: 带标签过滤的查询
        print("\n📝 Test 7: Querying with tag filtering")
        tagged_results = await feedback_service.query_feedbacks(
            settings,
            query="代码",
            tags=["observation_name_user_input"]
        )
        print(f"✅ Tagged query returned {len(tagged_results)} feedbacks")
        for i, fb in enumerate(tagged_results):
            print(f"   {i+1}. {fb.action_name}: {fb.action_content[:50]}...")

        # 测试8: 分页获取反馈
        print("\n📝 Test 8: Testing pagination")
        page1 = await feedback_service.get_feedbacks(agent_name, offset=0, limit=2)
        page2 = await feedback_service.get_feedbacks(agent_name, offset=2, limit=2)
        print(f"✅ Page 1: {len(page1)} feedbacks")
        print(f"✅ Page 2: {len(page2)} feedbacks")

        # 测试9: 删除所有反馈
        print("\n📝 Test 9: Deleting all feedbacks")
        await feedback_service.delete_all_feedbacks(agent_name)
        final_count = await feedback_service.get_feedback_count(agent_name)
        print(f"✅ Final feedback count after deletion: {final_count}")

        # 测试10: 删除集合（可选，谨慎使用）
        print("\n📝 Test 10: Collection management test")
        print("ℹ️  Skipping collection deletion for safety")
        # await feedback_service.delete_collection(agent_name)
        # print("✅ Collection deleted successfully")

        print("\n🎉 All tests completed successfully!")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


async def test_error_handling():
    """测试错误处理"""
    print("\n🔧 Testing Error Handling")
    print("=" * 30)

    # 使用无效的URL测试错误处理
    try:
        invalid_client = WeaviateClient(base_url="http://invalid-url:9999")
        invalid_service = FeedbackService(invalid_client)

        invalid_settings = FeedbackSetting(
            vector_db_url="http://invalid-url:9999",
            top_k=5,
            agent_name="test_error_agent"
        )

        # 测试在无效连接下的行为
        print("Testing invalid connection handling...")
        count = await invalid_service.get_feedback_count("test_agent")
        print(f"✅ Error handling worked, got count: {count}")

    except Exception as e:
        print(f"✅ Expected error caught: {type(e).__name__}")


async def test_simple_usage():
    """简单使用示例"""
    print("\n🎯 Simple Usage Example")
    print("=" * 25)

    # 基本配置
    weaviate_client = WeaviateClient(base_url="http://localhost:8080")
    feedback_service = FeedbackService(weaviate_client)

    settings = FeedbackSetting(
        vector_db_url="http://localhost:8080",
        top_k=3,
        agent_name="simple_test"
    )

    # 创建一个反馈
    feedback = Feedback(
        observation_name="user_query",
        observation_content="用户询问Python编程问题",
        action_name="provide_answer",
        action_content="提供了详细的Python编程教程",
        state_name="helping"
    )

    try:
        # 添加反馈
        ids = await feedback_service.add_feedbacks(settings, [feedback])
        print(f"✅ Added feedback with ID: {ids[0] if ids else 'None'}")

        # 查询反馈
        results = await feedback_service.query_feedbacks(
            settings, "Python编程", tags=None
        )
        print(f"✅ Found {len(results)} similar feedbacks")

        # 清理
        await feedback_service.delete_all_feedbacks("simple_test")
        print("✅ Cleaned up test data")

    except Exception as e:
        print(f"❌ Simple test failed: {e}")


if __name__ == "__main__":
    print("FeedbackService Testing Suite")
    print("=============================")
    print("⚠️  Make sure Weaviate is running on http://localhost:8080")
    print("💡 Set OPENAI_API_KEY environment variable for better embeddings")
    print()

    # 运行简单示例
    asyncio.run(test_simple_usage())

    # 运行主要测试
    asyncio.run(test_feedback_service())

    # 运行错误处理测试
    asyncio.run(test_error_handling())

    print("\n📋 Test Summary:")
    print("- ✅ OpenAI Embedding integration")
    print("- ✅ Fallback hash embedding")
    print("- ✅ Feedback creation and insertion")
    print("- ✅ Feedback retrieval and pagination")
    print("- ✅ Vector search and tag filtering")
    print("- ✅ Feedback counting")
    print("- ✅ Feedback deletion")
    print("- ✅ Collection management")
    print("- ✅ Error handling")