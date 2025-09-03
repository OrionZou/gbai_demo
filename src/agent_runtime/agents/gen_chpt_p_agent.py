"""
GenChptPAgent - 章节提示词生成Agent

基于BaseAgent实现，专门用于为章节生成专用的辅助提示词
"""

from typing import Optional, List, Dict, Any

from agent_runtime.agents.base import BaseAgent
from agent_runtime.clients.llm.openai_client import LLM
from agent_runtime.data_format.context_ai import AIContext
from agent_runtime.logging.logger import logger


class GenChptPAgent(BaseAgent):
    """
    章节提示词生成Agent
    专门负责为章节生成专用的辅助提示词，指导LLM基于特定章节回答问题
    """

    # 默认agent名称
    DEFAULT_AGENT_NAME = "gen_chpt_p_agent"

    # 默认系统提示词
    DEFAULT_SYSTEM_PROMPT = """你是提示词工程专家与技术编辑。目标：为给定的章节，产出一个'辅助提示词 prompt'，该提示词将与 {chapter_name, q} 一起提供给 LLM，用于更准确地生成 a。

要求：
 - 严格限定知识范围：只依据本章节的主题与提供的 Q&A 语料，不得臆造外部事实；
 - 当问题超出本章节范围或缺乏依据时，应指导回答者明确说明'依据不足'并给出继续提问方向；
 - 语气专业、克制、面向技术文档；
 - 输出语言与输入示例主要语言一致（若示例以中文为主则输出中文）；
 - 优先使用示例中的术语与命名，保持一致性；
 - 回答策略：若是概念性问题先给定义与边界；若是流程/配置问题给步骤或要点清单；
 - 禁止包含与问题无关的客套话、个人观点、链接；"""

    # 默认用户提示词模板
    DEFAULT_USER_TEMPLATE = """章节名称：{{ chapter_name }}

{% if reason %}
章节聚合理由：{{ reason }}
{% endif %}

【补充约束】：
{% if extra_instructions -%}
{{ extra_instructions }}
{%- endif %}

【章节相关示例】：
{% for qa in qas %}
{{ loop.index }}. {{ qa }}
{% endfor %}

请生成一个可复用的章节级辅助提示词，用于指导 LLM 依据该章节回答此主题下的问题。"""

    def __init__(
        self,
        llm_engine: LLM,
        agent_name: Optional[str] = None,
        system_prompt: Optional[str] = None,
        user_prompt_template: Optional[str] = None,
    ):
        """
        初始化GenChptPAgent

        Args:
            llm_engine: LLM客户端引擎
            agent_name: agent名称，如果不提供则使用默认值"gen_chpt_p_agent"
            system_prompt: 自定义系统提示词，如果不提供则使用默认值
            user_prompt_template: 自定义用户提示词模板，如果不提供则使用默认值
        """
        super().__init__(
            agent_name=agent_name,
            llm_engine=llm_engine,
            system_prompt=system_prompt or self.DEFAULT_SYSTEM_PROMPT,
            user_prompt_template=user_prompt_template or self.DEFAULT_USER_TEMPLATE,
        )

        logger.info("GenChptPAgent initialized for chapter prompt generation")

    async def step(self, context: Optional[AIContext] = None, **kwargs) -> str:
        """
        执行章节提示词生成任务

        Args:
            context: 可选的外部上下文
            **kwargs: 包含章节信息的参数

        Expected kwargs:
            chapter_name (str): 章节名称
            reason (str, optional): 章节聚合理由
            qas (List): 章节包含的问答对
            extra_instructions (str, optional): 额外的生成指令

        Returns:
            str: 生成的章节提示词
        """
        # 获取参数
        chapter_name = kwargs.get("chapter_name")
        reason = kwargs.get("reason", "")
        qas = kwargs.get("qas", [])
        extra_instructions = kwargs.get("extra_instructions", "")

        if not chapter_name:
            raise ValueError("chapter_name parameter is required for prompt generation")

        # 如果没有提供外部上下文，创建新的上下文
        if context is None:
            working_context = AIContext()
            working_context.add_system_prompt(self.system_prompt)
        else:
            working_context = context

        # 渲染用户提示词
        rendered_prompt = self._render_user_prompt(
            chapter_name=chapter_name,
            reason=reason,
            qas=qas,
            extra_instructions=extra_instructions,
        )
        working_context.add_user_prompt(rendered_prompt)

        try:
            logger.debug(f"Generating prompt for chapter: {chapter_name}")
            openai_messages = working_context.to_openai_format()

            # 调用LLM生成提示词
            prompt_content = await self.llm_engine.ask(
                messages=openai_messages, temperature=0.3
            )

            logger.debug(
                f"Generated prompt for chapter '{chapter_name}': {prompt_content[:100]}..."
            )
            return prompt_content

        except Exception as e:
            logger.error(f"Chapter prompt generation failed for '{chapter_name}': {e}")
            raise

    async def generate_chapter_prompt(
        self,
        chapter_name: str,
        qas: List[Dict[str, str]],
        reason: str = "",
        extra_instructions: str = "",
    ) -> str:
        """
        章节提示词生成的便捷方法

        Args:
            chapter_name: 章节名称
            qas: 章节包含的问答对列表
            reason: 章节聚合理由
            extra_instructions: 额外的生成指令

        Returns:
            str: 生成的章节提示词
        """
        return await self.step(
            chapter_name=chapter_name,
            reason=reason,
            qas=qas,
            extra_instructions=extra_instructions,
        )
