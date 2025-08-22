from typing import List, Union, Literal, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone, timedelta

from workbook_ai.domain.entity.content import ContentPart


# === 复用前面定义的 ContentPart ===
class Message(BaseModel):
    """
    OpenAI 兼容的消息格式，扩展了 role_name 和时间字段。
    """

    role: Literal["system", "user", "assistant", "tool"] = Field(
        default="user", description="消息角色"
    )
    role_name: Optional[str] = Field(
        None, description="角色名称，用于区分不同角色实例"
    )
    content: Union[str, List["ContentPart"]] = Field(
        ..., description="消息内容，可以是字符串或 ContentPart 数组"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone(timedelta(hours=8))),
        description="消息创建时间（北京时间）"
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "role": "system",
                    "role_name": "system-1",
                    "content": "你是一个有帮助的助手。",
                    "created_at": "2025-08-21T06:25:00Z"
                },
                {
                    "role": "user",
                    "role_name": "alice",
                    "content": [
                        {"type": "text", "text": "你好"},
                        {"type": "markdown", "markdown": "**加粗的消息**"},
                        {"type": "json", "json_data": {"key": "value"}}
                    ],
                    "created_at": "2025-08-21T06:26:00Z"
                },
                {
                    "role": "assistant",
                    "role_name": "assistant-zh",
                    "content": "你好！很高兴见到你。",
                    "created_at": "2025-08-21T06:27:00Z"
                }
            ]
        }