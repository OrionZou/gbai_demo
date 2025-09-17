import json
import uuid
import requests
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from workbook_ai.infrastructure.logging.logger import logger


class WeaviateClientError(Exception):
    """Weaviate 客户端自定义异常"""

    def __init__(self,
                 message: str,
                 status_code: Optional[int] = None,
                 response: Optional[Any] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class WeaviateClient:
    """
    Weaviate API 客户端
    - 支持 Schema / Object / Meta 操作
    - 内置日志记录
    - 统一错误处理
    """

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        embedding_api_key: Optional[str] = None,
        module_config: Optional[Dict[str, Any]] = None,
        timeout: int = 30,
    ):
        """
        初始化 Weaviate 客户端。

        :param base_url: Weaviate 服务地址，例如 "http://localhost:8080"
        :param api_key: Weaviate 集群的 API key（可选）
        :param timeout: HTTP 请求超时（秒）
        :param module_config: 全局 moduleConfig 配置，用于向量化模块等设置（参考文档示例：text2vec-openai）
        """

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        # 持有一个 moduleConfig，后续 schema 创建中会注入
        self.module_config = module_config or {}

        self.headers = {"Content-Type": "application/json"}

        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"
        if embedding_api_key:
            self.headers["X-Openai-Api-Key"] = f"{embedding_api_key}"

        logger.info(
            f"✅ WeaviateClient 初始化完成: base_url={self.base_url}, timeout={timeout}s, module_config={self.module_config}"
        )

    # ================== 内部方法 ==================
    def _request(self, method: str, path: str, **kwargs) -> Any:
        """统一封装 HTTP 请求，带日志 & 错误管理"""
        url = f"{self.base_url}{path}"
        try:
            logger.debug(
                f"➡️ 请求: {method} {url} headers={self.headers} kwargs={kwargs}"
            )

            resp = requests.request(
                method,
                url,
                headers=self.headers,
                timeout=self.timeout,
                **kwargs,
            )

            logger.debug(
                f"⬅️ 响应: status={resp.status_code}, body={resp.text[:500]}")

            if not resp.ok:
                raise WeaviateClientError(
                    f"请求失败: {method} {url} → {resp.status_code} {resp.text}",
                    status_code=resp.status_code,
                    response=resp.text,
                )

            if resp.text:
                return resp.json()
            return None
        except requests.RequestException as e:
            logger.exception(f"网络请求错误: {method} {url} {e}")
            raise WeaviateClientError(str(e)) from e

    # ================== 客户端信息 ==================
    def get_meta(self) -> Dict[str, Any]:
        """获取 Weaviate 实例信息"""
        return self._request("GET", "/v1/meta")

    def get_schema(self) -> Dict[str, Any]:
        """获取 Schema 信息"""
        return self._request("GET", "/v1/schema")

    # ================== Collection (Schema) ==================
    def create_collection(
        self,
        class_name: str,
        properties: List[Dict[str, Any]],
        description: Optional[str] = None,
        vector_config: Optional[Dict[str, Any]] = None,
        inverted_index_config: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        创建 Collection (Class)
        使用 Weaviate v1.24+ 推荐的 vectorConfig 配置

        :param class_name: 类名
        :param properties: 属性定义
        :param description: 类描述
        :param vector_config: 向量配置（支持命名向量）
        :param inverted_index_config: 倒排索引配置
        """
        schema: Dict[str, Any] = {
            "class": class_name,
            "properties": properties,
        }

        if description:
            schema["description"] = description

        # schema["moduleConfig"] = self.module_config
        logger.debug(f"self.module_config:{self.module_config}")
        if vector_config:
            schema["vectorConfig"] = vector_config
        else:
            schema["vectorConfig"] = {
                "default": {
                    "vectorizer": self.module_config,
                    "vectorIndexType": "hnsw",
                    "vectorIndexConfig": {
                        "efConstruction": 128,
                        "maxConnections": 64,
                        "distance": "cosine"
                    },
                }
            }

        if inverted_index_config:
            schema["invertedIndexConfig"] = inverted_index_config

        # 允许额外参数覆盖
        schema.update(kwargs)
        logger.debug(f"schema:{schema}")

        return self._request("POST", "/v1/schema", json=schema)

    def delete_collection(self, class_name: str) -> None:
        """删除 Collection"""
        return self._request("DELETE", f"/v1/schema/{class_name}")

    def get_collection(self, class_name: str) -> Dict[str, Any]:
        """获取单个 Collection 信息"""
        return self._request("GET", f"/v1/schema/{class_name}")

    # ================== Object ==================
    def create_object(
        self,
        class_name: str,
        properties: Dict[str, Any],
        additional: Optional[Dict[str, Any]] = None,
        object_id: Optional[str] = None,
        vector: Optional[List[float]] = None,
        vectors: Optional[Dict[str, List[float]]] = None,
        vector_weights: Optional[Dict[str, int]] = None,
    ) -> Dict[str, Any]:
        """创建对象"""
        if object_id is None:
            object_id = str(uuid.uuid4())
        obj = {"class": class_name, "properties": properties, "id": object_id}
        if vector:
            obj["vector"] = vector
        if vectors:
            obj["vectors"] = vectors
        if vector_weights:
            obj["vectorWeights"] = vector_weights
        if additional:
            obj["additional"] = additional

        return self._request("POST", "/v1/objects", json=obj)

    def get_object(self, object_id: str) -> Dict[str, Any]:
        """获取对象"""
        return self._request("GET", f"/v1/objects/{object_id}")

    def patch_object(self, object_id: str, class_name: str,
                     properties: Dict[str, Any]) -> Dict[str, Any]:
        """部分更新对象"""
        return self._request("PATCH",
                             f"/v1/objects/{class_name}/{object_id}",
                             json={
                                 "class": class_name,
                                 "properties": properties
                             })

    def delete_object(self, object_id: str) -> None:
        """删除对象"""
        return self._request("DELETE", f"/v1/objects/{object_id}")

    def list_objects(self,
                     class_name: str,
                     limit: int = 10,
                     offset: int = 0) -> Dict[str, Any]:
        """获取对象列表"""
        path = f"/v1/objects?class={class_name}&limit={limit}&offset={offset}"
        return self._request("GET", path)

    # ================== Search ==================
    def search(
        self,
        class_name: str,
        fields: List[str],
        query: Optional[str] = None,
        vector: Optional[List[float]] = None,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        alpha: float = 0.5,
    ) -> Dict[str, Any]:
        """
        搜索对象 (GraphQL)
        - 支持 keyword (BM25)、vector、hybrid
        :param class_name: 类名
        :param fields: 需要返回的字段 (["title", "content"])
        :param query: 关键字搜索 (BM25 / hybrid)
        :param vector: 向量搜索
        :param limit: 返回数量
        :param filters: where 过滤条件 (dict 格式)
        :param alpha: hybrid 模式下的权重 (0=纯BM25, 1=纯向量)
        """
        search_args = [f"limit: {limit}"]

        if query and vector:
            # Hybrid search
            search_args.append(
                f'hybrid: {{ query: "{query}", vector: {json.dumps(vector)}, alpha: {alpha} }}'
            )
        elif query:
            # BM25
            search_args.append(f'nearText: {{ concepts: ["{query}"] }}')
        elif vector:
            # Vector search
            search_args.append(
                f"nearVector: {{ vector: {json.dumps(vector)} }}")

        if filters:
            where_str = json.dumps(filters).replace('"', '\\"')
            search_args.append(f'where: {where_str}')

        gql = {
            "query":
            f"""{{
                Get {{
                    {class_name}({", ".join(search_args)}) {{
                        {" ".join(fields)}
                        _additional {{ id distance certainty }}
                    }}
                }}
            }}"""
        }

        logger.debug(f"🔎 GraphQL 查询: {json.dumps(gql, ensure_ascii=False)}")

        return self._request("POST", "/v1/graphql", json=gql)

    def get_object_vector(
        self,
        class_name: str,
        object_id: str,
        vector_name: Optional[str] = "default",
    ) -> Dict[str, Any]:
        """
        获取指定对象的向量 (embedding)
        - 默认返回主向量 (_additional.vector)
        - 如果指定 vector_name，则返回 named vector (_additional.vectors[vector_name])

        :param class_name: 类名
        :param object_id: 对象 ID
        :param vector_name: 向量名字（可选，用于 named vectors）
        """
        # 构造 GraphQL 查询
        if vector_name:
            additional = f"""
                _additional {{
                    id
                    vectors {{
                        {vector_name}
                    }}
                }}
            """
        else:
            additional = """
                _additional {
                    id
                    vector
                }
            """

        query = {
            "query":
            f"""
            {{
                Get {{
                    {class_name}(where: {{
                        path: ["id"],
                        operator: Equal,
                        valueText: "{object_id}"
                    }}) {{
                        {additional}
                    }}
                }}
            }}
            """
        }

        logger.debug(
            f"📥 GraphQL 向量查询: {json.dumps(query, ensure_ascii=False)}")
        resp = self._request("POST", "/v1/graphql", json=query)

        # 解析结果
        results = resp.get("data", {}).get("Get", {}).get(class_name, [])
        if not results:
            raise WeaviateClientError(f"未找到对象: {class_name}/{object_id}")

        return results[0]["_additional"]
