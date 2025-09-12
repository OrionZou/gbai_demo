import uuid
from typing import Dict, Any, List, Optional

from agent_runtime.clients.weaviate_client import WeaviateClient
from workbook_ai.infrastructure.clients.openai_embedding_client import OpenAIEmbeddingClient
from workbook_ai.infrastructure.logging.logger import logger


class KnowledgeBaseService:
    """
    统一知识库存取服务
    - 基于 OpenAIEmbeddingClient 生成向量
    - 使用 WeaviateClient 存储/检索
    """

    def __init__(self, weaviate_client: WeaviateClient, embedding_client: OpenAIEmbeddingClient):
        self.weaviate = weaviate_client
        self.embedding = embedding_client
        logger.info("✅ KnowledgeBaseService 已初始化")

    async def add_document(
        self,
        class_name: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        object_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        插入新文档
        - 生成向量
        - 存储到 Weaviate
        """
        logger.debug(f"📝 开始存储文档: class={class_name}, text_len={len(text)}")

        vector = await self.embedding.embed_text(text)
        obj_id = object_id or str(uuid.uuid4())

        properties = {"text": text}
        if metadata:
            properties.update(metadata)

        result = self.weaviate.create_object(
            class_name=class_name,
            properties=properties,
            object_id=obj_id,
            vector=vector,
        )
        logger.info(f"✅ 文档已存储: id={obj_id}")
        return result

    async def search_similar(
        self, class_name: str, query: str, top_k: int = 5, fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        相似度搜索
        - 为查询生成向量
        - 调用 Weaviate GraphQL 搜索
        """
        vector = await self.embedding.embed_text(query)
        fields = fields or ["id", "text"]

        graphql_query = {
            "query": f"""
            {{
              Get {{
                {class_name}(nearVector: {{vector: {vector}}}, limit: {top_k}) {{
                  {" ".join(fields)}
                  _additional {{ distance id }}
                }}
              }}
            }}
            """
        }

        resp = self.weaviate._request("POST", "/v1/graphql", json=graphql_query)
        hits = resp.get("data", {}).get("Get", {}).get(class_name, [])
        logger.info(f"🔍 搜索完成: query='{query[:30]}' → {len(hits)} 条结果")
        return hits

    def get_document(self, object_id: str) -> Dict[str, Any]:
        """获取单个文档"""
        return self.weaviate.get_object(object_id)

    def delete_document(self, object_id: str) -> None:
        """删除文档"""
        return self.weaviate.delete_object(object_id)