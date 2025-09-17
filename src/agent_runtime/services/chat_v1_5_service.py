"""
Chat V1.5 Service

从v2_core.py重构的chat方法，提供更好的服务化架构
"""

import json
from typing import List, Optional, Tuple

from agent_runtime.data_format.fsm import Memory
from agent_runtime.interface.api_models import Setting
from agent_runtime.data_format.action import V2Action
from agent_runtime.data_format.fsm import Step
from agent_runtime.data_format.feedback import (
    FeedbackSetting,
    TAG_PREFIX_OBSERVATION_NAME,
    TAG_PREFIX_STATE_NAME,
)
from agent_runtime.services.feedback_service import FeedbackService
from agent_runtime.data_format.tool import RequestTool, SendMessageToUser
from agent_runtime.stats import TokenCounter
from agent_runtime.agents.select_actions_agent import SelectActionsAgent
from agent_runtime.agents.state_select_agent import StateSelectAgent
from agent_runtime.agents.new_state_agent import NewStateAgent
from agent_runtime.clients.openai_llm_client import LLM
from agent_runtime.data_format.tool import ActionExecutor
from agent_runtime.logging.logger import logger

# Additional imports for V2 service functionality
from agent_runtime.services.feedback_service import FeedbackService
from agent_runtime.clients.weaviate_client import WeaviateClient
from agent_runtime.clients.openai_embedding_client import OpenAIEmbeddingClient
from agent_runtime.interface.api_models import (
    ChatRequest,
    ChatResponse,
    LearnRequest,
    LearnResponse,
    GetFeedbackParam,
    DeleteFeedbackParam
)
from agent_runtime.data_format.feedback import Feedback, FeedbackSetting


class ChatService:
    """
    Chat V1.5 服务类

    重构自v2_core.py的chat方法，提供更好的模块化和可维护性
    """

    def __init__(self):
        """初始化ChatService"""
        self.action_executor = ActionExecutor()

        # 初始化LLM引擎
        self.llm_engine = LLM()

        # 初始化各种agents
        self.select_actions_agent = SelectActionsAgent()
        self.state_select_agent = StateSelectAgent(llm_engine=self.llm_engine)
        self.new_state_agent = NewStateAgent(llm_engine=self.llm_engine)

        logger.debug("ChatService initialized with state agents")

    async def chat(
        self,
        settings: Setting,
        memory: Memory,
        request_tools: List[RequestTool] = None,
        token_counter: Optional[TokenCounter] = None,
    ) -> Tuple[Memory, TokenCounter]:
        """
        执行聊天流程

        重构自v2_core.py的chat方法，包含完整的状态机和动作选择逻辑

        Args:
            settings: 设置对象
            memory: 记忆对象
            request_tools: 请求工具列表
            token_counter: token计数器

        Returns:
            Tuple[Memory, TokenCounter]: 更新后的记忆和token计数器
        """
        if request_tools is None:
            request_tools = []

        if token_counter is None:
            token_counter = TokenCounter()

        logger.info(f"Starting chat for agent: {settings.agent_name}")

        # 准备工具
        send_message_to_user = SendMessageToUser()
        tools = [send_message_to_user] + request_tools

        # 检查工具名称重复
        if len(tools) != len(set([tool.name for tool in tools])):
            raise ValueError("There are duplicated tool names")

        # Step 0: 初始化记忆
        memory = await self._initialize_memory_if_needed(
            settings, memory, send_message_to_user, token_counter
        )

        # 如果是初始化步骤，直接返回
        if len(memory.history) == 1 and not memory.history[0].actions[0].result:
            return memory, token_counter

        # Step 1: 执行动作
        memory = await self._execute_actions(memory, tools)

        # Step 2: 选择下一个状态
        current_state, state_feedbacks = await self._select_next_state(
            settings, memory, token_counter
        )
        memory.history[-1].state_feedbacks = state_feedbacks

        # Step 3: 选择下一个动作
        action_feedbacks = await self._get_action_feedbacks(
            settings, memory, current_state
        )

        memory = await self._select_next_actions(
            settings, memory, tools, current_state, action_feedbacks, token_counter
        )
        memory.history[-1].action_feedbacks = action_feedbacks

        logger.info(f"Chat completed for agent: {settings.agent_name}")
        return memory, token_counter

    async def chat_step(
        self,
        user_message: str = "",
        edited_last_response: str = "",
        recall_last_user_message: bool = False,
        settings: Setting = None,
        memory: Memory = None,
        request_tools: List[RequestTool] = None,
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
            token_counter = TokenCounter()

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
                memory, token_counter = await self.chat(
                    settings, memory, request_tools, token_counter
                )

            memory, send_msg_action_idx = self._remove_duplicate_send_message_actions(
                memory, message_tool_name
            )

            # Step 3: 处理消息编辑和用户输入
            if send_msg_action_idx is not None:  # 如果存在 send_message_to_user 动作
                if edited_last_response:
                    memory.history[-1].actions[send_msg_action_idx].arguments = {
                        "agent_message": edited_last_response
                    }
                memory.history[-1].actions[send_msg_action_idx].result = {
                    "user_message": user_message
                }
            elif (
                edited_last_response or user_message
            ):  # 如果没有现存的 send_message_to_user 动作且有新消息
                memory.history[-1].actions.append(
                    V2Action(
                        name=message_tool_name,
                        arguments={"agent_message": edited_last_response},
                        result={"user_message": user_message},
                    )
                )
                send_msg_action_idx = len(memory.history[-1].actions) - 1

            # Step 4: 生成对话响应
            memory, token_counter = await self.chat(
                settings, memory, request_tools, token_counter
            )
            memory, send_msg_action_idx = self._remove_duplicate_send_message_actions(
                memory, message_tool_name
            )

            # Step 5: 如果有多个动作且存在 send_message_to_user，移除 send_message_to_user 动作
            if send_msg_action_idx is not None and len(memory.history[-1].actions) > 1:
                del memory.history[-1].actions[send_msg_action_idx]
                send_msg_action_idx = None

            # Step 6: 创建响应
            response = ""
            if send_msg_action_idx is not None:
                response = (
                    memory.history[-1]
                    .actions[send_msg_action_idx]
                    .arguments.get("agent_message", "")
                )

            result = {
                "response": response,
                "memory": memory,
                "result_type": "Success",
                "llm_calling_times": token_counter.llm_calling_times,
                "total_input_token": token_counter.total_input_token,
                "total_output_token": token_counter.total_output_token,
            }

            logger.info(
                f"Chat step completed successfully for agent {settings.agent_name}"
            )
            return result

        except Exception as e:
            logger.exception(
                f"Error in chat step for agent {settings.agent_name}", exc_info=e
            )
            raise e

    def _remove_duplicate_send_message_actions(
        self, memory: Memory, message_tool_name: str
    ):
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
                "Multiple 'send_message_to_user' actions found in the last memory history. Only the first one will be used."
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
        token_counter: TokenCounter,
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
        self, settings: Setting, memory: Memory, token_counter: TokenCounter
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
                token_counter=token_counter,
            )
        else:
            # 直接使用NewStateAgent创建新状态
            current_state = await self.new_state_agent.step(
                settings=settings, memory=memory, token_counter=token_counter
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

        feedback_service = self._get_feedback_service(settings.vector_db_url)
        state_feedbacks = await feedback_service.query_feedbacks(
            settings=FeedbackSetting(
                vector_db_url=settings.vector_db_url,
                top_k=settings.top_k,
                agent_name=settings.agent_name,
            ),
            query=json.dumps(memory.history[-1].actions[0].result, ensure_ascii=False),
            tags=observation_tag,
        )

        logger.debug(f"Retrieved {len(state_feedbacks)} state feedbacks")
        return state_feedbacks

    async def _get_action_feedbacks(
        self, settings: Setting, memory: Memory, current_state
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

            feedback_service = self._get_feedback_service(settings.vector_db_url)
            action_feedbacks = await feedback_service.query_feedbacks(
                settings=FeedbackSetting(
                    vector_db_url=settings.vector_db_url,
                    top_k=settings.top_k,
                    agent_name=settings.agent_name,
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
        current_state,
        feedbacks: List,
        token_counter: TokenCounter,
    ) -> Memory:
        """选择下一个动作"""
        logger.debug("Selecting next actions using SelectActionsAgent")

        memory = await self.select_actions_agent.step(
            settings=settings,
            memory=memory,
            tools=tools,
            current_state=current_state,
            feedbacks=feedbacks,
            token_counter=token_counter,
        )

        return memory

    def get_stats(self) -> dict:
        """获取服务统计信息"""
        return {
            "service_type": "ChatService",
            "action_executor_stats": self.action_executor.get_stats(),
            "select_actions_agent": type(self.select_actions_agent).__name__,
            "state_select_agent": type(self.state_select_agent).__name__,
            "new_state_agent": type(self.new_state_agent).__name__,
            "llm_engine": type(self.llm_engine).__name__,
        }

    # ===== V2 API Service Methods (from ChatV2Service) =====

    def _get_feedback_service(self, vector_db_url: str) -> FeedbackService:
        """
        获取FeedbackService实例

        Args:
            vector_db_url: 向量数据库URL

        Returns:
            FeedbackService: 反馈服务实例
        """
        # 创建WeaviateClient
        weaviate_client = WeaviateClient(
            url=vector_db_url,
            timeout=30
        )

        # 创建OpenAI嵌入客户端
        embedding_client = OpenAIEmbeddingClient()

        # 创建FeedbackService
        return FeedbackService(
            weaviate_client=weaviate_client,
            embedding_client=embedding_client
        )

    async def generate_chat(self, request: ChatRequest) -> ChatResponse:
        """
        生成聊天响应

        Args:
            request: 聊天请求

        Returns:
            ChatResponse: 聊天响应
        """
        try:
            logger.info(f"Processing chat request for agent: {request.settings.agent_name}")

            # 将请求转换为ChatService的格式
            settings = Setting(**request.settings.model_dump())
            memory = Memory(**request.memory.model_dump())

            # 转换request_tools
            request_tools = []
            for tool_data in request.request_tools:
                request_tool = RequestTool(**tool_data)
                request_tools.append(request_tool)

            # 调用ChatService的chat_step方法
            result = await self.chat_step(
                user_message=request.user_message,
                edited_last_response=request.edited_last_response,
                recall_last_user_message=request.recall_last_user_message,
                settings=settings,
                memory=memory,
                request_tools=request_tools
            )

            # 构建响应
            response = ChatResponse(
                response=result["response"],
                memory=result["memory"].model_dump(),
                result_type=result["result_type"],
                llm_calling_times=result["llm_calling_times"],
                total_input_token=result["total_input_token"],
                total_output_token=result["total_output_token"]
            )

            logger.info(f"Chat request completed for agent: {request.settings.agent_name}")
            return response

        except Exception as e:
            logger.error(f"Error in generate_chat: {e}")
            raise

    async def learn_from_feedback(self, request: LearnRequest) -> LearnResponse:
        """
        从反馈中学习

        Args:
            request: 学习请求

        Returns:
            LearnResponse: 学习响应
        """
        try:
            logger.info(f"Processing learn request for agent: {request.settings.agent_name}")

            # 转换为FeedbackService的格式
            feedback_setting = FeedbackSetting(
                vector_db_url=request.settings.vector_db_url,
                agent_name=request.settings.agent_name
            )

            # 转换feedbacks
            feedbacks = []
            for feedback_data in request.feedbacks:
                feedback = Feedback(**feedback_data.model_dump())
                feedbacks.append(feedback)

            # 获取FeedbackService实例并调用learn方法
            feedback_service = self._get_feedback_service(request.settings.vector_db_url)
            result = await feedback_service.learn(
                settings=feedback_setting,
                feedbacks=feedbacks
            )

            # 构建响应
            response = LearnResponse(
                result_type="Success",
                learned_count=result.get("learned_count", len(feedbacks)),
                message=result.get("message", "Learning completed successfully")
            )

            logger.info(f"Learn request completed for agent: {request.settings.agent_name}")
            return response

        except Exception as e:
            logger.error(f"Error in learn_from_feedback: {e}")
            raise

    async def get_all_feedbacks(self, param: GetFeedbackParam) -> List[Feedback]:
        """
        获取所有反馈

        Args:
            param: 获取反馈参数

        Returns:
            List[Feedback]: 反馈列表
        """
        try:
            logger.info(f"Getting feedbacks for agent: {param.agent_name}")

            # 转换为FeedbackService的格式
            feedback_setting = FeedbackSetting(
                vector_db_url=param.vector_db_url,
                agent_name=param.agent_name
            )

            # 获取FeedbackService实例并调用get_all方法
            feedback_service = self._get_feedback_service(param.vector_db_url)
            feedbacks = await feedback_service.get_all(
                settings=feedback_setting,
                offset=param.offset,
                limit=param.limit
            )

            logger.info(f"Retrieved {len(feedbacks)} feedbacks for agent: {param.agent_name}")
            return feedbacks

        except Exception as e:
            logger.error(f"Error in get_all_feedbacks: {e}")
            raise

    async def delete_all_feedbacks(self, param: DeleteFeedbackParam) -> None:
        """
        删除所有反馈

        Args:
            param: 删除反馈参数
        """
        try:
            logger.info(f"Deleting feedbacks for agent: {param.agent_name}")

            # 转换为FeedbackService的格式
            feedback_setting = FeedbackSetting(
                vector_db_url=param.vector_db_url,
                agent_name=param.agent_name
            )

            # 获取FeedbackService实例并调用delete_all方法
            feedback_service = self._get_feedback_service(param.vector_db_url)
            result = await feedback_service.delete_all(settings=feedback_setting)

            logger.info(f"Deleted feedbacks for agent: {param.agent_name}, result: {result}")

        except Exception as e:
            logger.error(f"Error in delete_all_feedbacks: {e}")
            raise
