"""
状态选择Agent

负责根据当前状态、历史记录和反馈信息选择下一个最合适的状态
"""

import yaml
from typing import Optional

from agent_runtime.agents.base import BaseAgent
from agent_runtime.data_format.context import AIContext
from agent_runtime.data_format.fsm import State
from agent_runtime.utils.text_utils import safe_to_int
from agent_runtime.clients.openai_llm_client import LLM
from agent_runtime.logging.logger import logger


class StateSelectAgent(BaseAgent):
    """状态选择Agent

    根据当前状态、历史记录和反馈信息，使用LLM选择下一个最合适的状态
    """

    # 默认agent名称
    DEFAULT_AGENT_NAME = "state_select_agent"

    # 默认系统提示词
    DEFAULT_SYSTEM_PROMPT = """You are a professional state selection agent.
Your task is to analyze the conversation history, current context, and \
available feedback to select the most appropriate next state.
You must consider the scenario of each state and the user's recent actions.
The recent actions are more important than previous actions."""

    # 默认用户提示词模板
    DEFAULT_USER_TEMPLATE = """You are a professional agent follow the \
instruction as following:
{{ global_prompt }}

Each step includes a timestamp and may contain a user_message.
To make the best decision, consider how recently each user_message was made.

Here is the history of steps:
{{ history }}

Here is the state list with index:
{{ states }}

{% if feedbacks %}
You **MUST** follow examples to select the state based on the **SIMILAR** \
"name" and "result" of the last action:
{{ feedbacks }}
{% endif %}

Now, You need to select the proper state for the next action base on the \
scenario.
The recent actions is more important than previous actions.
You must return only the "number" that corresponds to the objective you \
selected."""

    def __init__(
        self,
        llm_engine: LLM,
        agent_name: Optional[str] = None,
        system_prompt: Optional[str] = None,
        user_prompt_template: Optional[str] = None,
    ):
        """
        初始化StateSelectAgent

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

        logger.info("StateSelectAgent initialized for state selection")

    async def step(self, context: Optional[AIContext] = None,
                   **kwargs) -> State:
        """
        重构的step方法，专门用于状态选择任务
        每次step都重新开始，不累积历史对话

        Args:
            context: 可选的外部上下文，如果为None则创建临时context
            **kwargs: 包含settings, memory, feedbacks, token_counter等参数

        Returns:
            State: 选择的下一个状态

        Raises:
            ValueError: 当必需参数缺失或状态机配置无效时
        """
        # 提取必需参数
        settings = kwargs.get('settings')
        memory = kwargs.get('memory')
        feedbacks = kwargs.get('feedbacks', [])
        token_counter = kwargs.get('token_counter')

        if not settings or not memory:
            raise ValueError("settings and memory are required")

        if not settings.state_machine.states:
            raise ValueError("There are no states in state_machine")

        # 如果没有历史记录，返回初始状态
        if not memory.history:
            initial_state = settings.state_machine.get_state(
                settings.state_machine.initial_state_name
            )
            if initial_state is None:
                raise ValueError("Initial state not found in state machine")
            return initial_state

        # 验证当前状态
        current_state_name = memory.history[-1].state_name
        if current_state_name not in settings.state_machine._states_dict:
            raise ValueError(
                f"Invalid state_name \"{current_state_name}\" "
                f"which is not in states"
            )

        current_state = settings.state_machine.get_state(current_state_name)
        next_states = settings.state_machine.get_next_states(current_state_name)

        # 如果没有提供外部上下文，创建一个新的临时上下文
        if context is None:
            working_context = AIContext()
        else:
            working_context = context

        # 添加系统提示词
        working_context.add_system_prompt(self.system_prompt)

        # 构建状态列表
        states_data = yaml.dump(
            {f"State.{i}": {"name": state.name, "scenario": state.scenario}
                for i, state in enumerate(next_states)},
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False
        )

        # 构建反馈信息
        feedbacks_data = ""
        if feedbacks:
            feedbacks_data = yaml.dump(
                {
                    "Last Action": {
                        "name": memory.history[-1].actions[0].name,
                        "result": memory.history[-1].actions[0].result,
                    },
                    "Examples": [
                        {
                            "Last Action": {
                                "name": feedback.observation_name,
                                "result": feedback.observation_content,
                            },
                            "Selected State": feedback.state_name,
                        } for feedback in feedbacks
                    ]
                },
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False
            )

        # 渲染并添加用户提示词
        rendered_prompt = self._render_user_prompt(
            global_prompt=settings.global_prompt,
            history=memory.print_history(),
            states=states_data,
            feedbacks=feedbacks_data
        )
        working_context.add_user_prompt(rendered_prompt)

        try:
            # 调用LLM
            openai_messages = working_context.to_openai_format()
            response = await self.llm_engine.ask(
                messages=openai_messages,
                temperature=getattr(settings, 'temperature', 1.0),
            )

            # 更新token计数器
            if token_counter:
                token_counter.llm_calling_times += 1
                # 注意：LLM类的ask方法可能没有直接返回token信息
                # 这里需要根据实际LLM实现来调整

            # 解析响应
            state_index = safe_to_int(response)
            if state_index < 0 or state_index >= len(next_states):
                logger.warning(
                    f"Invalid state index {state_index}, "
                    f"returning current state {current_state.name}"
                )
                return current_state
            else:
                selected_state = next_states[state_index]
                logger.info(f"Selected state: {selected_state.name}")
                return selected_state

        except Exception as e:
            logger.error(f"StateSelect step execution failed: {e}")
            raise