"""
新状态创建Agent

当没有预定义状态机时，根据历史记录动态创建新状态
"""

from typing import Optional

from agent_runtime.agents.base import BaseAgent
from agent_runtime.data_format.context import AIContext
from agent_runtime.data_format.fsm import State
from agent_runtime.clients.openai_llm_client import LLM
from agent_runtime.logging.logger import logger


class NewStateAgent(BaseAgent):
    """新状态创建Agent

    当没有预定义状态机时，根据历史记录动态创建新状态，
    生成合适的指令来指导下一步的动作选择
    """

    # 默认agent名称
    DEFAULT_AGENT_NAME = "new_state_agent"

    # 默认系统提示词
    DEFAULT_SYSTEM_PROMPT = """You are a professional state creation agent.
Your task is to analyze the conversation history and generate appropriate \
instructions for the next action when no predefined state machine exists.
You should focus on understanding the user's intent and providing clear, \
actionable guidance for the assistant's next response.
The recent actions are more important than previous actions."""

    # 默认用户提示词模板
    DEFAULT_USER_TEMPLATE = """You are a professional agent follow the \
instruction as following:
{{ global_prompt }}

The recent actions is more important than previous actions.
Each step includes a timestamp and may contain a user_message.
To make the best decision, consider how recently each user_message was made.

History of steps:
{{ history }}

Now, You need to generate assistant's instruction for the next action.
Please provide clear, specific guidance that will help the assistant \
respond appropriately to the user's needs."""

    def __init__(
        self,
        llm_engine: LLM,
        agent_name: Optional[str] = None,
        system_prompt: Optional[str] = None,
        user_prompt_template: Optional[str] = None,
    ):
        """
        初始化NewStateAgent

        Args:
            llm_engine: LLM客户端引擎
            agent_name: agent名称，如果不提供则使用默认值
            system_prompt: 自定义系统提示词，如果不提供则使用默认值
            user_prompt_template: 自定义用户提示词模板，如果不提供则使用默认值
        """
        super().__init__(
            agent_name=agent_name or self.DEFAULT_AGENT_NAME,
            llm_engine=llm_engine,
            system_prompt=system_prompt or self.DEFAULT_SYSTEM_PROMPT,
            user_prompt_template=(user_prompt_template or
                                  self.DEFAULT_USER_TEMPLATE),
        )

        logger.info("NewStateAgent initialized for new state creation")

    async def step(self, context: Optional[AIContext] = None,
                   **kwargs) -> State:
        """
        重构的step方法，专门用于新状态创建任务
        每次step都重新开始，不累积历史对话

        Args:
            context: 可选的外部上下文，如果为None则创建临时context
            **kwargs: 包含settings, memory等参数

        Returns:
            State: 新创建的状态

        Raises:
            ValueError: 当必需参数缺失时
        """
        # 提取必需参数
        settings = kwargs.get('settings')
        memory = kwargs.get('memory')

        if not settings or not memory:
            raise ValueError("settings and memory are required")

        # 如果没有提供外部上下文，创建一个新的临时上下文
        if context is None:
            working_context = AIContext()
        else:
            working_context: AIContext = context

        # 添加系统提示词
        working_context.add_system_prompt(self.system_prompt)

        # 渲染并添加用户提示词
        rendered_prompt = self._render_user_prompt(
            global_prompt=settings.global_prompt,
            history=memory.print_history()
        )
        working_context.add_user_prompt(rendered_prompt)

        try:
            # 调用LLM生成指令
            openai_messages = working_context.to_openai_format()
            response = await self.llm_engine.ask(
                messages=openai_messages,
                temperature=getattr(settings, 'temperature', 1.0),
            )


            # 创建新状态
            new_state = State(
                name="",
                scenario="",
                instruction=response or "",
            )

            logger.info(f"Created new state with instruction: "
                        f"{new_state.instruction[:100]}...")
            return new_state

        except Exception as e:
            logger.error(f"NewState step execution failed: {e}")
            raise