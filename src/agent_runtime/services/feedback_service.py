"""
Feedback Service for managing feedbacks using WeaviateClient

基于 WeaviateClient 实现的反馈管理服务，提供完整的反馈CRUD操作。
参考 agent/src/agent/v2/feedback.py 的实现模式。
"""

import json
import asyncio
from typing import List, Optional

from agent_runtime.clients.weaviate_client import WeaviateClient
from agent_runtime.clients.openai_embedding_client import OpenAIEmbeddingClient
from agent_runtime.data_format.feedback import Feedback, FeedbackSetting
from agent_runtime.logging.logger import logger


def convert_to_pascal_case(s: str) -> str:
    """Convert a string to PascalCase for Weaviate collection names."""
    if not s:
        raise ValueError("Input string cannot be empty or None.")

    # Already PascalCase
    if s[0].isupper() and "_" not in s and "-" not in s:
        return s

    # Split and capitalize
    import re

    parts = []
    for chunk in re.split(r"[\s_\-]+", s):
        if chunk:
            parts.append(chunk.lower().capitalize())
    return "".join(parts)


class FeedbackService:
    """
    Feedback管理服务

    使用WeaviateClient提供反馈的增删改查功能，支持向量搜索和标签过滤。
    """

    def __init__(
        self,
        weaviate_client: WeaviateClient,
        embedding_client: Optional[OpenAIEmbeddingClient] = None,
    ):
        """
        初始化FeedbackService

        Args:
            weaviate_client: WeaviateClient实例
            embedding_client: OpenAI嵌入客户端，用于计算文本向量
        """
        self.client = weaviate_client
        self.embedding_client = embedding_client
        logger.debug(
            f"FeedbackService initialized with embedding: "
            f"{embedding_client is not None}"
        )

    def _get_collection_name(self, agent_name: str) -> str:
        """获取集合名称"""
        return convert_to_pascal_case(agent_name)

    async def _ensure_collection_exists(self, agent_name: str) -> str:
        """确保集合存在，如果不存在则创建"""
        collection_name = self._get_collection_name(agent_name)

        try:
            # 检查集合是否存在
            await self._get_collection_info(collection_name)
            logger.debug(f"Collection {collection_name} already exists")
        except Exception:
            # 集合不存在，创建新集合
            logger.info(f"Creating collection: {collection_name}")
            properties = [
                {
                    "name": "text",
                    "dataType": ["text"],
                    "description": "Feedback content as JSON",
                },
                {
                    "name": "tags",
                    "dataType": ["text[]"],
                    "description": "Tags for filtering",
                },
            ]

            vector_config = {
                "default": {
                    "vectorizer": "none",  # Manual vectors
                    "vectorIndexType": "hnsw",
                    "vectorIndexConfig": {
                        "efConstruction": 128,
                        "maxConnections": 64,
                        "distance": "cosine",
                    },
                }
            }

            await asyncio.to_thread(
                self.client.create_collection,
                class_name=collection_name,
                properties=properties,
                description=f"Feedback collection for agent: {agent_name}",
                vector_config=vector_config,
            )
            logger.info(f"Collection {collection_name} created successfully")

        return collection_name

    async def _get_collection_info(self, collection_name: str) -> dict:
        """获取集合信息"""
        return await asyncio.to_thread(self.client.get_collection, collection_name)

    async def _embed_text(self, text: str) -> List[float]:
        """
        使用OpenAI API计算文本嵌入向量

        Args:
            text: 要嵌入的文本

        Returns:
            List[float]: 嵌入向量

        Raises:
            ValueError: 当没有配置嵌入客户端时
        """
        if self.embedding_client is None:
            # 如果没有嵌入客户端，使用简单的哈希嵌入
            return self._simple_hash_embedding(text)

        try:
            # 使用OpenAI API计算嵌入
            vector = await self.embedding_client.embed_text(text)
            logger.debug(f"Generated embedding vector of dimension {len(vector)}")
            return vector
        except Exception as e:
            logger.warning(f"OpenAI embedding failed, using fallback: {e}")
            # 如果API失败，回退到简单嵌入
            return self._simple_hash_embedding(text)

    def _simple_hash_embedding(self, text: str) -> List[float]:
        """
        简单的哈希嵌入作为备用方案

        Args:
            text: 要嵌入的文本

        Returns:
            List[float]: 简单嵌入向量
        """
        import hashlib

        # 创建一个简单的向量表示
        hash_obj = hashlib.sha256(text.encode())
        hex_hash = hash_obj.hexdigest()

        # 转换为固定长度的浮点向量 (384维，兼容常见嵌入模型)
        # dimensions = self.embedding_client.dimensions
        dimensions = 384
        vector = []
        part_d = int(dimensions / 4)
        for i in range(0, part_d):  # 96 * 4 = 384
            chunk_start = i % len(hex_hash)
            chunk_end = (i % len(hex_hash)) + 4
            chunk = hex_hash[chunk_start:chunk_end].ljust(4, "0")
            try:
                # 归一化到[-0.5, 0.5]
                val = int(chunk, 16) / 65535.0 - 0.5
                vector.append(val)
            except ValueError:
                vector.append(0.0)

        # 扩展到384维
        while len(vector) < dimensions:
            remaining = dimensions - len(vector)
            to_extend = min(remaining, len(vector))
            vector.extend(vector[:to_extend])

        return vector[:dimensions]

    async def add_feedbacks(
        self, settings: FeedbackSetting, feedbacks: List[Feedback]
    ) -> List[str]:
        """
        添加反馈到Weaviate

        Args:
            settings: 反馈设置
            feedbacks: 反馈列表

        Returns:
            List[str]: 插入对象的ID列表
        """
        if not feedbacks:
            logger.warning("No feedbacks to add")
            return []

        collection_name = await self._ensure_collection_exists(settings.agent_name)

        # 生成向量（并发处理）
        texts = [fb.observation_content for fb in feedbacks]
        if self.embedding_client is not None:
            # 使用OpenAI批量嵌入API提高效率
            try:
                vectors = await self.embedding_client.embed_texts(texts)
                logger.debug(
                    f"Generated {len(vectors)} embedding vectors using OpenAI API"
                )
            except Exception as e:
                logger.warning(f"Batch embedding failed, using fallback: {e}")
                vectors = [self._simple_hash_embedding(text) for text in texts]
        else:
            # 没有嵌入客户端，使用简单嵌入
            vectors = [self._simple_hash_embedding(text) for text in texts]

        inserted_ids = []
        for feedback, vector in zip(feedbacks, vectors):
            try:
                properties = {
                    "text": feedback.model_dump_json(),
                    "tags": feedback.tags(),
                }

                result = await asyncio.to_thread(
                    self.client.create_object,
                    class_name=collection_name,
                    properties=properties,
                    vector=vector,
                )

                if result and "id" in result:
                    inserted_ids.append(result["id"])
                    logger.debug(f"Inserted feedback with ID: {result['id']}")

            except Exception as e:
                logger.error(f"Failed to insert feedback: {e}")
                continue

        logger.info(
            f"Successfully added {len(inserted_ids)} feedbacks to " f"{collection_name}"
        )
        return inserted_ids

    async def delete_collection(self, agent_name: str) -> None:
        """
        删除整个集合

        Args:
            agent_name: 代理名称
        """
        collection_name = self._get_collection_name(agent_name)

        try:
            await asyncio.to_thread(self.client.delete_collection, collection_name)
            logger.info(f"Collection {collection_name} deleted successfully")
        except Exception as e:
            logger.error(f"Failed to delete collection {collection_name}: {e}")
            raise

    async def get_feedbacks(
        self, agent_name: str, offset: int = 0, limit: int = -1
    ) -> List[Feedback]:
        """
        获取所有反馈

        Args:
            agent_name: 代理名称
            offset: 偏移量
            limit: 限制数量，-1表示无限制

        Returns:
            List[Feedback]: 反馈列表
        """
        collection_name = await self._ensure_collection_exists(agent_name)

        try:
            # 获取对象列表
            if limit == -1:
                count = await self.get_feedback_count(agent_name)
                limit = count

            result = await asyncio.to_thread(
                self.client.list_objects,
                class_name=collection_name,
                limit=limit,
                offset=offset,
            )

            feedbacks = []
            if result and "objects" in result:
                for obj in result["objects"]:
                    try:
                        if "properties" in obj and "text" in obj["properties"]:
                            fb_json = json.loads(obj["properties"]["text"])
                            feedbacks.append(Feedback(**fb_json))
                    except Exception as e:
                        logger.warning(f"Failed to parse feedback object: {e}")
                        continue

            logger.debug(f"Retrieved {len(feedbacks)} feedbacks from {collection_name}")
            return feedbacks

        except Exception as e:
            logger.error(f"Failed to get feedbacks from {collection_name}: {e}")
            return []

    async def delete_all_feedbacks(self, agent_name: str) -> None:
        """
        删除所有反馈（保留集合）

        Args:
            agent_name: 代理名称
        """
        collection_name = await self._ensure_collection_exists(agent_name)

        try:
            # 获取所有对象ID
            result = await asyncio.to_thread(
                self.client.list_objects,
                class_name=collection_name,
                limit=20000,  # 批量删除
            )

            if result and "objects" in result:
                for obj in result["objects"]:
                    if "id" in obj:
                        try:
                            await asyncio.to_thread(
                                self.client.delete_object, object_id=obj["id"]
                            )
                        except Exception as e:
                            logger.warning(f"Failed to delete object {obj['id']}: {e}")

            logger.info(f"All feedbacks deleted from {collection_name}")

        except Exception as e:
            logger.error(f"Failed to delete all feedbacks from {collection_name}: {e}")
            raise

    async def get_feedback_count(self, agent_name: str) -> int:
        """
        获取反馈数量

        Args:
            agent_name: 代理名称

        Returns:
            int: 反馈数量
        """
        collection_name = await self._ensure_collection_exists(agent_name)

        try:
            result = await asyncio.to_thread(
                self.client.list_objects,
                class_name=collection_name,
                limit=20000,  # 大数量获取计数
            )

            count = 0
            if result and "objects" in result:
                count = len(result["objects"])

            logger.debug(f"Feedback count in {collection_name}: {count}")
            return count

        except Exception as e:
            logger.error(f"Failed to get feedback count from {collection_name}: {e}")
            return 0

    async def query_feedbacks(
        self, settings: FeedbackSetting, query: str, tags: Optional[List[str]] = None
    ) -> List[Feedback]:
        """
        查询反馈（向量搜索）

        Args:
            settings: 反馈设置
            query: 查询文本
            tags: 可选的标签过滤

        Returns:
            List[Feedback]: 匹配的反馈列表
        """
        if not query:
            logger.warning("Empty query provided")
            return []

        collection_name = await self._ensure_collection_exists(settings.agent_name)

        try:
            # 生成查询向量
            query_vector = await self._embed_text(query)

            # 构建搜索字段
            fields = ["text", "tags"]

            # 使用WeaviateClient的search方法
            result = await asyncio.to_thread(
                self.client.search,
                class_name=collection_name,
                fields=fields,
                vector=query_vector,
                limit=settings.top_k,
            )

            feedbacks = []
            if result and "data" in result and "Get" in result["data"]:
                objects = result["data"]["Get"].get(collection_name, [])

                for obj in objects:
                    try:
                        if "text" in obj:
                            fb_json = json.loads(obj["text"])
                            feedback = Feedback(**fb_json)

                            # 如果指定了标签过滤，检查标签匹配
                            if tags:
                                feedback_tags = feedback.tags()
                                if not any(tag in feedback_tags for tag in tags):
                                    continue

                            feedbacks.append(feedback)
                    except Exception as e:
                        logger.warning(
                            f"Failed to parse feedback from search result: {e}"
                        )
                        continue

            logger.debug(
                f"Query returned {len(feedbacks)} feedbacks from " f"{collection_name}"
            )
            return feedbacks

        except Exception as e:
            logger.error(f"Failed to query feedbacks from {collection_name}: {e}")
            return []
