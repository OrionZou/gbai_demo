from typing import List, Dict, Any, Tuple, Optional
from agent_runtime.agents.base import BaseAgent
from agent_runtime.data_format.context import AIContext
from agent_runtime.data_format.v2_core import (
    chat, Memory, Setting, TokenCounter, V2Action as Action
)
from agent_runtime.data_format.tools import RequestTool
from agent_runtime.logging.logger import logger


class ChatAgent(BaseAgent):
    """
    Chat Agent - 基于v2 chat核心实现的对话代理

    维护与原始agent/v2 API完全一致的输入输出格式
    """

    DEFAULT_AGENT_NAME = "chat_agent"

    def __init__(self, agent_name: str = None, **kwargs):
        system_prompt = "Professional conversational AI assistant"
        user_template = ""  # 不需要用户模板，直接通过参数传递
        super().__init__(
            agent_name=agent_name or self.DEFAULT_AGENT_NAME,
            system_prompt=system_prompt,
            user_prompt_template=user_template,
            **kwargs
        )

    async def chat_step(
        self,
        user_message: str = "",
        edited_last_response: str = "",
        recall_last_user_message: bool = False,
        settings: Setting = None,
        memory: Memory = None,
        request_tools: List[RequestTool] = None,
        context: Optional[AIContext] = None
    ) -> Dict[str, Any]:
        """
        执行对话步骤

        Args:
            user_message: 用户消息
            edited_last_response: 编辑的上次响应
            recall_last_user_message: 是否撤回上次用户消息
            settings: 对话设置
            memory: 对话记忆
            request_tools: 请求工具列表
            context: AI上下文（可选）

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
        logger.info(f"Starting chat step for agent {self.agent_name}")

        try:
            token_counter = TokenCounter()

            # Step 1: 处理撤回逻辑
            message_tool_name = "send_message_to_user"

            if recall_last_user_message and memory.history:
                memory, send_msg_action_idx = self._remove_duplicate_send_message_actions(memory, message_tool_name)
                # 如果最后的动作是 'send_message_to_user'，移除它
                if send_msg_action_idx is not None:
                    memory.history = memory.history[:-1]

            # Step 2: 检查记忆是否为空
            if not memory.history:
                memory, token_counter = await chat(settings, memory, request_tools, token_counter)

            memory, send_msg_action_idx = self._remove_duplicate_send_message_actions(memory, message_tool_name)

            # Step 3: 处理消息编辑和用户输入
            if send_msg_action_idx is not None:  # 如果存在 send_message_to_user 动作
                if edited_last_response:
                    memory.history[-1].actions[send_msg_action_idx].arguments = {"agent_message": edited_last_response}
                memory.history[-1].actions[send_msg_action_idx].result = {"user_message": user_message}
            elif edited_last_response or user_message:  # 如果没有现存的 send_message_to_user 动作且有新消息
                memory.history[-1].actions.append(
                    Action(
                        name=message_tool_name,
                        arguments={"agent_message": edited_last_response},
                        result={"user_message": user_message}
                    )
                )
                send_msg_action_idx = len(memory.history[-1].actions) - 1

            # Step 4: 生成对话响应
            memory, token_counter = await chat(settings, memory, request_tools, token_counter)
            memory, send_msg_action_idx = self._remove_duplicate_send_message_actions(memory, message_tool_name)

            # Step 5: 如果有多个动作且存在 send_message_to_user，移除 send_message_to_user 动作
            if send_msg_action_idx is not None and len(memory.history[-1].actions) > 1:
                del memory.history[-1].actions[send_msg_action_idx]
                send_msg_action_idx = None

            # Step 6: 创建响应
            response = ""
            if send_msg_action_idx is not None:
                response = memory.history[-1].actions[send_msg_action_idx].arguments.get("agent_message", "")

            result = {
                "response": response,
                "memory": memory,
                "result_type": "Success",
                "llm_calling_times": token_counter.llm_calling_times,
                "total_input_token": token_counter.total_input_token,
                "total_output_token": token_counter.total_output_token
            }

            logger.info(f"Chat step completed successfully for agent {self.agent_name}")
            return result

        except Exception as e:
            logger.exception(f"Error in chat step for agent {self.agent_name}", exc_info=e)
            raise e

    def _remove_duplicate_send_message_actions(self, memory: Memory, message_tool_name: str) -> Tuple[Memory, Optional[int]]:
        """
        从最后的记忆历史中移除重复的 'send_message_to_user' 动作
        """
        if not memory.history:
            return memory, None

        send_msg_action_idx_list = [
            i for i, action in enumerate(memory.history[-1].actions)
            if action.name == message_tool_name
        ]

        if len(send_msg_action_idx_list) > 1:
            logger.warning("Multiple 'send_message_to_user' actions found in the last memory history. Only the first one will be used.")
            # 只保留第一个 send_message_to_user 动作
            for i in sorted(send_msg_action_idx_list[1:], reverse=True):
                del memory.history[-1].actions[i]

        index = send_msg_action_idx_list[0] if send_msg_action_idx_list else None
        return memory, index

    async def step(self, context: Optional[AIContext] = None, **kwargs) -> Any:
        """
        BaseAgent要求实现的step方法
        这里委托给chat_step处理
        """
        return await self.chat_step(context=context, **kwargs)