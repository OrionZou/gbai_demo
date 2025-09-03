from abc import ABC, abstractmethod
from typing import Any, Set
import threading
from jinja2 import Template, Environment, meta

from agent_runtime.clients.llm.openai_client import LLM
from agent_runtime.data_format.context_ai import AIContext
from agent_runtime.logging.logger import logger


class BaseAgent(ABC):
    """
    Agent基础类，提供通用的LLM交互功能

    Attributes:
        system_prompt (str): 系统提示词
        user_template (Template): 用户输入模板
        context (AIContext): AI对话上下文
        llm_engine (LLM): LLM客户端引擎
    """

    _instances = {}
    _lock = threading.Lock()
    _initialized = set()

    def __new__(cls, *args, **kwargs):
        # 从kwargs中获取agent_name，如果没有则从args中获取，最后使用类的默认值
        agent_name = kwargs.get("agent_name")
        if agent_name is None and args:
            agent_name = args[0] if isinstance(args[0], str) else None
        if agent_name is None:
            # 如果仍然没有agent_name，使用类的默认值（子类应该重写此属性）
            agent_name = getattr(cls, "DEFAULT_AGENT_NAME", cls.__name__.lower())

        with cls._lock:
            if agent_name not in cls._instances:
                cls._instances[agent_name] = super().__new__(cls)
            return cls._instances[agent_name]

    def __init__(
        self,
        agent_name: str = None,
        llm_engine: LLM = LLM(),
        system_prompt: str = "",
        user_prompt_template: str = "",
    ):
        """
        初始化Agent基础类

        Args:
            agent_name: Agent名称，用作单例标识，如果为None则使用类默认值
            llm_engine: LLM客户端引擎
            system_prompt: 系统提示词
            user_prompt_template: 用户提示词模板
        """
        # 确定最终的agent_name
        if agent_name is None:
            agent_name = getattr(
                self.__class__, "DEFAULT_AGENT_NAME", self.__class__.__name__.lower()
            )

        if agent_name in self._initialized:
            return

        self.agent_name = agent_name
        self.llm_engine = llm_engine
        self.system_prompt = system_prompt
        self.user_prompt_template = user_prompt_template
        self.user_template = (
            Template(user_prompt_template) if user_prompt_template else None
        )
        self.user_template_vars = self._get_user_template_vars()

        self.reset_context()
        self._initialized.add(agent_name)

    def _get_user_template_vars(self) -> Set:
        parsed_content = Environment().parse(self.user_prompt_template)
        return meta.find_undeclared_variables(parsed_content)

    def update_system_prompt(self, system_prompt: str) -> None:
        """
        更新系统提示词

        Args:
            system_prompt: 新的系统提示词
        """
        self.system_prompt = system_prompt
        logger.debug("System prompt updated")

    def update_user_template(self, user_prompt_template: str) -> None:
        """
        更新用户提示词模板

        Args:
            user_prompt_template: 新的用户提示词模板
        """
        self.user_prompt_template = user_prompt_template
        self.user_template = Template(user_prompt_template)
        self.user_template_vars = self._get_user_template_vars()
        logger.debug("User prompt template updated")

    def _render_user_prompt(self, **kwargs) -> str:
        """
        渲染用户提示词
        Args:
            **kwargs: 模板变量

        Returns:
            渲染后的用户提示词

        Raises:
            ValueError: 当用户模板未设置时
            ValueError: 当缺少必要的模板变量时
        """
        if not self.user_template:
            raise ValueError("User template is not set")
        # 检查是否提供了所有必需的模板变量
        missing_vars = self.user_template_vars - set(kwargs.keys())
        if missing_vars:
            raise ValueError(f"Missing required template variables: {missing_vars}")
        try:
            rendered_prompt = self.user_template.render(**kwargs)
            return rendered_prompt
        except Exception as e:
            logger.error(f"Failed to render user prompt template: {e}")
            raise ValueError(f"Template rendering failed: {e}")

    def reset_context(self) -> None:
        """重置对话上下文"""
        self.context = AIContext()
        self.context.add_system_prompt(self.system_prompt)
        logger.debug("Context reset")

    def update_context(self, context: AIContext) -> None:
        """更新对话上下文"""
        self.context = context
        logger.debug("Context updated")

    @abstractmethod
    async def step(self, context: AIContext = None, **kwargs) -> Any:
        """
        执行一步Agent推理

        Args:
            context: 可选的外部上下文，如果提供则临时使用
            **kwargs: 用户提示词模板的渲染参数

        Returns:
            LLM的响应结果
        """
        ...
