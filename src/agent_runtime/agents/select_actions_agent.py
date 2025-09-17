"""
Select Actions Agent - 动作选择器

基于BaseAgent实现，专门用于动作选择和工具调用
"""

import json
import yaml
from typing import Optional, List, Tuple, TYPE_CHECKING

from agent_runtime.agents.base import BaseAgent
from agent_runtime.data_format.context import AIContext
from agent_runtime.data_format.feedback import Feedback
from agent_runtime.data_format.tool import BaseTool, SendMessageToUser
from agent_runtime.data_format.fsm import State
from agent_runtime.stats import TokenCounter
from agent_runtime.logging.logger import logger
from agent_runtime.clients.openai_llm_client import LLM
from openai import AsyncOpenAI

if TYPE_CHECKING:
    from agent_runtime.interface.api_models import Setting
    from agent_runtime.data_format.fsm import Memory


class SelectActionsAgent(BaseAgent):
    """
    Action selection agent for tool calling
    基于BaseAgent的动作选择代理
    """

    DEFAULT_AGENT_NAME = "select_actions_agent"

    # 默认系统提示词
    DEFAULT_SYSTEM_PROMPT = (
        "You are a professional agent follow the instruction as following:\n"
        "{global_prompt}\n"
        "Now, consider the history of steps and select the next action; "
        "you **MUST** select at least one action.\n"
        "Each step includes a timestamp and may contain a user_message.\n"
        "To make the best decision, consider how recently each user_message "
        "was made.\n"
        "History of steps:\n{history}\n"
    )

    # 默认用户提示词模板
    DEFAULT_USER_TEMPLATE = (
        "You **MUST** follow examples to select next actions and give "
        "**SIMILAR** arguments:\n{feedbacks}\n"
        "And the instruction for the next action is:\n{instruction}\n"
    )

    def __init__(
        self,
        agent_name: Optional[str] = None,
        llm_engine: Optional[LLM] = None,
        system_prompt: Optional[str] = None,
        user_prompt_template: Optional[str] = None
    ):
        """
        初始化SelectActionsAgent

        Args:
            agent_name: agent名称，如果不提供则使用默认值
            llm_engine: LLM客户端引擎，如果不提供则创建默认引擎
            system_prompt: 自定义系统提示词，如果不提供则使用默认值
            user_prompt_template: 自定义用户提示词模板，如果不提供则使用默认值
        """
        super().__init__(
            agent_name=agent_name or self.DEFAULT_AGENT_NAME,
            llm_engine=llm_engine or LLM(),
            system_prompt=system_prompt or self.DEFAULT_SYSTEM_PROMPT,
            user_prompt_template=user_prompt_template or self.DEFAULT_USER_TEMPLATE,
        )
        logger.info("SelectActionsAgent initialized for action selection")

    async def step(
        self,
        context: Optional[AIContext] = None,
        **kwargs
    ) -> "Memory":
        """
        Execute action selection step

        Args:
            context: AI context (optional, not used in this agent)
            **kwargs: Required parameters:
                - settings: Setting object
                - memory: Memory object
                - tools: List of BaseTool objects
                - current_state: State object
                - feedbacks: List of Feedback objects
                - token_counter: TokenCounter object

        Returns:
            Updated Memory object
        """
        # Extract required parameters with type checking
        settings = kwargs.get('settings')
        memory = kwargs.get('memory')
        tools = kwargs.get('tools')
        current_state = kwargs.get('current_state')
        feedbacks = kwargs.get('feedbacks', [])
        token_counter = kwargs.get('token_counter')

        if not all([settings, memory, tools, current_state, token_counter]):
            raise ValueError(
                "Missing required parameters: settings, memory, tools, "
                "current_state, token_counter"
            )

        # Type assertions for type checker
        assert settings is not None
        assert memory is not None
        assert tools is not None
        assert current_state is not None
        assert token_counter is not None

        return await self._select_actions(
            settings=settings,
            memory=memory,
            tools=tools,
            current_state=current_state,
            feedbacks=feedbacks,
            token_counter=token_counter
        )

    async def _select_actions(
        self,
        settings: "Setting",
        memory: "Memory",
        tools: List[BaseTool],
        current_state: State,
        feedbacks: List[Feedback],
        token_counter: TokenCounter
    ) -> "Memory":
        """
        Select next actions using LLM with tool calling
        """
        try:
            # Build system prompt
            system_prompt = self.system_prompt.format(
                global_prompt=settings.global_prompt,
                history=memory.print_history()
            )

            # Build user prompt with feedbacks and instruction
            user_prompt = ""
            if feedbacks:
                feedbacks_content = yaml.dump(
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
                                "Next Action": {
                                    "name": feedback.action_name,
                                    "arguments": feedback.action_content,
                                },
                            } for feedback in feedbacks
                        ]
                    },
                    allow_unicode=True,
                    default_flow_style=False,
                    sort_keys=False
                )
                user_prompt += (
                    "You **MUST** follow examples to select next actions and "
                    f"give **SIMILAR** arguments:\n{feedbacks_content}\n"
                )

            user_prompt += (
                f"And the instruction for the next action is:\n"
                f"{current_state.instruction}\n"
            )

            # Call LLM with tool calling using the enhanced LLM client
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            # Create a temporary LLM client with settings configuration
            temp_llm = LLM()
            temp_llm.api_key = settings.api_key
            temp_llm.base_url = settings.base_url
            temp_llm.model = settings.chat_model
            temp_llm.temperature = settings.temperature
            temp_llm.top_p = settings.top_p

            # Create new client with updated settings
            temp_llm.client = AsyncOpenAI(
                api_key=settings.api_key,
                base_url=settings.base_url
            )

            # Use the enhanced ask_tool method with token counting
            response = await temp_llm.ask_tool(
                messages=messages,
                tools=[tool.get_tool_calling_schema() for tool in tools],
                tool_choice="required",
                temperature=settings.temperature,
                token_counter=token_counter
            )

            # Parse tool calls from the message response
            tools_and_args = self._parse_tool_calls_from_message(response, tools)

            # If no tools are selected, send empty message to user
            if not tools_and_args:
                send_message_tool = next(
                    (tool for tool in tools if tool.name == "send_message_to_user"),
                    SendMessageToUser()
                )
                tools_and_args.append((send_message_tool, {"agent_message": ""}))

            # Create new step with selected actions - using dynamic import to
            # avoid circular dependency
            from agent_runtime.data_format.fsm import Step
            from agent_runtime.data_format.action import V2Action

            memory.history.append(
                Step(
                    state_name=current_state.name,
                    actions=[
                        V2Action(name=tool.name, arguments=arguments, result=None)
                        for tool, arguments in tools_and_args
                    ]
                )
            )

            logger.info(
                f"Selected {len(tools_and_args)} actions for state: "
                f"{current_state.name}"
            )

            return memory

        except Exception as e:
            logger.error(f"Error in _select_actions: {e}")
            raise

    def _parse_tool_calls_from_message(
        self,
        message,
        tools: List[BaseTool]
    ) -> List[Tuple[BaseTool, dict]]:
        """
        Parse tool calls from LLM message response

        Args:
            message: OpenAI message object from ask_tool
            tools: Available tools

        Returns:
            List of (tool, arguments) tuples
        """
        tools_and_args = []

        if not hasattr(message, 'tool_calls') or not message.tool_calls:
            return tools_and_args

        for tool_call in message.tool_calls:
            tool = next(
                (tool for tool in tools if tool.name == tool_call.function.name),
                None
            )
            if tool is None:
                logger.warning(f"Tool not found: {tool_call.function.name}")
                continue

            try:
                arguments = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                logger.warning(
                    f"Failed to parse arguments for tool "
                    f"{tool_call.function.name}"
                )
                arguments = {}

            # Handle escaped JSON strings from some models (Deepseek, Qwen)
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    logger.warning(
                        f"Failed to parse escaped JSON arguments for tool "
                        f"{tool_call.function.name}"
                    )
                    arguments = {}

            tools_and_args.append((tool, arguments))

        return tools_and_args

    def _parse_tool_calls(
        self,
        response,
        tools: List[BaseTool]
    ) -> List[Tuple[BaseTool, dict]]:
        """
        Legacy method - parse tool calls from LLM response object
        Kept for backward compatibility
        """
        if hasattr(response, 'choices') and response.choices:
            return self._parse_tool_calls_from_message(
                response.choices[0].message, tools
            )
        else:
            return self._parse_tool_calls_from_message(response, tools)