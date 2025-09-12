from typing import Dict, Any, Optional
from workbook_ai.infrastructure.clients.openai_embedding_client import (
    OpenAIEmbeddingClient,
)
from agent_runtime.clients.weaviate_client import (
    WeaviateClient,
)
from workbook_ai.infrastructure.logging.logger import logger


class EmbeddingService:
    """
    Service: 结合 OpenAIEmbeddingClient 和 WeaviateClient
    实现对象向量化并存入 Weaviate 数据库。
    """

    def __init__(
        self,
        embedding_client: OpenAIEmbeddingClient,
        weaviate_client: WeaviateClient,
    ):
        self.embedding_client = embedding_client
        self.weaviate_client = weaviate_client

    async def embed_and_store(
        self,
        class_name: str,
        properties: Dict[str, Any],
        text_for_embedding: str,
        object_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        对指定文本进行 embedding，并结合对象属性存入 Weaviate。

        Args:
            class_name: Weaviate collection 名称
            properties: 对象属性
            text_for_embedding: 用于生成 embedding 的文本
            object_id: 可选对象ID

        Returns:
            Weaviate API 响应 (Dict)
        """
        logger.info(
            f"🔄 开始生成 embedding "
            f"(class={class_name}, text_length={len(text_for_embedding)})"
        )
        vector = await self.embedding_client.embed_text(text_for_embedding)
        logger.info(f"✅ 向量生成完成，维度 {len(vector)}")

        if object_id:
            result = self.weaviate_client.create_object(
                class_name=class_name,
                properties=properties,
                object_id=object_id,
                vector=vector,
            )
        else:
            result = self.weaviate_client.create_object(
                class_name=class_name,
                properties=properties,
                vector=vector,
            )
        logger.info(
            f"📦 对象已写入 Weaviate "
            f"(class={class_name}, id={result.get('id')})"
        )
        return result