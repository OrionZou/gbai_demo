"""
DEPRECATED: v2_core module - Use new service-based architecture instead

This module is kept for backward compatibility only.
All functionality has been moved to appropriate modules:

- Memory, Step: moved to agent_runtime.data_format.fsm
- Setting: moved to agent_runtime.interface.api_models
- V2Action: moved to agent_runtime.data_format.action
- chat function: uses ChatService from chat_v1_5_service
- select_state, create_new_state: use StateSelectAgent and NewStateAgent directly
- _select_actions: refactored into SelectActionsAgent class
- _execute_actions: refactored into ActionExecutor class
"""

from typing import Optional, List, Tuple, TYPE_CHECKING

from agent_runtime.data_format.tool import RequestTool
from agent_runtime.data_format.fsm import Memory

if TYPE_CHECKING:
    from agent_runtime.interface.api_models import Setting


async def chat(
    settings: "Setting",
    memory: Memory,
    request_tools: List[RequestTool] = [],
) -> Memory:
    """
    聊天功能 - 使用ChatService重构后的实现

    这个方法现在作为ChatService的包装器，保持向后兼容性
    """
    from agent_runtime.services.chat_v1_5_service import ChatService

    # 创建ChatService实例
    chat_service = ChatService()

    # 调用重构后的chat方法
    memory, _ = await chat_service.chat(
        settings=settings,
        memory=memory,
        request_tools=request_tools,
    )
    return memory


__all__ = ["chat"]