from abc import ABC, abstractmethod
from typing import Optional, Any, Dict
from enum import Enum
import httpx
from pydantic import BaseModel


class BaseTool(ABC, BaseModel):
    """工具基类"""
    name: str
    description: str

    @abstractmethod
    async def execute(self, **kwargs: Any) -> Dict[str, Any]:
        """Execute the tool with given parameters."""

    def get_tool_calling_schema(self) -> Dict[str, Any]:
        """Convert tool to function call format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.get_parameters(),
            },
        }

    def get_parameters(self) -> Dict[str, Any]:
        """Get the parameters of the tool."""
        return {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        }


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


class RequestMethodEnum(Enum):
    """HTTP请求方法枚举"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class RequestTool(BaseTool):
    """HTTP请求工具"""
    url: str
    method: RequestMethodEnum
    headers: Optional[Dict[str, Any]] = None
    request_params: Optional[Dict[str, Any]] = None
    request_json: Optional[Dict[str, Any]] = None

    async def execute(
        self,
        request_params: Optional[Dict[str, Any]] = None,
        request_json: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """执行HTTP请求"""
        try:
            async with httpx.AsyncClient() as client:
                params_in_url = self.url.split("?")
                if len(params_in_url) > 1:
                    url = params_in_url[0]
                    query_params = params_in_url[1].split("&")
                    query_params_dict = {
                        param.split("=")[0]: param.split("=")[1]
                        for param in query_params
                    }
                    merged_params = {**query_params_dict}
                    if request_params:
                        merged_params.update(request_params)
                    request_params = merged_params
                else:
                    url = self.url

                response = await client.request(
                    method=self.method.value,
                    url=url,
                    headers=self.headers,
                    params=request_params,
                    json=request_json,
                )
        except Exception as e:
            return {"error": str(e)}

        try:
            response_content = response.json()
        except ValueError:
            response_content = response.text

        return {
            "status_code": response.status_code,
            "content": response_content,
        }

    def get_parameters(self) -> Dict[str, Any]:
        """获取工具参数"""
        return_schema = super().get_parameters()

        if self.request_params is not None:
            return_schema["properties"]["request_params"] = {
                "type": "object",
                "description": (
                    "The parameters to send with the request. "
                    "Required for GET and DELETE requests. "
                    "Optional for POST, PUT, and PATCH requests."
                ),
                "properties": self.request_params,
                "required": list(self.request_params.keys()),
                "additionalProperties": False,
            }
            return_schema["required"].append("request_params")

        if self.request_json is not None:
            return_schema["properties"]["request_json"] = {
                "type": "object",
                "description": (
                    "The JSON body to send with the request. "
                    "Required for POST, PUT, and PATCH requests."
                ),
                "properties": self.request_json,
                "required": list(self.request_json.keys()),
                "additionalProperties": False,
            }
            return_schema["required"].append("request_json")

        return return_schema