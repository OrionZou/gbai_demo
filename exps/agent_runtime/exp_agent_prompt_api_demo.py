"""
Agent Prompt Management API 测试脚本

展示如何通过API查看和更新Agent提示词
"""

import asyncio
import json
from typing import Dict, Any
import sys
import os

# 添加src目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from agent_runtime.clients.llm.openai_client import LLM
from agent_runtime.services.agent_prompt_service import (
    AgentPromptService,
    AgentType,
    AgentPromptUpdate
)
from agent_runtime.logging.logger import logger


async def demo_agent_prompt_api():
    """演示Agent Prompt Management API功能"""
    
    print("=== Agent Prompt Management API 演示 ===\n")
    
    # 初始化服务（模拟API后端的初始化）
    llm_client = LLM()
    agent_prompt_service = AgentPromptService(llm_client)
    
    # 1. 获取支持的Agent类型
    print("1. 📋 获取支持的Agent类型:")
    supported_types = agent_prompt_service.get_supported_agent_types()
    print(f"   支持的Agent类型: {supported_types}")
    print()
    
    # 2. 获取所有Agent的提示词信息
    print("2. 📄 获取所有Agent的提示词信息:")
    all_agents_info = agent_prompt_service.get_all_agents_prompt_info()
    for agent_type, info in all_agents_info.items():
        print(f"   🤖 Agent: {agent_type}")
        print(f"      名称: {info.agent_name}")
        print(f"      系统提示词长度: {len(info.system_prompt)} 字符")
        print(f"      用户模板变量: {info.template_variables}")
        print(f"      用户模板长度: {len(info.user_prompt_template)} 字符")
        print()
    
    # 3. 获取特定Agent的详细信息（模拟GET /agents/reward_agent/prompts）
    print("3. 🎯 获取RewardAgent的详细信息:")
    reward_info = agent_prompt_service.get_agent_prompt_info(AgentType.REWARD_AGENT)
    print(f"   Agent名称: {reward_info.agent_name}")
    print(f"   Agent类型: {reward_info.agent_type}")
    print(f"   模板变量: {reward_info.template_variables}")
    print(f"   系统提示词预览: {reward_info.system_prompt[:200]}...")
    print(f"   用户模板预览: {reward_info.user_prompt_template[:200]}...")
    print()
    
    # 4. 验证模板变量（模拟POST /agents/reward_agent/prompts/validate）
    print("4. ✅ 验证模板变量:")
    test_variables = {
        "question": "什么是机器学习？",
        "target_answer": "机器学习是人工智能的一个分支",
        "candidates": [
            "机器学习是AI的子领域",
            "机器学习用于数据分析",
            "机器学习是编程技术"
        ]
    }
    
    validation_result = agent_prompt_service.validate_template_variables(
        AgentType.REWARD_AGENT, test_variables
    )
    print(f"   ✓ 验证有效: {validation_result['valid']}")
    print(f"   ⚠ 缺失变量: {validation_result['missing_variables']}")
    print(f"   ➕ 多余变量: {validation_result['extra_variables']}")
    if validation_result['rendered_preview']:
        print(f"   👀 渲染预览: {validation_result['rendered_preview'][:300]}...")
    print()
    
    # 5. 更新Agent提示词（模拟PUT /agents/reward_agent/prompts）
    print("5. 🔄 更新RewardAgent的系统提示词:")
    new_system_prompt = """
你是高级答案一致性评审器。请仔细分析每个候选答案与目标答案的语义匹配度。

评审标准：
- equivalent：语义完全等价
- partially_equivalent：主要内容一致，但有细节差异
- different：结论不同或矛盾
- unsupported：无关或不支持

请提供详细的分析理由。
    """.strip()
    
    update_request = AgentPromptUpdate(system_prompt=new_system_prompt)
    updated_info = agent_prompt_service.update_agent_prompts(
        AgentType.REWARD_AGENT, update_request
    )
    print(f"   ✓ 系统提示词已更新")
    print(f"   📝 新的系统提示词: {updated_info.system_prompt[:150]}...")
    print()
    
    # 6. 批量更新（模拟PUT /agents/prompts/batch）
    print("6. 📦 批量更新演示:")
    batch_updates = {
        AgentType.REWARD_AGENT: AgentPromptUpdate(
            user_prompt_template="""
评审任务：

问题：{{ question }}

目标答案：{{ target_answer }}

候选答案列表：
{% for candidate in candidates %}
{{ loop.index }}. {{ candidate }}
{% endfor %}

请按照标准格式输出JSON评审结果。
            """.strip()
        )
    }
    
    batch_results = agent_prompt_service.update_multiple_agents_prompts(batch_updates)
    print(f"   ✓ 批量更新了 {len(batch_results)} 个Agent")
    for agent_type, info in batch_results.items():
        print(f"   📄 {agent_type}: 用户模板已更新 ({len(info.user_prompt_template)} 字符)")
    print()
    
    # 7. 验证更新后的模板
    print("7. 🧪 验证更新后的模板:")
    validation_after_update = agent_prompt_service.validate_template_variables(
        AgentType.REWARD_AGENT, test_variables
    )
    print(f"   ✓ 更新后验证有效: {validation_after_update['valid']}")
    if validation_after_update['rendered_preview']:
        print(f"   👀 新模板渲染预览: {validation_after_update['rendered_preview'][:200]}...")
    print()
    
    # 8. 重置到默认状态（模拟POST /agents/reward_agent/prompts/reset）
    print("8. 🔄 重置RewardAgent到默认状态:")
    reset_info = agent_prompt_service.reset_agent_to_default(AgentType.REWARD_AGENT)
    print(f"   ✓ 已重置到默认状态")
    print(f"   📝 默认系统提示词: {reset_info.system_prompt[:150]}...")
    print()
    
    # 9. 模拟API响应格式
    print("9. 📡 模拟API响应格式:")
    api_response = {
        "agent_name": reset_info.agent_name,
        "agent_type": reset_info.agent_type,
        "system_prompt": reset_info.system_prompt,
        "user_prompt_template": reset_info.user_prompt_template,
        "template_variables": reset_info.template_variables,
        "timestamp": "2024-01-01T00:00:00Z",
        "version": "1.0.0"
    }
    print("   📋 API响应示例 (JSON格式):")
    print(f"   {json.dumps(api_response, ensure_ascii=False, indent=2)[:500]}...")
    
    print("\n=== API演示完成 ===")
    print("\n💡 可用的API端点:")
    print("   GET    /agents/types                     - 获取支持的Agent类型")
    print("   GET    /agents/prompts                   - 获取所有Agent提示词")
    print("   GET    /agents/{type}/prompts            - 获取指定Agent提示词")
    print("   PUT    /agents/{type}/prompts            - 更新指定Agent提示词")
    print("   PUT    /agents/prompts/batch             - 批量更新Agent提示词")
    print("   POST   /agents/{type}/prompts/reset      - 重置Agent提示词")
    print("   POST   /agents/{type}/prompts/validate   - 验证模板变量")


def test_api_error_handling():
    """测试API错误处理"""
    print("\n=== 错误处理测试 ===")
    
    llm_client = LLM()
    service = AgentPromptService(llm_client)
    
    # 测试无效的Agent类型
    try:
        # 这会抛出ValueError，在实际API中会被转换为400错误
        invalid_type = "invalid_agent"
        print(f"❌ 测试无效Agent类型: {invalid_type}")
        # 实际API会验证agent_type是否在AgentType枚举中
        if invalid_type not in [t.value for t in AgentType]:
            print(f"   ✓ 正确识别无效类型，应返回400错误")
    except Exception as e:
        print(f"   ⚠ 异常: {e}")
    
    # 测试模板变量验证错误
    try:
        print("❌ 测试缺失模板变量:")
        incomplete_vars = {"question": "test"}  # 缺少必需变量
        result = service.validate_template_variables(
            AgentType.REWARD_AGENT, incomplete_vars
        )
        print(f"   ✓ 验证结果: valid={result['valid']}, missing={result['missing_variables']}")
    except Exception as e:
        print(f"   ⚠ 异常: {e}")
    
    print("=== 错误处理测试完成 ===")


if __name__ == "__main__":
    # 运行演示
    asyncio.run(demo_agent_prompt_api())
    
    # 测试错误处理
    test_api_error_handling()