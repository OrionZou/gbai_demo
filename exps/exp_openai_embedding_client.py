from workbook_ai.infrastructure.clients.openai_embedding_client import OpenAIEmbeddingClient
from workbook_ai.infrastructure.config.loader import ConfigLoader

embed_client_config = ConfigLoader.get_embedding_config()


async def main():
    client = OpenAIEmbeddingClient(**embed_client_config)

    texts = ["Weaviate is a vector database.", "OpenAI embeddings test."] * 20
    embeddings = await client.embed_texts(texts, concurrent=True)
    print(embeddings[8:10])
    print(f"共生成 {len(embeddings)} 个向量，每个长度={len(embeddings[0])}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
