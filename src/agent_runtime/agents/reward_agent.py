"""
Reward Agent - 答案一致性评审器

基于BaseAgent实现，专门用于答案语义匹配度评审
"""

import json
from typing import Optional, List, Dict, Any
from agent_runtime.logging.logger import logger
from agent_runtime.agents.base import BaseAgent
from agent_runtime.clients.llm.openai_client import LLM
from agent_runtime.data_format.context_ai import AIContext
from agent_runtime.clients.utils import normalize_to_list


class RewardAgent(BaseAgent):
    """
    答案一致性评审Agent
    仅重构step方法，其他业务逻辑保留在RewardService中
    """
    
    # 默认agent名称
    DEFAULT_AGENT_NAME = "reward_agent"

    # 默认系统提示词
    DEFAULT_SYSTEM_PROMPT = """
你是答案一致性评审器。仅依据"目标答案"的含义来判断每个候选答案与其是否一致。
标签定义：
- equivalent：与目标答案事实与结论等价；措辞不同不影响含义/范围。
- partially_equivalent：主体一致，但范围/前提/时间/数量等有限定差异或缺失。
- different：结论不同或互相矛盾。
- unsupported：与问题或目标答案无关、空泛，或加入目标答案未支持的推断/闲聊。
要求：
- 输出 JSON，键为 label/confidence/reason。
- confidence 给出0-1之间的小数，随判断把握调整。
- reason 简洁中文说明关键差异点。
"""

    # 默认用户提示词模板
    DEFAULT_USER_TEMPLATE = """
问题：
{{ question }}

目标答案：
{{ target_answer }}

候选答案：
{% for ans in candidates %}
{{ loop.index }}. {{ ans }}
{% endfor %}

输出 JSON 格式的列表，列表元素表示每个候选答案：
[
{% for a in candidates %}
  {
    "index": {{ loop.index0 }},
    "label": "equivalent | partially_equivalent | different | unsupported",
    "confidence": 0.0-1.0,
    "reason": "简要中文理由"
  }{% if not loop.last %},{% endif %}
{% endfor %}
]
"""

    def __init__(
        self,
        llm_engine: LLM,
        agent_name: Optional[str] = None,
        system_prompt: Optional[str] = None,
        user_prompt_template: Optional[str] = None,
    ):
        """
        初始化RewardAgent

        Args:
            llm_engine: LLM客户端引擎
            agent_name: agent名称，如果不提供则使用默认值"reward_agent"
            system_prompt: 自定义系统提示词，如果不提供则使用默认值
            user_prompt_template: 自定义用户提示词模板，如果不提供则使用默认值
        """
        super().__init__(
            agent_name=agent_name,
            llm_engine=llm_engine,
            system_prompt=system_prompt or self.DEFAULT_SYSTEM_PROMPT,
            user_prompt_template=user_prompt_template or self.DEFAULT_USER_TEMPLATE,
        )

        logger.info("RewardAgent initialized for answer consistency evaluation")

    async def step(self, context=None, **kwargs) -> List[Dict[str, Any]]:
        """
        重构的step方法，专门用于答案比较任务
        每次step都重新开始，不累积历史对话

        Args:
            context: 可选的外部上下文
            **kwargs: 包含question, target_answer, candidates等参数

        Returns:
            LLM的JSON响应内容
        """
        # 如果没有提供外部上下文，创建一个新的临时上下文
        if context is None:
            working_context = self.context
        else:
            working_context = context

        try:
            openai_messages = working_context.to_openai_format()
            response_content = await self.llm_engine.structured_output_old(
                messages=openai_messages
            )
            json_list = normalize_to_list(response_content)
            logger.debug(f"json_list:{json_list}")
            return json_list
        except Exception as e:
            logger.error(f"Reward step execution failed: {e}")
            raise
