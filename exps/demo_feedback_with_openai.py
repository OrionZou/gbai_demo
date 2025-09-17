"""
FeedbackService with OpenAI Embedding Demo

演示如何使用OpenAI嵌入客户端集成的FeedbackService
"""

import asyncio
import os
import sys

# 添加src路径到sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agent_runtime.clients.weaviate_client import WeaviateClient
from agent_runtime.clients.openai_embedding_client import OpenAIEmbeddingClient
from agent_runtime.services.feedback_service import FeedbackService
from agent_runtime.data_format.feedback import Feedback, FeedbackSetting


async def demo_openai_embedding_integration():
    """演示OpenAI嵌入集成"""
    print("🎯 FeedbackService + OpenAI Embedding Demo")
    print("=" * 45)

    # 配置
    weaviate_url = "http://localhost:8080"
    agent_name = "demo_agent"

    # 检查OpenAI API密钥
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("❌ 请设置OPENAI_API_KEY环境变量")
        print("   export OPENAI_API_KEY='your-api-key-here'")
        return

    try:
        # 初始化客户端
        print("📡 Initializing clients...")
        weaviate_client = WeaviateClient(base_url=weaviate_url)

        embedding_client = OpenAIEmbeddingClient(
            api_key=openai_api_key,
            model_name="text-embedding-3-small",
            dimensions=384,  # 使用较小维度节省成本
            batch_size=5
        )

        feedback_service = FeedbackService(
            weaviate_client=weaviate_client,
            embedding_client=embedding_client
        )

        settings = FeedbackSetting(
            vector_db_url=weaviate_url,
            top_k=3,
            agent_name=agent_name
        )

        print("✅ All clients initialized successfully")

        # 清理之前的数据
        print("\n🧹 Cleaning previous data...")
        try:
            await feedback_service.delete_all_feedbacks(agent_name)
            print("✅ Previous data cleaned")
        except Exception:
            print("ℹ️  No previous data to clean")

        # 创建测试反馈
        print("\n📝 Creating test feedbacks...")
        feedbacks = [
            Feedback(
                observation_name="user_question",
                observation_content="用户询问如何使用Python进行机器学习",
                action_name="provide_tutorial",
                action_content="提供了详细的Python机器学习教程和代码示例",
                state_name="teaching"
            ),
            Feedback(
                observation_name="user_question",
                observation_content="用户请求帮助调试深度学习模型",
                action_name="debug_assistance",
                action_content="分析了模型代码并提供了调试建议",
                state_name="debugging"
            ),
            Feedback(
                observation_name="user_question",
                observation_content="用户想了解自然语言处理的最新发展",
                action_name="explain_nlp",
                action_content="详细介绍了Transformer架构和GPT模型",
                state_name="explaining"
            ),
            Feedback(
                observation_name="user_question",
                observation_content="用户需要数据分析和可视化的帮助",
                action_name="data_analysis",
                action_content="使用pandas和matplotlib进行数据分析演示",
                state_name="analyzing"
            )
        ]

        # 添加反馈（使用OpenAI嵌入）
        print("🚀 Adding feedbacks with OpenAI embeddings...")
        inserted_ids = await feedback_service.add_feedbacks(settings, feedbacks)
        print(f"✅ Added {len(inserted_ids)} feedbacks with OpenAI embeddings")

        # 获取反馈统计
        count = await feedback_service.get_feedback_count(agent_name)
        print(f"📊 Total feedbacks in collection: {count}")

        # 进行语义搜索
        print("\n🔍 Performing semantic search tests...")

        search_queries = [
            "Python编程学习",
            "深度学习和神经网络",
            "文本处理和NLP",
            "数据科学和统计分析"
        ]

        for query in search_queries:
            print(f"\n🔎 Searching for: '{query}'")
            results = await feedback_service.query_feedbacks(
                settings=settings,
                query=query,
                tags=None
            )

            print(f"   📋 Found {len(results)} relevant feedbacks:")
            for i, result in enumerate(results):
                similarity_score = "High" if i == 0 else "Medium" if i == 1 else "Low"
                print(f"   {i+1}. [{similarity_score}] {result.action_name}: {result.observation_content[:50]}...")

        # 测试标签过滤
        print("\n🏷️  Testing tag-based filtering...")
        tagged_results = await feedback_service.query_feedbacks(
            settings=settings,
            query="学习",
            tags=["observation_name_user_question"]
        )
        print(f"   📋 Found {len(tagged_results)} feedbacks with specific tags")

        # 展示向量相似性
        print("\n🎯 Testing semantic similarity...")
        similar_queries = [
            ("机器学习教程", "Python ML学习"),
            ("调试神经网络", "深度学习问题"),
            ("NLP和语言模型", "自然语言处理")
        ]

        for query1, query2 in similar_queries:
            print(f"\n   Comparing: '{query1}' vs '{query2}'")

            results1 = await feedback_service.query_feedbacks(settings, query1)
            results2 = await feedback_service.query_feedbacks(settings, query2)

            # 检查是否返回相似的结果
            if results1 and results2:
                match = results1[0].state_name == results2[0].state_name
                print(f"   🎯 Top results match: {'✅ Yes' if match else '❌ No'}")
            else:
                print("   ⚠️  Insufficient results for comparison")

        print("\n🎉 Demo completed successfully!")
        print("\n📈 Benefits of OpenAI Embedding Integration:")
        print("   - 🧠 Better semantic understanding")
        print("   - 🎯 More accurate similarity search")
        print("   - 🌐 Multi-language support")
        print("   - ⚡ Batch processing efficiency")
        print("   - 🔄 Automatic fallback to hash embedding")

    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("OpenAI Embedding Integration Demo")
    print("=================================")
    print("This demo shows how FeedbackService uses OpenAI embeddings")
    print("for better semantic search and similarity matching.")
    print()

    asyncio.run(demo_openai_embedding_integration())