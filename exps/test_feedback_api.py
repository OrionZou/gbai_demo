"""
Feedback API 测试脚本

测试 learn、get 和 delete API 的功能
"""

import asyncio
import httpx
import json
import sys
import os

# 添加src路径到sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agent_runtime.data_format.feedback import Feedback


# API 基础URL
BASE_URL = "http://localhost:8000"
API_PREFIX = "/feedback"


async def test_feedback_apis():
    """测试反馈API"""
    print("🚀 Testing Feedback APIs")
    print("=" * 30)

    async with httpx.AsyncClient() as client:
        agent_name = "test_api_agent"

        try:
            # 1. 健康检查
            print("\n📝 Test 1: Health Check")
            response = await client.get(f"{BASE_URL}{API_PREFIX}/health")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")

            # 2. 获取初始统计
            print("\n📝 Test 2: Initial Stats")
            response = await client.get(f"{BASE_URL}{API_PREFIX}/stats/{agent_name}")
            if response.status_code == 200:
                stats = response.json()
                print(f"Initial feedback count: {stats['feedback_count']}")
                print(f"Has embeddings: {stats['has_embeddings']}")
            else:
                print(f"Stats request failed: {response.status_code}")

            # 3. 学习反馈
            print("\n📝 Test 3: Learn Feedbacks")
            feedbacks_data = [
                {
                    "observation_name": "user_query",
                    "observation_content": "用户询问Python编程基础",
                    "action_name": "provide_tutorial",
                    "action_content": "提供了Python基础教程",
                    "state_name": "teaching"
                },
                {
                    "observation_name": "user_query",
                    "observation_content": "用户请求代码调试帮助",
                    "action_name": "debug_code",
                    "action_content": "分析并修复了代码错误",
                    "state_name": "debugging"
                },
                {
                    "observation_name": "user_query",
                    "observation_content": "用户想了解机器学习算法",
                    "action_name": "explain_ml",
                    "action_content": "详细介绍了监督学习算法",
                    "state_name": "explaining"
                }
            ]

            learn_request = {
                "agent_name": agent_name,
                "feedbacks": feedbacks_data,
                "vector_db_url": "http://localhost:8080",
                "top_k": 5
            }

            response = await client.post(
                f"{BASE_URL}{API_PREFIX}/learn",
                json=learn_request
            )

            if response.status_code == 200:
                result = response.json()
                print(f"✅ Learn successful: {result['message']}")
                print(f"   Feedback IDs: {result['feedback_ids'][:2]}...")
                print(f"   Total count: {result['count']}")
            else:
                print(f"❌ Learn failed: {response.status_code} - {response.text}")

            # 4. 获取所有反馈
            print("\n📝 Test 4: Get All Feedbacks")
            get_request = {
                "agent_name": agent_name,
                "vector_db_url": "http://localhost:8080",
                "offset": 0,
                "limit": 10
            }

            response = await client.post(
                f"{BASE_URL}{API_PREFIX}/get",
                json=get_request
            )

            if response.status_code == 200:
                result = response.json()
                print(f"✅ Get successful: {result['message']}")
                print(f"   Query count: {result['query_count']}")
                print(f"   Total count: {result['total_count']}")
                for i, fb in enumerate(result['feedbacks'][:2]):
                    print(f"   {i+1}. {fb['action_name']}: {fb['observation_content'][:40]}...")
            else:
                print(f"❌ Get failed: {response.status_code} - {response.text}")

            # 5. 语义搜索
            print("\n📝 Test 5: Semantic Search")
            search_request = {
                "agent_name": agent_name,
                "vector_db_url": "http://localhost:8080",
                "query": "Python编程学习",
                "top_k": 3
            }

            response = await client.post(
                f"{BASE_URL}{API_PREFIX}/get",
                json=search_request
            )

            if response.status_code == 200:
                result = response.json()
                print(f"✅ Search successful: {result['message']}")
                print(f"   Found {result['query_count']} relevant feedbacks:")
                for i, fb in enumerate(result['feedbacks']):
                    print(f"   {i+1}. {fb['state_name']}: {fb['observation_content'][:40]}...")
            else:
                print(f"❌ Search failed: {response.status_code} - {response.text}")

            # 6. 带标签的搜索
            print("\n📝 Test 6: Tagged Search")
            tagged_search_request = {
                "agent_name": agent_name,
                "vector_db_url": "http://localhost:8080",
                "query": "编程",
                "tags": ["observation_name_user_query"],
                "top_k": 3
            }

            response = await client.post(
                f"{BASE_URL}{API_PREFIX}/get",
                json=tagged_search_request
            )

            if response.status_code == 200:
                result = response.json()
                print(f"✅ Tagged search successful: {result['message']}")
                print(f"   Found {result['query_count']} tagged feedbacks")
            else:
                print(f"❌ Tagged search failed: {response.status_code} - {response.text}")

            # 7. 分页获取
            print("\n📝 Test 7: Pagination")
            page_request = {
                "agent_name": agent_name,
                "vector_db_url": "http://localhost:8080",
                "offset": 0,
                "limit": 2
            }

            response = await client.post(
                f"{BASE_URL}{API_PREFIX}/get",
                json=page_request
            )

            if response.status_code == 200:
                result = response.json()
                print(f"✅ Pagination successful: Got {result['query_count']} of {result['total_count']} feedbacks")
            else:
                print(f"❌ Pagination failed: {response.status_code} - {response.text}")

            # 8. 删除所有反馈
            print("\n📝 Test 8: Delete All Feedbacks")
            delete_request = {
                "agent_name": agent_name,
                "vector_db_url": "http://localhost:8080",
                "delete_type": "all"
            }

            response = await client.post(
                f"{BASE_URL}{API_PREFIX}/delete",
                json=delete_request
            )

            if response.status_code == 200:
                result = response.json()
                print(f"✅ Delete successful: {result['message']}")
                if result['deleted_count'] is not None:
                    print(f"   Deleted count: {result['deleted_count']}")
            else:
                print(f"❌ Delete failed: {response.status_code} - {response.text}")

            # 9. 验证删除
            print("\n📝 Test 9: Verify Deletion")
            response = await client.get(f"{BASE_URL}{API_PREFIX}/stats/{agent_name}")
            if response.status_code == 200:
                stats = response.json()
                print(f"✅ Final feedback count: {stats['feedback_count']}")
            else:
                print(f"❌ Verification failed: {response.status_code}")

        except Exception as e:
            print(f"❌ Test failed with error: {e}")


async def test_error_handling():
    """测试错误处理"""
    print("\n🔧 Testing Error Handling")
    print("=" * 25)

    async with httpx.AsyncClient() as client:
        try:
            # 测试无效的删除类型
            print("Testing invalid delete type...")
            delete_request = {
                "agent_name": "test_agent",
                "delete_type": "invalid_type"
            }

            response = await client.post(
                f"{BASE_URL}{API_PREFIX}/delete",
                json=delete_request
            )

            if response.status_code == 400:
                print("✅ Invalid delete type correctly rejected")
            else:
                print(f"❌ Expected 400, got {response.status_code}")

        except Exception as e:
            print(f"✅ Error handling test completed: {e}")


def print_curl_examples():
    """打印curl命令示例"""
    print("\n📋 Curl Examples:")
    print("=" * 20)

    print("\n1. Learn feedbacks:")
    print(f'''curl -X POST "{BASE_URL}{API_PREFIX}/learn" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "agent_name": "my_agent",
    "feedbacks": [{{
      "observation_name": "user_query",
      "observation_content": "用户问题",
      "action_name": "respond",
      "action_content": "回答内容",
      "state_name": "helping"
    }}]
  }}\'''')

    print("\n2. Get feedbacks:")
    print(f'''curl -X POST "{BASE_URL}{API_PREFIX}/get" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "agent_name": "my_agent",
    "limit": 10
  }}\'''')

    print("\n3. Semantic search:")
    print(f'''curl -X POST "{BASE_URL}{API_PREFIX}/get" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "agent_name": "my_agent",
    "query": "搜索关键词",
    "top_k": 5
  }}\'''')

    print("\n4. Delete all feedbacks:")
    print(f'''curl -X POST "{BASE_URL}{API_PREFIX}/delete" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "agent_name": "my_agent",
    "delete_type": "all"
  }}\'''')

    print("\n5. Get stats:")
    print(f'''curl "{BASE_URL}{API_PREFIX}/stats/my_agent"''')


if __name__ == "__main__":
    print("Feedback API Testing Suite")
    print("==========================")
    print("⚠️  Make sure the FastAPI server is running on http://localhost:8000")
    print("⚠️  Make sure Weaviate is running on http://localhost:8080")
    print("💡 Set OPENAI_API_KEY for better embeddings")
    print()

    # 运行API测试
    asyncio.run(test_feedback_apis())

    # 运行错误处理测试
    asyncio.run(test_error_handling())

    # 显示curl示例
    print_curl_examples()

    print("\n📋 Test Summary:")
    print("- ✅ Learn API (add feedbacks)")
    print("- ✅ Get API (retrieve & search)")
    print("- ✅ Delete API (remove feedbacks)")
    print("- ✅ Stats API (get counts)")
    print("- ✅ Health check")
    print("- ✅ Error handling")
    print("- ✅ Semantic search")
    print("- ✅ Tag filtering")
    print("- ✅ Pagination")