from typing import List, Union, Literal, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone, timedelta

from agent_runtime.data_format.content import ContentPart


# === 复用前面定义的 ContentPart ===
class Message(BaseModel):
    """
    OpenAI 兼容的消息格式，扩展了 name 和时间字段。
    """

    role: Literal["system", "user", "assistant", "tool"] = Field(
        default="user", description="消息角色"
    )
    name: Optional[str] = Field(
        None, description="角色名称，用于区分不同角色实例"
    )
    content: Union[str, List["ContentPart"]] = Field(
        ..., description="消息内容，可以是字符串或 ContentPart 数组"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone(timedelta(hours=8))),
        description="消息创建时间（北京时间）"
    )

    extras: Optional[Dict[str, Any]] = None

    def to_openai_format(self) -> Dict[str, Any]:
        msg: Dict[str, Any] = {"role": self.role, "content": self.content}
        if self.name:
            msg["name"] = self.name
        if self.extras:
            msg.update(self.extras)
        return msg

    @classmethod
    def from_openai_format(cls, data: Dict[str, Any]) -> "Message":
        """Create Message from OpenAI format dict"""
        role = data.get("role", "user")
        content = data.get("content", "")
        name = data.get("name")
        
        # Extract extras (any fields not in standard format)
        extras = {}
        standard_fields = {"role", "content", "name"}
        for key, value in data.items():
            if key not in standard_fields:
                extras[key] = value
        
        return cls(
            role=role,
            content=content,
            name=name,
            extras=extras if extras else None
        )
