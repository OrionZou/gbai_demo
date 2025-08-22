import asyncio
from typing import List, Optional
from openai import AsyncOpenAI

from workbook_ai.infrastructure.logging.logger import logger


class OpenAIEmbeddingClient:
    """
    使用 OpenAI API 实现的异步向量嵌入客户端。
    特性：
    - 支持批量文本嵌入
    - 自动清洗输入
    - 支持并发批量处理
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "text-embedding-3-small",
        base_url: Optional[str] = None,
        dimensions: Optional[int] = None,
        timeout: float = 180.0,
        batch_size: int = 10,
    ):
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = base_url
        self.dimensions = dimensions
        self.batch_size = batch_size

        self.async_client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
        )

        logger.info(
            f"✅ OpenAIEmbeddingClient 初始化完成 "
            f"(model='{model_name}', base_url='{base_url or 'default'}', "
            f"timeout={timeout}s, batch_size={batch_size})")

    async def embed_text(self, text: str) -> List[float]:
        """
        将单个文本转换为嵌入向量。
        """
        logger.debug(f"正在嵌入单文本，长度 {len(text)} 字符")
        results = await self.embed_texts([text])
        return results[0]

    async def embed_texts(self,
                          texts: List[str],
                          concurrent: bool = True) -> List[List[float]]:
        """
        将一组文本转换为嵌入向量。
        支持批量并发请求。

        Args:
            texts: 文本列表
            concurrent: 是否启用并发批量处理
        """
        if not texts:
            return []

        # 清洗文本（OpenAI 官方建议：替换换行符）
        cleaned_texts = [
            self._clean_input(t).replace("\n", " ") for t in texts
        ]
        logger.debug(f"开始嵌入，共 {len(cleaned_texts)} 条文本")

        # 按 batch_size 切分
        batches = [
            cleaned_texts[i:i + self.batch_size]
            for i in range(0, len(cleaned_texts), self.batch_size)
        ]

        # 定义处理单批任务
        async def process_batch(batch):
            try:
                response = await self.async_client.embeddings.create(
                    input=batch,
                    model=self.model_name,
                    dimensions=self.dimensions,
                )
                return [item.embedding for item in response.data]
            except Exception as e:
                logger.exception(f"OpenAI 嵌入请求失败: {e}")
                raise

        # 并发 or 串行
        if concurrent:
            responses = await asyncio.gather(*(process_batch(batch)
                                               for batch in batches))
        else:
            responses = []
            for batch in batches:
                responses.append(await process_batch(batch))

        embeddings = [
            vec for batch_result in responses for vec in batch_result
        ]
        logger.info(
            f"嵌入完成：输入 {len(cleaned_texts)} 条 → 输出 {len(embeddings)} 向量")
        return embeddings

    @staticmethod
    def _clean_input(text_input: str) -> str:
        """
        清理输入文本，移除无效字符，使其更适合嵌入模型处理。
        """
        cleaned = text_input.encode("utf-8", errors="ignore").decode("utf-8")

        # 移除零宽字符
        zero_width_chars = "\u200b\u200c\u200d\ufeff\u2060"
        for char in zero_width_chars:
            cleaned = cleaned.replace(char, "")

        # 过滤控制符
        cleaned = "".join(char for char in cleaned
                          if ord(char) >= 32 or char in "\n\r\t")

        return cleaned
