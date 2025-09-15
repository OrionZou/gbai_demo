"""
Agent Prompt Management Service

提供查看和更新所有/指定agent的system/user prompt功能
"""

from typing import Dict, List, Optional, Type, Any
from pydantic import BaseModel, Field, ConfigDict

from agent_runtime.clients.openai_llm_client import LLM
from agent_runtime.agents.base import BaseAgent
from agent_runtime.agents.reward_agent import RewardAgent
from agent_runtime.agents.agg_chapters_agent import AggChaptersAgent
from agent_runtime.agents.gen_chpt_p_agent import GenChptPAgent
from agent_runtime.agents.chapter_classification_agent import ChapterClassificationAgent
from agent_runtime.agents.chapter_structure_agent import ChapterStructureAgent
from agent_runtime.agents.bqa_agent import BQAAgent

from agent_runtime.logging.logger import logger


class AgentPromptInfo(BaseModel):
    """Agent提示词信息"""

    model_config = ConfigDict(extra="forbid", strict=True)

    agent_name: str = Field(..., description="Agent名称")
    system_prompt: str = Field(..., description="系统提示词")
    user_prompt_template: str = Field(..., description="用户提示词模板")
    template_variables: List[str] = Field(
        default_factory=list, description="用户模板中的变量列表"
    )


class AgentPromptUpdate(BaseModel):
    """Agent提示词更新请求"""

    model_config = ConfigDict(extra="forbid", strict=True)

    system_prompt: Optional[str] = Field(
        None, description="新的系统提示词，如果为None则不更新"
    )
    user_prompt_template: Optional[str] = Field(
        None, description="新的用户提示词模板，如果为None则不更新"
    )


class AgentPromptService:
    """Agent提示词管理服务"""

    # Agent名称到类的映射
    AGENT_CLASSES: Dict[str, Type[BaseAgent]] = {
        "reward_agent": RewardAgent,
        "agg_chapters_agent": AggChaptersAgent,
        "gen_chpt_p_agent": GenChptPAgent,
        "chpt_structure_agent": ChapterStructureAgent,
        "chpt_chassification_agent": ChapterClassificationAgent,
        "bpa_agent": BQAAgent,
        # 可以在这里添加更多Agent映射
        # "chat_agent": ChatAgent,
        # "task_agent": TaskAgent,
    }

    def __init__(self, llm_client: LLM):
        """
        初始化Agent提示词管理服务

        Args:
            llm_client: LLM客户端
        """
        self.llm_client = llm_client
        
        # 初始化全局上下文
        from agent_runtime.data_format.context import AIContext
        self.global_context = AIContext()
        self.global_context.add_system_prompt("你是一个专业的Agent提示词管理助手，负责查看、更新和验证各种Agent的系统提示词和用户提示词模板。")
        
        logger.info("AgentPromptService initialized with global context")

    def get_global_context(self):
        """获取全局上下文"""
        return self.global_context
    
    def update_global_context(self, context) -> None:
        """更新全局上下文"""
        self.global_context = context
        logger.info("Global context updated for AgentPromptService")

    def _get_or_create_agent(self, agent_name: str) -> BaseAgent:
        """
        获取或创建Agent实例（利用单例模式）

        Args:
            agent_name: Agent名称

        Returns:
            Agent实例
        """
        if agent_name not in self.AGENT_CLASSES:
            raise ValueError(f"Unsupported agent: {agent_name}")

        agent_class = self.AGENT_CLASSES[agent_name]
        # 利用BaseAgent的单例模式，相同agent_name会返回同一实例
        agent = agent_class(agent_name=agent_name, llm_engine=self.llm_client)
        logger.debug(f"Got or created agent instance: {agent_name}")
        return agent

    def get_supported_agent_names(self) -> List[str]:
        """
        获取支持的Agent名称列表

        Returns:
            支持的Agent名称列表
        """
        return list(self.AGENT_CLASSES.keys())

    def get_agent_prompt_info(self, agent_name: str) -> AgentPromptInfo:
        """
        获取指定Agent的提示词信息

        Args:
            agent_name: Agent名称

        Returns:
            Agent提示词信息
        """
        agent = self._get_or_create_agent(agent_name)

        # 获取模板变量
        template_vars = (
            list(agent.user_template_vars)
            if hasattr(agent, "user_template_vars")
            else []
        )

        return AgentPromptInfo(
            agent_name=agent.agent_name,
            system_prompt=agent.system_prompt,
            user_prompt_template=agent.user_prompt_template,
            template_variables=template_vars,
        )

    def get_all_agents_prompt_info(self) -> Dict[str, AgentPromptInfo]:
        """
        获取所有支持的Agent的提示词信息

        Returns:
            所有Agent的提示词信息字典，key为agent_name
        """
        result = {}
        for agent_name in self.AGENT_CLASSES.keys():
            result[agent_name] = self.get_agent_prompt_info(agent_name)

        logger.info(f"Retrieved prompt info for {len(result)} agents")
        return result

    def update_agent_prompts(
        self, agent_name: str, update_request: AgentPromptUpdate
    ) -> AgentPromptInfo:
        """
        更新指定Agent的提示词

        Args:
            agent_name: Agent名称
            update_request: 更新请求

        Returns:
            更新后的Agent提示词信息
        """
        agent = self._get_or_create_agent(agent_name)

        updated_fields = []

        # 更新系统提示词
        if update_request.system_prompt is not None:
            agent.update_system_prompt(update_request.system_prompt)
            updated_fields.append("system_prompt")

        # 更新用户提示词模板
        if update_request.user_prompt_template is not None:
            agent.update_user_template(update_request.user_prompt_template)
            updated_fields.append("user_prompt_template")

        logger.info(f"Updated {agent_name} prompts. Fields: {updated_fields}")

        # 返回更新后的信息
        return self.get_agent_prompt_info(agent_name)

    def reset_agent_to_default(self, agent_name: str) -> AgentPromptInfo:
        """
        重置指定Agent的提示词为默认值

        Args:
            agent_name: Agent名称

        Returns:
            重置后的Agent提示词信息
        """
        # 从单例缓存中移除实例，下次获取时会创建新的默认实例
        if agent_name in BaseAgent._instances:
            del BaseAgent._instances[agent_name]
        if agent_name in BaseAgent._initialized:
            BaseAgent._initialized.remove(agent_name)

        logger.info(f"Reset {agent_name} prompts to default")

        # 返回默认的Agent信息
        return self.get_agent_prompt_info(agent_name)

    def validate_template_variables(
        self, agent_name: str, test_variables: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        验证模板变量是否有效

        Args:
            agent_name: Agent名称
            test_variables: 测试变量

        Returns:
            验证结果，包含是否有效和错误信息
        """
        agent = self._get_or_create_agent(agent_name)

        result = {
            "valid": False,
            "missing_variables": [],
            "extra_variables": [],
            "rendered_preview": None,
            "error": None,
        }

        try:
            # 检查缺失的变量
            required_vars = (
                agent.user_template_vars
                if hasattr(agent, "user_template_vars")
                else set()
            )
            provided_vars = set(test_variables.keys())

            missing_vars = required_vars - provided_vars
            extra_vars = provided_vars - required_vars

            result["missing_variables"] = list(missing_vars)
            result["extra_variables"] = list(extra_vars)

            # 如果没有缺失变量，尝试渲染预览
            if not missing_vars:
                rendered = agent._render_user_prompt(**test_variables)
                result["rendered_preview"] = rendered
                result["valid"] = True

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Template validation failed for {agent_name}: {e}")

        return result
