import asyncio
from agent_runtime.clients.weaviate_client import WeaviateClient
from workbook_ai.infrastructure.clients.openai_embedding_client import OpenAIEmbeddingClient
from workbook_ai.infrastructure.config.loader import ConfigLoader

weaviate_config = ConfigLoader.get_weaviate_config()
embed_client_config = ConfigLoader.get_embedding_config()


client = WeaviateClient(**weaviate_config)
embed_client = OpenAIEmbeddingClient(**embed_client_config)

async def run():
    # 1. 获取服务元信息
    print(f"get_meta:{client.get_meta()}")

    print(f"get_schema:{client.get_schema()}")

    # 2. 创建 Collection
    class_name = "Product"
    properties = [{
        "name": "name",
        "dataType": ["text"]
    }, {
        "name": "price",
        "dataType": ["number"]
    }, {
        "name": "brand",
        "dataType": ["text"]
    }]
    description = "产品信息"
    # vector_config = {
    #     "default": {
    #         "vectorizer": {
    #             "text2vec-openai": {
    #                 "model": "text-embedding-v4",
    #                 "api_key": "sk-3d3d383d703c42c0bfea1a21fb56d50e",
    #                 "baseURL":
    #                 "https://dashscope.aliyuncs.com/compatible-mode",
    #                 "encoding_format": "float",
    #                 "type": "text"
    #             }
    #         },
    #         "vectorIndexType": "hnsw",
    #         "vectorIndexConfig": {
    #             "efConstruction": 128,
    #             "maxConnections": 64,
    #             "distance": "cosine"
    #         },
    #     }
    # }
    try:
        client.delete_collection(class_name=class_name)
        client.create_collection(class_name=class_name,
                                 properties=properties,
                                 description=description,
                                 inverted_index_config=None)
    except Exception as e:
        print(e)

    # 3. 添加对象
    try:
        obj = client.create_object(class_name=class_name,
                                   properties={
                                       "name": "iPhone 15",
                                       "price": 799,
                                       "brand": "Apple"
                                   })

        print(f"obj:{obj}")
        print(f"vector len:{len(obj['vectors']['default'])}")
    except Exception as e:
        print(e)
    
    object_id = obj["id"]

    # 4. 查询对象
    print(client.get_object(object_id))

    # 5. 更新对象
    client.patch_object(object_id,
                        class_name="Product",
                        properties={"price": 749})
    print(client.get_object(object_id))

    result = client.get_object_vector(class_name=class_name,
                                      object_id=object_id)
    # print(result)
    query = "三星"
    query_embedding = await embed_client.embed_text(query)
    result = client.search(
        class_name=class_name,
        query=query,
        vector=query_embedding,
        fields=["brand"]
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(run())
    