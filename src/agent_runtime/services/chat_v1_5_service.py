"""
Chat V1.5 Service

从v2_core.py重构的chat方法，提供更好的服务化架构
"""

import json
from typing import List, Optional, Tuple, TYPE_CHECKING

from agent_runtime.data_format.fsm import Memory
from agent_runtime.interface.api_models import Setting
from agent_runtime.data_format.action import V2Action
from agent_runtime.data_format.fsm import Step
from agent_runtime.data_format.feedback import (
    TAG_PREFIX_OBSERVATION_NAME,
    TAG_PREFIX_STATE_NAME,
)
from agent_runtime.interface.api_models import FeedbackSetting
from agent_runtime.services.feedback_service import FeedbackService
from agent_runtime.data_format.tool import RequestTool, SendMessageToUser
from agent_runtime.agents.select_actions_agent import SelectActionsAgent
from agent_runtime.agents.state_select_agent import StateSelectAgent
from agent_runtime.agents.new_state_agent import NewStateAgent
from agent_runtime.clients.openai_llm_client import LLM
from agent_runtime.data_format.tool import ActionExecutor
from agent_runtime.config.loader import LLMSetting
from agent_runtime.logging.logger import logger

if TYPE_CHECKING:
    from agent_runtime.data_format.fsm import State

# Additional imports for V2 service functionality
from agent_runtime.clients.weaviate_client import WeaviateClient
from agent_runtime.clients.openai_embedding_client import OpenAIEmbeddingClient


class ChatService:
    """
    Chat V1.5 服务类

    重构自v2_core.py的chat方法，提供更好的模块化和可维护性。
    每次调用generate_chat时根据传入参数动态创建llm_engine，保持agent静态创建。
    """

    def __init__(self) -> None:
        """初始化ChatService"""
        self.action_executor = ActionExecutor()

        # 静态创建agents（使用默认LLM，后续可以更新）
        default_llm = LLM()
        self.select_actions_agent = SelectActionsAgent(llm_engine=default_llm)
        self.state_select_agent = StateSelectAgent(llm_engine=default_llm)
        self.new_state_agent = NewStateAgent(llm_engine=default_llm)

        # FeedbackService链接
        self.feedback_service: Optional[FeedbackService] = None

        logger.debug("ChatService initialized with static agents")

    def update_agents_llm_engine(self, llm_engine: LLM) -> None:
        """
        更新agents的LLM引擎

        Args:
            llm_engine: 新的LLM引擎实例
        """
        # 更新需要LLM的agents
        self.select_actions_agent.llm_engine = llm_engine
        self.state_select_agent.llm_engine = llm_engine
        self.new_state_agent.llm_engine = llm_engine

        logger.debug(f"Updated agents with new LLM engine: {llm_engine.model}")

    def link_feedback_service(self, feedback_service: FeedbackService) -> None:
        """
        链接FeedbackService到ChatService

        Args:
            feedback_service: FeedbackService实例
        """
        self.feedback_service = feedback_service
        logger.debug("FeedbackService linked to ChatService")

    async def chat(
        self,
        settings: Setting,
        memory: Memory,
        request_tools: Optional[List[RequestTool]] = None,
    ) -> Memory:
        """
        执行聊天流程

        重构自v2_core.py的chat方法，包含完整的状态机和动作选择逻辑

        Args:
            settings: 设置对象
            memory: 记忆对象
            request_tools: 请求工具列表
        Returns:
            Memory: 更新后的记忆
        """
        if request_tools is None:
            request_tools = []

        logger.info(f"Starting chat for agent: {settings.agent_name}")

        # 准备工具
        send_message_to_user = SendMessageToUser()
        tools = [send_message_to_user] + request_tools

        # 检查工具名称重复
        if len(tools) != len(set([tool.name for tool in tools])):
            raise ValueError("There are duplicated tool names")

        # Step 0: 初始化记忆
        memory = await self._initialize_memory_if_needed(
            settings, memory, send_message_to_user
        )

        # 如果是初始化步骤，直接返回
        if len(memory.history) == 1 and not memory.history[0].actions[0].result:
            return memory

        # Step 1: 执行动作
        memory = await self._execute_actions(memory, tools)

        # Step 2: 选择下一个状态
        current_state, state_feedbacks = await self._select_next_state(
            settings, memory
        )
        memory.history[-1].state_feedbacks = state_feedbacks

        # Step 3: 选择下一个动作
        action_feedbacks = await self._get_action_feedbacks(
            settings, memory, current_state
        )

        memory = await self._select_next_actions(
            settings, memory, tools, current_state, action_feedbacks
        )
        memory.history[-1].action_feedbacks = action_feedbacks

        logger.info(f"Chat completed for agent: {settings.agent_name}")
        return memory

    async def chat_step(
        self,
        user_message: str = "",
        edited_last_response: str = "",
        recall_last_user_message: bool = False,
        settings: Optional[Setting] = None,
        memory: Optional[Memory] = None,
        request_tools: Optional[List[RequestTool]] = None,
    ) -> dict:
        """
        高级聊天步骤，集成自ChatAgent的逻辑

        处理用户消息、编辑响应、撤回功能等高级对话管理功能

        Args:
            user_message: 用户消息
            edited_last_response: 编辑的上次响应
            recall_last_user_message: 是否撤回上次用户消息
            settings: 对话设置
            memory: 对话记忆
            request_tools: 请求工具列表

        Returns:
            包含response, memory, token统计等信息的字典
        """
        if not settings:
            raise ValueError("Settings is required for chat")

        if memory is None:
            memory = Memory()

        if request_tools is None:
            request_tools = []

        # 记录日志
        logger.info(f"Starting chat step for agent {settings.agent_name}")

        try:

            # Step 1: 处理撤回逻辑
            message_tool_name = "send_message_to_user"

            if recall_last_user_message and memory.history:
                memory, send_msg_action_idx = (
                    self._remove_duplicate_send_message_actions(
                        memory, message_tool_name
                    )
                )
                # 如果最后的动作是 'send_message_to_user'，移除它
                if send_msg_action_idx is not None:
                    memory.history = memory.history[:-1]

            # Step 2: 检查记忆是否为空
            if not memory.history:
                memory = await self.chat(
                    settings, memory, request_tools
                )

            memory, send_msg_action_idx = self._remove_duplicate_send_message_actions(
                memory, message_tool_name
            )

            # Step 3: 处理消息编辑和用户输入
            # 如果存在 send_message_to_user 动作
            if send_msg_action_idx is not None:
                if edited_last_response:
                    action = memory.history[-1].actions[send_msg_action_idx]
                    action.arguments = {"agent_message": edited_last_response}
                action = memory.history[-1].actions[send_msg_action_idx]
                action.result = {"user_message": user_message}
            # 如果没有现存的 send_message_to_user 动作且有新消息
            elif edited_last_response or user_message:
                memory.history[-1].actions.append(
                    V2Action(
                        name=message_tool_name,
                        arguments={"agent_message": edited_last_response},
                        result={"user_message": user_message},
                    )
                )
                send_msg_action_idx = len(memory.history[-1].actions) - 1

            # Step 4: 生成对话响应
            memory = await self.chat(
                settings, memory, request_tools
            )
            memory, send_msg_action_idx = self._remove_duplicate_send_message_actions(
                memory, message_tool_name
            )

            # Step 5: 如果有多个动作且存在 send_message_to_user，
            # 移除 send_message_to_user 动作
            if send_msg_action_idx is not None and len(memory.history[-1].actions) > 1:
                del memory.history[-1].actions[send_msg_action_idx]
                send_msg_action_idx = None

            # Step 6: 创建响应
            response = ""
            if send_msg_action_idx is not None:
                action = memory.history[-1].actions[send_msg_action_idx]
                response = (action.arguments or {}).get("agent_message", "")

            result = {
                "response": response,
                "memory": memory,
                "result_type": "Success",
                "llm_calling_times": 0,
                "total_input_token": 0,
                "total_output_token": 0,
            }

            logger.info(
                f"Chat step completed successfully for " f"agent {settings.agent_name}"
            )
            return result

        except Exception as e:
            logger.exception(
                f"Error in chat step for agent {settings.agent_name}", exc_info=e
            )
            raise e

    def _remove_duplicate_send_message_actions(
        self, memory: Memory, message_tool_name: str
    ) -> Tuple[Memory, Optional[int]]:
        """
        从最后的记忆历史中移除重复的 'send_message_to_user' 动作
        """
        if not memory.history:
            return memory, None

        send_msg_action_idx_list = [
            i
            for i, action in enumerate(memory.history[-1].actions)
            if action.name == message_tool_name
        ]

        if len(send_msg_action_idx_list) > 1:
            logger.warning(
                "Multiple 'send_message_to_user' actions found in the last "
                "memory history. Only the first one will be used."
            )
            # 只保留第一个 send_message_to_user 动作
            for i in sorted(send_msg_action_idx_list[1:], reverse=True):
                del memory.history[-1].actions[i]

        index = send_msg_action_idx_list[0] if send_msg_action_idx_list else None
        return memory, index

    async def _initialize_memory_if_needed(
        self,
        settings: Setting,
        memory: Memory,
        send_message_to_user: SendMessageToUser,
    ) -> Memory:
        """初始化记忆（如果需要）"""
        if not memory.history:
            logger.debug("Initializing memory with initial actions")
            memory.history.append(
                Step(
                    state_name=settings.state_machine.initial_state_name,
                    actions=[
                        V2Action(
                            name=send_message_to_user.name,
                            arguments={"agent_message": ""},
                            result=None,
                        )
                    ],
                )
            )
        return memory

    async def _execute_actions(self, memory: Memory, tools: List) -> Memory:
        """执行动作"""
        logger.debug("Executing actions using ActionExecutor")
        memory = await self.action_executor.execute_actions(memory=memory, tools=tools)
        return memory

    async def _select_next_state(
        self, settings: Setting, memory: Memory
    ) -> Tuple:
        """选择下一个状态"""
        logger.debug("Selecting next state")

        state_feedbacks = []

        # 如果有状态机定义
        if settings.state_machine.states:
            # 获取状态反馈
            if memory.history and memory.history[-1].actions:
                state_feedbacks = await self._get_state_feedbacks(settings, memory)

            # 直接使用StateSelectAgent
            current_state = await self.state_select_agent.step(
                settings=settings,
                memory=memory,
                feedbacks=state_feedbacks,
            )
        else:
            # 直接使用NewStateAgent创建新状态
            current_state = await self.new_state_agent.step(
                settings=settings, memory=memory
            )

        return current_state, state_feedbacks

    async def _get_state_feedbacks(self, settings: Setting, memory: Memory) -> List:
        """获取状态反馈"""
        if not (memory.history and memory.history[-1].actions):
            return []

        # TODO: 目前只从最后一步的最后一个动作获取反馈
        # 需要从最后一步的所有动作获取反馈
        observation_tag = [
            TAG_PREFIX_OBSERVATION_NAME + memory.history[-1].actions[0].name
        ]

        # 查询状态反馈（如果有FeedbackService链接）
        state_feedbacks = []
        if self.feedback_service:
            state_feedbacks = await self.feedback_service.query_feedbacks(
                settings=FeedbackSetting(
                    vector_db_url=settings.vector_db_url,
                    top_k=settings.top_k,
                    agent_name=settings.agent_name,
                    embedding_api_key=settings.embedding_api_key or "",
                ),
                query=json.dumps(
                    memory.history[-1].actions[0].result, ensure_ascii=False
                ),
                tags=observation_tag,
            )

        logger.debug(f"Retrieved {len(state_feedbacks)} state feedbacks")
        return state_feedbacks

    async def _get_action_feedbacks(
        self, settings: Setting, memory: Memory, current_state: "State"
    ) -> List:
        """获取动作反馈"""
        action_feedbacks = []

        if memory.history and memory.history[-1].actions:
            # TODO: 目前只从最后一步的最后一个动作获取反馈
            # 需要从最后一步的所有动作获取反馈
            observation_tag = [
                TAG_PREFIX_OBSERVATION_NAME + memory.history[-1].actions[0].name
            ]
            state_tag = (
                [TAG_PREFIX_STATE_NAME + current_state.name]
                if current_state.name
                else []
            )

            # 查询动作反馈（如果有FeedbackService链接）
            action_feedbacks = []
            if self.feedback_service:
                action_feedbacks = await self.feedback_service.query_feedbacks(
                    settings=FeedbackSetting(
                        vector_db_url=settings.vector_db_url,
                        top_k=settings.top_k,
                        agent_name=settings.agent_name,
                        embedding_api_key=settings.embedding_api_key or "",
                    ),
                    query=json.dumps(
                        memory.history[-1].actions[0].result, ensure_ascii=False
                    ),
                    tags=observation_tag + state_tag,
                )

            logger.debug(f"Retrieved {len(action_feedbacks)} action feedbacks")

        return action_feedbacks

    async def _select_next_actions(
        self,
        settings: Setting,
        memory: Memory,
        tools: List,
        current_state: "State",
        feedbacks: List,
    ) -> Memory:
        """选择下一个动作"""
        logger.debug("Selecting next actions using SelectActionsAgent")

        memory = await self.select_actions_agent.step(
            settings=settings,
            memory=memory,
            tools=tools,
            current_state=current_state,
            feedbacks=feedbacks,
        )

        return memory

    def get_stats(self) -> dict:
        """获取服务统计信息"""
        return {
            "service_type": "ChatService (Dynamic)",
            "mode": "stateless_dynamic_agents",
            "action_executor_stats": self.action_executor.get_stats(),
            "description": "Agents and LLM engine created dynamically per request",
        }
