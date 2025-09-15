"""
Agent Prompt Service 使用示例

展示如何使用 AgentPromptService 来查看和更新 agent 的提示词
"""

import asyncio
from agent_runtime.clients.openai_llm_client import LLM
from agent_runtime.services.agent_prompt_service import (
    AgentPromptService,
    AgentType,
    AgentPromptUpdate
)
from agent_runtime.logging.logger import logger


async def demo_agent_prompt_service():
    """演示 AgentPromptService 的各种功能"""
    
    # 初始化 LLM 客户端（这里需要根据实际情况配置）
    llm_client = LLM()  # 假设有默认配置
    
    # 创建 AgentPromptService 实例
    prompt_service = AgentPromptService(llm_client)
    
    print("=== Agent Prompt Service 演示 ===\n")
    
    # 1. 查看支持的 Agent 类型
    print("1. 支持的 Agent 类型:")
    supported_types = prompt_service.get_supported_agent_types()
    for agent_type in supported_types:
        print(f"   - {agent_type}")
    print()
    
    # 2. 查看所有 Agent 的提示词信息
    print("2. 查看所有 Agent 的提示词信息:")
    all_agents_info = prompt_service.get_all_agents_prompt_info()
    for agent_type, info in all_agents_info.items():
        print(f"   Agent: {agent_type}")
        print(f"   Name: {info.agent_name}")
        print(f"   System Prompt: {info.system_prompt[:100]}...")
        print(f"   Template Variables: {info.template_variables}")
        print()
    
    # 3. 查看特定 Agent 的详细信息
    print("3. 查看 RewardAgent 的详细信息:")
    reward_agent_info = prompt_service.get_agent_prompt_info(
        AgentType.REWARD_AGENT
    )
    print(f"   Agent Name: {reward_agent_info.agent_name}")
    print(f"   Agent Type: {reward_agent_info.agent_type}")
    print(f"   System Prompt Length: {len(reward_agent_info.system_prompt)}")
    print(f"   Template Variables: {reward_agent_info.template_variables}")
    print()
    
    # 4. 验证模板变量
    print("4. 验证模板变量:")
    test_vars = {
        "question": "测试问题",
        "target_answer": "目标答案",
        "candidates": ["候选答案1", "候选答案2"]
    }
    validation_result = prompt_service.validate_template_variables(
        AgentType.REWARD_AGENT,
        test_vars
    )
    print(f"   Valid: {validation_result['valid']}")
    print(f"   Missing Variables: {validation_result['missing_variables']}")
    print(f"   Extra Variables: {validation_result['extra_variables']}")
    if validation_result['rendered_preview']:
        print(f"   Rendered Preview: {validation_result['rendered_preview'][:200]}...")
    print()
    
    # 5. 更新 Agent 的提示词
    print("5. 更新 RewardAgent 的系统提示词:")
    new_system_prompt = """
你是改进版的答案一致性评审器。你需要更加仔细地分析每个候选答案。
标签定义与之前相同，但请提供更详细的分析理由。
    """.strip()
    
    update_request = AgentPromptUpdate(
        system_prompt=new_system_prompt
    )
    
    updated_info = prompt_service.update_agent_prompts(
        AgentType.REWARD_AGENT,
        update_request
    )
    print(f"   Updated System Prompt: {updated_info.system_prompt[:100]}...")
    print()
    
    # 6. 重置 Agent 到默认状态
    print("6. 重置 RewardAgent 到默认状态:")
    reset_info = prompt_service.reset_agent_to_default(AgentType.REWARD_AGENT)
    print(f"   Reset System Prompt: {reset_info.system_prompt[:100]}...")
    print()
    
    # 7. 批量更新多个 Agent（如果有多个的话）
    print("7. 批量更新演示:")
    batch_updates = {
        AgentType.REWARD_AGENT: AgentPromptUpdate(
            system_prompt="批量更新的系统提示词测试"
        )
    }
    
    batch_results = prompt_service.update_multiple_agents_prompts(batch_updates)
    print(f"   批量更新了 {len(batch_results)} 个 Agent")
    for agent_type, info in batch_results.items():
        print(f"   {agent_type}: {info.system_prompt[:50]}...")
    
    print("\n=== 演示完成 ===")


if __name__ == "__main__":
    # 运行演示
    asyncio.run(demo_agent_prompt_service())