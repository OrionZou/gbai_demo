from typing import Any, Dict
from .base import BaseTool


class SendMessageToUser(BaseTool):
    """发送消息给用户的工具"""

    name: str = "send_message_to_user"
    description: str = "Send a message to the user."

    async def execute(self, agent_message: str = "") -> Dict[str, Any]:
        """执行发送消息操作"""
        # Return empty user_message because we are waiting for the user
        return {"user_message": ""}

    def get_parameters(self) -> Dict[str, Any]:
        """获取工具参数"""
        return_schema = super().get_parameters()
        return_schema["properties"] = {
            "agent_message": {
                "type": "string",
                "description": (
                    "The message to send to the user. "
                    "Can be an empty string if you are passively waiting."
                ),
            }
        }
        return return_schema
