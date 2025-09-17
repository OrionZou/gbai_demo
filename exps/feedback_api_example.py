"""
Feedback API 使用示例

展示如何使用反馈API进行学习、查询和管理
"""

import asyncio
import httpx
import json
from typing import List, Dict, Any


class FeedbackAPIClient:
    """反馈API客户端"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.api_prefix = "/feedback"

    async def learn(
        self,
        agent_name: str,
        feedbacks: List[Dict[str, Any]],
        vector_db_url: str = "http://localhost:8080"
    ) -> Dict[str, Any]:
        """学习反馈"""
        async with httpx.AsyncClient() as client:
            request_data = {
                "agent_name": agent_name,
                "feedbacks": feedbacks,
                "vector_db_url": vector_db_url
            }
            response = await client.post(
                f"{self.base_url}{self.api_prefix}/learn",
                json=request_data
            )
            response.raise_for_status()
            return response.json()

    async def get_feedbacks(
        self,
        agent_name: str,
        query: str = None,
        tags: List[str] = None,
        offset: int = 0,
        limit: int = -1,
        top_k: int = 5,
        vector_db_url: str = "http://localhost:8080"
    ) -> Dict[str, Any]:
        """获取或搜索反馈"""
        async with httpx.AsyncClient() as client:
            request_data = {
                "agent_name": agent_name,
                "vector_db_url": vector_db_url,
                "offset": offset,
                "limit": limit,
                "top_k": top_k
            }
            if query:
                request_data["query"] = query
            if tags:
                request_data["tags"] = tags

            response = await client.post(
                f"{self.base_url}{self.api_prefix}/get",
                json=request_data
            )
            response.raise_for_status()
            return response.json()

    async def delete_feedbacks(
        self,
        agent_name: str,
        delete_type: str = "all",
        vector_db_url: str = "http://localhost:8080"
    ) -> Dict[str, Any]:
        """删除反馈"""
        async with httpx.AsyncClient() as client:
            request_data = {
                "agent_name": agent_name,
                "delete_type": delete_type,
                "vector_db_url": vector_db_url
            }
            response = await client.post(
                f"{self.base_url}{self.api_prefix}/delete",
                json=request_data
            )
            response.raise_for_status()
            return response.json()

    async def get_stats(self, agent_name: str) -> Dict[str, Any]:
        """获取统计信息"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}{self.api_prefix}/stats/{agent_name}"
            )
            response.raise_for_status()
            return response.json()


async def example_usage():
    """使用示例"""
    print("🎯 Feedback API 使用示例")
    print("=" * 25)

    # 初始化客户端
    client = FeedbackAPIClient()
    agent_name = "example_agent"

    try:
        # 1. 准备训练数据
        print("\n📚 Step 1: 准备学习数据")
        training_feedbacks = [
            {
                "observation_name": "user_question",
                "observation_content": "用户询问如何学习Python编程",
                "action_name": "provide_learning_path",
                "action_content": "推荐了Python学习路径和资源",
                "state_name": "educational_guidance"
            },
            {
                "observation_name": "user_question",
                "observation_content": "用户遇到代码错误需要调试帮助",
                "action_name": "debug_assistance",
                "action_content": "分析代码错误并提供修复建议",
                "state_name": "technical_support"
            },
            {
                "observation_name": "user_question",
                "observation_content": "用户想了解机器学习项目实践",
                "action_name": "project_guidance",
                "action_content": "提供机器学习项目的完整实施方案",
                "state_name": "project_consulting"
            },
            {
                "observation_name": "user_question",
                "observation_content": "用户需要数据分析方面的专业建议",
                "action_name": "data_analysis_advice",
                "action_content": "详细解释数据分析流程和工具使用",
                "state_name": "data_consulting"
            }
        ]

        print(f"准备了 {len(training_feedbacks)} 条训练反馈")

        # 2. 学习反馈
        print("\n🧠 Step 2: 学习反馈")
        learn_result = await client.learn(agent_name, training_feedbacks)
        print(f"✅ 学习成功: {learn_result['message']}")
        print(f"   添加的反馈ID: {len(learn_result['feedback_ids'])} 个")
        print(f"   总反馈数量: {learn_result['count']}")

        # 3. 获取统计信息
        print("\n📊 Step 3: 查看统计信息")
        stats = await client.get_stats(agent_name)
        print(f"✅ 代理: {stats['agent_name']}")
        print(f"   反馈数量: {stats['feedback_count']}")
        print(f"   支持嵌入: {stats['has_embeddings']}")

        # 4. 语义搜索测试
        print("\n🔍 Step 4: 语义搜索测试")
        search_queries = [
            "Python学习",
            "代码调试",
            "机器学习",
            "数据分析"
        ]

        for query in search_queries:
            search_result = await client.get_feedbacks(
                agent_name=agent_name,
                query=query,
                top_k=2
            )
            print(f"\n🔎 搜索: '{query}'")
            print(f"   找到 {search_result['query_count']} 个相关反馈:")
            for i, feedback in enumerate(search_result['feedbacks']):
                print(f"   {i+1}. [{feedback['state_name']}] {feedback['observation_content'][:40]}...")

        # 5. 标签过滤搜索
        print("\n🏷️  Step 5: 标签过滤搜索")
        tagged_result = await client.get_feedbacks(
            agent_name=agent_name,
            query="学习",
            tags=["observation_name_user_question"],
            top_k=3
        )
        print(f"✅ 标签搜索找到 {tagged_result['query_count']} 个反馈")

        # 6. 分页获取
        print("\n📄 Step 6: 分页获取")
        page_result = await client.get_feedbacks(
            agent_name=agent_name,
            offset=0,
            limit=2
        )
        print(f"✅ 分页获取: {page_result['query_count']} / {page_result['total_count']}")

        # 7. 实际应用场景模拟
        print("\n🎮 Step 7: 实际应用场景")
        user_queries = [
            "我是编程新手，应该从哪里开始学习？",
            "我的代码总是报错，怎么办？",
            "如何开始一个机器学习项目？"
        ]

        for user_query in user_queries:
            print(f"\n👤 用户问题: {user_query}")

            # 搜索相关反馈
            similar_feedbacks = await client.get_feedbacks(
                agent_name=agent_name,
                query=user_query,
                top_k=1
            )

            if similar_feedbacks['feedbacks']:
                best_match = similar_feedbacks['feedbacks'][0]
                print(f"🤖 推荐回答策略: [{best_match['state_name']}]")
                print(f"   参考行动: {best_match['action_name']}")
                print(f"   历史处理: {best_match['action_content'][:50]}...")
            else:
                print("🤖 没有找到相关的历史处理经验")

        # 8. 清理数据（可选）
        print("\n🧹 Step 8: 清理测试数据")
        user_input = input("是否删除测试数据? (y/N): ")
        if user_input.lower() == 'y':
            delete_result = await client.delete_feedbacks(agent_name, "all")
            print(f"✅ {delete_result['message']}")

    except Exception as e:
        print(f"❌ 示例执行失败: {e}")


if __name__ == "__main__":
    print("Feedback API 客户端使用示例")
    print("=============================")
    print("这个示例展示了如何使用反馈API进行:")
    print("- 📚 反馈学习")
    print("- 🔍 语义搜索")
    print("- 🏷️ 标签过滤")
    print("- 📊 统计查询")
    print("- 🎮 实际应用场景模拟")
    print()
    print("⚠️  确保API服务器运行在 http://localhost:8000")
    print("⚠️  确保Weaviate运行在 http://localhost:8080")
    print()

    asyncio.run(example_usage())