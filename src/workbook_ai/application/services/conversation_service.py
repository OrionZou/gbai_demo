import uuid
import time
from typing import List, Optional

from agent_runtime.clients.weaviate_client import WeaviateClient
from workbook_ai.domain.message_entity import OSPAMessage, MESSAGE_CLASS


class ConversationService:
    """
    基于 Weaviate 的多轮对话管理服务
    """

    def __init__(self, client: WeaviateClient):
        self.client = client

    # ========== CRUD ==========
    def create_message(
        self,
        session_id: str,
        role: str,
        content: str
    ) -> OSPAMessage:
        """创建一条新的对话消息"""
        msg = OSPAMessage(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role=role,
            content=content,
            timestamp=time.time()
        )
        self.client.create_object(
            class_name=MESSAGE_CLASS,
            properties=msg.model_dump(),
            object_id=str(msg.id)
        )
        return msg

    def get_messages(
        self,
        session_id: str,
        limit: int = 50
    ) -> List[OSPAMessage]:
        """按 session_id 获取所有消息，默认最多返回 50 条"""
        resp = self.client.search(
            class_name=MESSAGE_CLASS,
            fields=["session_id", "role", "content", "timestamp"],
            query=None,
            filters={
                "path": ["session_id"],
                "operator": "Equal",
                "valueText": session_id,
            },
            limit=limit,
        )
        data = resp.get("data", {}).get("Get", {}).get(MESSAGE_CLASS, [])
        return [OSPAMessage(**item) for item in data]

    def update_message(
        self,
        message_id: str,
        new_content: str
    ) -> Optional[OSPAMessage]:
        """更新某条消息的内容"""
        patched = self.client.patch_object(
            object_id=message_id,
            class_name=MESSAGE_CLASS,
            properties={"content": new_content},
        )
        if patched and "properties" in patched:
            return OSPAMessage(**patched["properties"])
        return None

    def delete_message(self, message_id: str) -> None:
        """删除某条消息"""
        self.client.delete_object(message_id)

    def delete_conversation(self, session_id: str) -> None:
        """删除某个会话下的所有消息"""
        messages = self.get_messages(session_id=session_id, limit=9999)
        for msg in messages:
            if msg.id:
                self.delete_message(msg.id)