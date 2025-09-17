import os
from typing import Optional, Literal, Dict, Any
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# 加载 .env 文件
load_dotenv()


class EmbeddingConfig(BaseModel):
    """
    OpenAI Embedding Client 配置
    对应 openai_embedding_client.py 构造函数所需参数
    """

    api_key: str = os.getenv("EMBEDDING_API_KEY", "")
    model_name: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    base_url: Optional[str] = os.getenv("EMBEDDINGI_BASE_URL")
    dimensions: int = int(os.getenv("EMBEDDING_DIMENSIONS", "1024"))
    timeout: float = float(os.getenv("EMBEDDING_TIMEOUT", "180.0"))
    batch_size: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "10"))


class Text2VecOpenAIConfig(BaseModel):
    """
    Pydantic 配置类，用于 Weaviate 的 text2vec-openai 模块配置。
    支持指定第三方或 OpenAI embedding 服务的参数配置。
    """

    baseURL: Optional[str] = Field(
        os.getenv(
            "EMBEDDINGI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode"
        ).removesuffix("/v1"),
        description="兼容 OpenAI 的服务 base URL，例如 Dashscope Aliyun 服务接口",
    )
    model: str = Field(
        os.getenv("EMBEDDING_MODEL", "text-embedding-v4"),
        description="Embedding 模型名称",
    )
    dimensions: Optional[int] = Field(
        int(os.getenv("EMBEDDING_DIMENSIONS", "1024")),
        description="向量维度（可选，部分 embedding 模型需要显式指定，例如 1536/3072）",
    )
    batch_size: Optional[int] = Field(
        os.getenv("EMBEDDING_BATCH_SIZE", "10"),
        description="批处理大小，影响吞吐性能，默认 16",
    )
    encoding_format: Optional[Literal["float", "fp16", "int8"]] = Field(
        "float", description="向量编码格式，常见值如 'float', 'fp16' 等"
    )
    type: Literal["text", "code"] = Field(
        "text", description="定义输入类型，通常为 'text'"
    )

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "model": "text-embedding-v4",
                "api_key": "your_key",
                "baseURL": "https://dashscope.aliyuncs.com/compatible-mode",
                "encoding_format": "float",
                "type": "text",
            }
        }

    def to_module_config(self) -> dict:
        """
        将当前配置转换为 Weaviate moduleConfig 格式的 dict。
        """
        return {"text2vec-openai": self.dict(by_alias=True, exclude_none=True)}


class WeaviateConfig(BaseModel):
    """
    Weaviate Client 配置
    对应 weaviate_client.py 构造函数所需参数
    """

    base_url: str = os.getenv("WEAVIATE_URL", "http://localhost:8080")
    api_key: Optional[str] = os.getenv("WEAVIATE_API_KEY")
    embedding_api_key: Optional[str] = os.getenv("EMBEDDING_API_KEY")
    module_config: Dict[str, Any] = Text2VecOpenAIConfig().to_module_config()
    timeout: int = int(os.getenv("WEAVIATE_TIMEOUT", "30"))


class ConfigLoader:
    """统一的配置加载器"""

    _embedding_config: Optional[EmbeddingConfig] = None
    _weaviate_config: Optional[WeaviateConfig] = None

    @classmethod
    def get_embedding_setting(cls) -> EmbeddingConfig:
        if cls._embedding_config is None:
            cls._embedding_config = EmbeddingConfig()
        return cls._embedding_config.model_dump()

    @classmethod
    def get_weaviate_config(cls) -> WeaviateConfig:
        if cls._weaviate_config is None:
            cls._weaviate_config = WeaviateConfig()
        return cls._weaviate_config.model_dump()
