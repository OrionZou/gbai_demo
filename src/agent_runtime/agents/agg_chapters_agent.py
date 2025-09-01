"""
AggChaptersAgent - 章节聚合Agent

基于BaseAgent实现，专门用于将问答对按语义相似度聚合成章节结构
"""

from typing import List, Tuple, Optional, Dict, Any
from jinja2 import Template

from agent_runtime.agents.base import BaseAgent
from agent_runtime.clients.llm.openai_client import LLM
from agent_runtime.data_format.context_ai import AIContext
from agent_runtime.clients.utils import normalize_to_list
from agent_runtime.logging.logger import logger


class AggChaptersAgent(BaseAgent):
    """
    章节聚合Agent
    专门负责将问答对按语义相似度聚合成有意义的章节结构
    """
    
    # 默认agent名称
    DEFAULT_AGENT_NAME = "agg_chapters_agent"

    # 默认系统提示词
    DEFAULT_SYSTEM_PROMPT = """你是优秀的技术编辑，擅长为知识手册将 Q&A 素材进行主题化分章与聚合。
要求：
1) 先观察所有 Q 与 A 的主题相似度，进行语义聚类；
2) 生成清晰、去重、非重叠的章节名；
3) 每个章节配简短的聚合原因；
4) 严格输出 JSON，字段为：chapters=[{chapter_name, reason, qas=[{q,a}]}];"""

    # 默认用户提示词模板
    DEFAULT_USER_TEMPLATE = """请将以下 Q&A 素材聚合为章节 JSON：

【输入 Q&A 列表】：
{% for qa in qas %}
{{ loop.index }}. {{ qa }}
{% endfor %}

【补充约束】：
{% if extra_instructions -%}
{{ extra_instructions }}
{%- endif %}

【输出 JSON 严格格式】：
{
  "chapters": [
    {
      "chapter_name": "...",
      "reason": "...",
      "qas": [{"q":"...", "a":"..."}]
    }
  ]
}
"""

    def __init__(
        self,
        llm_engine: LLM,
        agent_name: Optional[str] = None,
        system_prompt: Optional[str] = None,
        user_prompt_template: Optional[str] = None,
    ):
        """
        初始化AggChaptersAgent

        Args:
            llm_engine: LLM客户端引擎
            agent_name: agent名称，如果不提供则使用默认值"agg_chapters_agent"
            system_prompt: 自定义系统提示词，如果不提供则使用默认值
            user_prompt_template: 自定义用户提示词模板，如果不提供则使用默认值
        """
        super().__init__(
            agent_name=agent_name,
            llm_engine=llm_engine,
            system_prompt=system_prompt or self.DEFAULT_SYSTEM_PROMPT,
            user_prompt_template=user_prompt_template or self.DEFAULT_USER_TEMPLATE,
        )

        logger.info("AggChaptersAgent initialized for chapter aggregation")

    async def step(self, context: Optional[AIContext] = None, **kwargs) -> List[Dict[str, Any]]:
        """
        执行章节聚合任务
        
        Args:
            context: 可选的外部上下文
            **kwargs: 包含qas和extra_instructions等参数
            
        Expected kwargs:
            qas (List[Tuple[str, str]]): 问答对列表
            extra_instructions (str, optional): 额外的聚合指令
            
        Returns:
            List[Dict[str, Any]]: 聚合后的章节数据列表
        """
        # 获取参数
        qas = kwargs.get('qas', [])
        extra_instructions = kwargs.get('extra_instructions', '')
        
        if not qas:
            raise ValueError("qas parameter is required for chapter aggregation")
        
        # 如果没有提供外部上下文，创建新的上下文
        if context is None:
            working_context = AIContext()
            working_context.add_system_prompt(self.system_prompt)
        else:
            working_context = context
            
        # 渲染用户提示词
        rendered_prompt = self._render_user_prompt(
            qas=qas, 
            extra_instructions=extra_instructions
        )
        working_context.add_user_prompt(rendered_prompt)
        
        try:
            logger.debug("Starting chapter aggregation with LLM")
            openai_messages = working_context.to_openai_format()
            
            # 调用LLM进行结构化输出
            response_content = await self.llm_engine.structured_output_old(
                messages=openai_messages
            )
            
            # 规范化输出为列表
            json_list = normalize_to_list(response_content)
            logger.debug(f"Chapter aggregation result: {json_list}")
            
            return json_list
            
        except Exception as e:
            logger.error(f"Chapter aggregation failed: {e}")
            raise

    async def aggregate_chapters(
        self, 
        qas: List[Tuple[str, str]], 
        extra_instructions: str = ""
    ) -> List[Dict[str, Any]]:
        """
        章节聚合的便捷方法
        
        Args:
            qas: 问答对列表，每个元组包含(问题, 答案)
            extra_instructions: 额外的聚合指令
            
        Returns:
            List[Dict[str, Any]]: 聚合后的章节数据列表
        """
        return await self.step(qas=qas, extra_instructions=extra_instructions)