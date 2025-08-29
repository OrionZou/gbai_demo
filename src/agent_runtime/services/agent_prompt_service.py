"""
Agent Prompt Management Service

提供查看和更新所有/指定agent的system/user prompt功能
"""

from typing import Dict, List, Optional, Type, Any
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict

from agent_runtime.clients.llm.openai_client import LLM
from agent_runtime.agents.base import BaseAgent
from agent_runtime.agents.reward_agent import RewardAgent
from agent_runtime.logging.logger import logger


class AgentType(str, Enum):
    """支持的Agent类型"""
    REWARD_AGENT = "reward_agent"
    # 可以在这里添加更多Agent类型
    # CHAT_AGENT = "chat_agent"
    # TASK_AGENT = "task_agent"


class AgentPromptInfo(BaseModel):
    """Agent提示词信息"""
    model_config = ConfigDict(extra="forbid", strict=True)

    agent_name: str = Field(..., description="Agent名称")
    agent_type: str = Field(..., description="Agent类型")
    system_prompt: str = Field(..., description="系统提示词")
    user_prompt_template: str = Field(..., description="用户提示词模板")
    template_variables: List[str] = Field(
        default_factory=list,
        description="用户模板中的变量列表"
    )


class AgentPromptUpdate(BaseModel):
    """Agent提示词更新请求"""
    model_config = ConfigDict(extra="forbid", strict=True)

    system_prompt: Optional[str] = Field(
        None,
        description="新的系统提示词，如果为None则不更新"
    )
    user_prompt_template: Optional[str] = Field(
        None,
        description="新的用户提示词模板，如果为None则不更新"
    )


class AgentPromptService:
    """Agent提示词管理服务"""

    # Agent类型到类的映射
    AGENT_CLASSES: Dict[AgentType, Type[BaseAgent]] = {
        AgentType.REWARD_AGENT: RewardAgent,
        # 可以在这里添加更多Agent映射
        # AgentType.CHAT_AGENT: ChatAgent,
        # AgentType.TASK_AGENT: TaskAgent,
    }

    def __init__(self, llm_client: LLM):
        """
        初始化Agent提示词管理服务

        Args:
            llm_client: LLM客户端
        """
        self.llm_client = llm_client
        self._agent_instances: Dict[str, BaseAgent] = {}
        logger.info("AgentPromptService initialized")

    def _get_or_create_agent(self, agent_type: AgentType) -> BaseAgent:
        """
        获取或创建Agent实例

        Args:
            agent_type: Agent类型

        Returns:
            Agent实例
        """
        if agent_type not in self._agent_instances:
            agent_class = self.AGENT_CLASSES[agent_type]
            # RewardAgent doesn't need agent_name as it's set in its __init__
            self._agent_instances[agent_type] = agent_class(
                llm_engine=self.llm_client
            )
            logger.debug(f"Created new agent instance: {agent_type}")

        return self._agent_instances[agent_type]

    def get_supported_agent_types(self) -> List[str]:
        """
        获取支持的Agent类型列表

        Returns:
            支持的Agent类型列表
        """
        return [agent_type.value for agent_type in AgentType]

    def get_agent_prompt_info(self, agent_type: AgentType) -> AgentPromptInfo:
        """
        获取指定Agent的提示词信息

        Args:
            agent_type: Agent类型

        Returns:
            Agent提示词信息
        """
        agent = self._get_or_create_agent(agent_type)

        # 获取模板变量
        template_vars = list(agent.user_template_vars) if hasattr(
            agent, 'user_template_vars'
        ) else []

        return AgentPromptInfo(
            agent_name=agent.agent_name,
            agent_type=agent_type.value,
            system_prompt=agent.system_prompt,
            user_prompt_template=agent.user_prompt_template,
            template_variables=template_vars
        )

    def get_all_agents_prompt_info(self) -> Dict[str, AgentPromptInfo]:
        """
        获取所有支持的Agent的提示词信息

        Returns:
            所有Agent的提示词信息字典，key为agent_type
        """
        result = {}
        for agent_type in AgentType:
            result[agent_type.value] = self.get_agent_prompt_info(agent_type)

        logger.info(f"Retrieved prompt info for {len(result)} agents")
        return result

    def update_agent_prompts(
        self,
        agent_type: AgentType,
        update_request: AgentPromptUpdate
    ) -> AgentPromptInfo:
        """
        更新指定Agent的提示词

        Args:
            agent_type: Agent类型
            update_request: 更新请求

        Returns:
            更新后的Agent提示词信息
        """
        agent = self._get_or_create_agent(agent_type)

        updated_fields = []

        # 更新系统提示词
        if update_request.system_prompt is not None:
            agent.update_system_prompt(update_request.system_prompt)
            updated_fields.append("system_prompt")

        # 更新用户提示词模板
        if update_request.user_prompt_template is not None:
            agent.update_user_template(update_request.user_prompt_template)
            updated_fields.append("user_prompt_template")

        logger.info(
            f"Updated {agent_type.value} prompts. Fields: {updated_fields}"
        )

        # 返回更新后的信息
        return self.get_agent_prompt_info(agent_type)

    def update_multiple_agents_prompts(
        self,
        updates: Dict[AgentType, AgentPromptUpdate]
    ) -> Dict[str, AgentPromptInfo]:
        """
        批量更新多个Agent的提示词

        Args:
            updates: Agent类型到更新请求的映射

        Returns:
            更新后的所有Agent提示词信息
        """
        result = {}

        for agent_type, update_request in updates.items():
            result[agent_type.value] = self.update_agent_prompts(
                agent_type,
                update_request
            )

        logger.info(f"Batch updated prompts for {len(updates)} agents")
        return result

    def reset_agent_to_default(self, agent_type: AgentType) -> AgentPromptInfo:
        """
        重置指定Agent的提示词为默认值

        Args:
            agent_type: Agent类型

        Returns:
            重置后的Agent提示词信息
        """
        # 删除现有实例，下次获取时会创建新的默认实例
        if agent_type in self._agent_instances:
            del self._agent_instances[agent_type]

        logger.info(f"Reset {agent_type.value} prompts to default")

        # 返回默认的Agent信息
        return self.get_agent_prompt_info(agent_type)

    def validate_template_variables(
        self,
        agent_type: AgentType,
        test_variables: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        验证模板变量是否有效

        Args:
            agent_type: Agent类型
            test_variables: 测试变量

        Returns:
            验证结果，包含是否有效和错误信息
        """
        agent = self._get_or_create_agent(agent_type)

        result = {
            "valid": False,
            "missing_variables": [],
            "extra_variables": [],
            "rendered_preview": None,
            "error": None
        }

        try:
            # 检查缺失的变量
            required_vars = agent.user_template_vars if hasattr(
                agent, 'user_template_vars'
            ) else set()
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
            logger.error(
                f"Template validation failed for {agent_type.value}: {e}"
            )

        return result
