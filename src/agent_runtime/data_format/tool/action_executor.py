"""
Action Executor for executing tools and actions

重构自 v2_core.py 中的 _execute_actions 函数
"""

import asyncio
from datetime import datetime
from typing import List, TYPE_CHECKING

from agent_runtime.logging.logger import logger

if TYPE_CHECKING:
    from agent_runtime.data_format.fsm import Memory
    from agent_runtime.data_format.action import V2Action
    from agent_runtime.data_format.tool import BaseTool


class ActionExecutor:
    """
    Action执行器

    负责执行Memory中最新Step的所有Actions，并处理执行结果和错误
    """

    def __init__(self):
        """初始化ActionExecutor"""
        self.execution_count = 0
        logger.debug("ActionExecutor initialized")

    async def execute_actions(
        self,
        memory: "Memory",
        tools: List["BaseTool"]
    ) -> "Memory":
        """
        执行内存中最新步骤的所有动作

        Args:
            memory: 包含待执行动作的内存对象
            tools: 可用工具列表

        Returns:
            Memory: 更新后的内存对象，包含执行结果

        Note:
            LLM可能生成错误的工具调用模式，可能导致execute()收到意外的关键字参数错误。
            此方法会处理这些错误并返回错误消息。
        """
        if not memory.history:
            logger.warning("No history in memory, nothing to execute")
            return memory

        if not memory.history[-1].actions:
            logger.warning("No actions in latest step, nothing to execute")
            return memory

        logger.info(f"Executing {len(memory.history[-1].actions)} actions")

        # 创建工具名称到工具对象的映射
        tool_map = {tool.name: tool for tool in tools}

        # 并发执行所有动作
        tasks = [
            self._execute_single_action(action, tool_map)
            for action in memory.history[-1].actions
        ]

        memory.history[-1].actions = await asyncio.gather(*tasks)
        memory.history[-1].timestamp = datetime.now().astimezone().isoformat()

        self.execution_count += 1
        logger.info(f"Completed execution batch #{self.execution_count}")

        return memory

    async def _execute_single_action(
        self,
        action: "V2Action",
        tool_map: dict[str, "BaseTool"]
    ) -> "V2Action":
        """
        执行单个动作

        Args:
            action: 待执行的动作
            tool_map: 工具名称到工具对象的映射

        Returns:
            V2Action: 包含执行结果的动作对象
        """
        # 如果动作已经有结果，直接返回
        if action.result:
            logger.debug(f"Action {action.name} already has result, skipping")
            return action

        try:
            tool = tool_map.get(action.name)
            if tool is None:
                error_msg = f"No tool found with the name '{action.name}'"
                logger.error(error_msg)
                action.result = {"error": error_msg}
            else:
                logger.debug(f"Executing action: {action.name}")
                # 确保参数不为None
                arguments = action.arguments or {}
                action.result = await tool.execute(**arguments)
                logger.debug(f"Action {action.name} completed successfully")

        except Exception as e:
            error_msg = (
                str(e) +
                ". You may need to check the schema of the tool_calling_schema."
            )
            logger.error(f"Action {action.name} failed: {error_msg}")
            action.result = {"error": error_msg}

        return action

    def get_stats(self) -> dict:
        """
        获取执行统计信息

        Returns:
            dict: 包含执行统计的字典
        """
        return {
            "execution_count": self.execution_count,
            "executor_type": "ActionExecutor"
        }