"""
Tool Base Classes

工具系统的基础类定义，提供统一的工具接口和抽象
"""

from abc import ABC, abstractmethod
from typing import Any, Dict
from pydantic import BaseModel


class BaseTool(ABC, BaseModel):
    """工具基类

    所有工具的抽象基类，定义了工具的基本接口和行为规范。

    Attributes:
        name (str): 工具名称，必须唯一
        description (str): 工具描述，用于LLM理解工具功能
    """

    name: str
    description: str

    @abstractmethod
    async def execute(self, **kwargs: Any) -> Dict[str, Any]:
        """执行工具操作

        所有工具子类必须实现此方法

        Args:
            **kwargs: 工具执行的参数，具体参数由各工具定义

        Returns:
            Dict[str, Any]: 工具执行结果，通常包含执行状态和返回数据

        Raises:
            NotImplementedError: 子类未实现此方法时抛出
        """
        pass

    def get_tool_calling_schema(self) -> Dict[str, Any]:
        """获取工具调用模式

        生成适用于LLM工具调用的JSON Schema格式

        Returns:
            Dict[str, Any]: 符合OpenAI Function Calling规范的工具描述
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.get_parameters(),
            },
        }

    def get_parameters(self) -> Dict[str, Any]:
        """获取工具参数模式

        定义工具的参数结构，用于LLM理解如何调用工具

        Returns:
            Dict[str, Any]: JSON Schema格式的参数定义

        Note:
            子类可以重写此方法来定义特定的参数结构
        """
        return {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        }