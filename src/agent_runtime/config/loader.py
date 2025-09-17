import os
from typing import Optional, Literal, Dict, Any
from dotenv import load_dotenv
from pydantic import BaseModel, Field, model_validator

load_dotenv()


def _parse_bool(val: Optional[str], default: bool = True) -> bool:
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on", "y"}


class LLMSetting(BaseModel):
    model: str = Field(default_factory=lambda: os.getenv("LLM_MODEL", ""))
    base_url: str = Field(
        default_factory=lambda: os.getenv(
            "LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
        ),
        description="API base URL",
    )
    api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("LLM_API_KEY", None), description="API key"
    )
    timeout: float = float(os.getenv("LLM_TIMEOUT", "180.0"))
    max_completion_tokens: int = Field(
        default_factory=lambda: int(os.getenv("LLM_MAX_COMPLETION_TOKENS", 2048)),
        description="Maximum number of tokens per request",
    )
    temperature: float = Field(
        default_factory=lambda: float(os.getenv("LLM_TEMPERATURE", "0.0")),
        ge=0.0,
        le=2.0,
        description="Sampling temperature",
    )
    top_p: float = Field(
        default_factory=lambda: float(os.getenv("LLM_TOP_P", "1.0")),
        ge=0.0,
        le=1.0,
        description="Nucleus sampling p",
    )
    stream: bool = Field(
        default_factory=lambda: _parse_bool(os.getenv("LLM_STREAM"), True),
        description="Stream chat completion",
    )

    api_type: Literal["openai", "azure"] = Field(
        default_factory=lambda: os.getenv("LLM_API_TYPE", "openai")
        or "openai",  # 转换成 str 再保证符合 Literal
        description="Backend type",
    )
    api_version: Optional[str] = Field(
        default_factory=lambda: os.getenv("LLM_API_VERSION", None),
        description="Azure OpenAI API version (if api_type=='azure')",
    )

    @model_validator(mode="after")
    def _azure_checks(self) -> "LLMSetting":
        if self.api_type == "azure":
            if not self.base_url:
                raise ValueError(
                    "For Azure, base_url is required "
                    "例如: https://<res>.openai.azure.com"
                )
            if not self.api_version:
                raise ValueError("For Azure, api_version is required")
        return self


class EmbeddingSetting(BaseModel):
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
        return {"text2vec-openai": self.model_dump(by_alias=True, exclude_none=True)}


class WeaviateConfig(BaseModel):
    """
    Weaviate Client 配置
    对应 weaviate_client.py 构造函数所需参数
    """

    base_url: str = Field(
        default_factory=lambda: os.getenv("WEAVIATE_URL", "http://localhost:8080")
    )
    api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("WEAVIATE_API_KEY")
    )
    embedding_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("EMBEDDING_API_KEY")
    )
    module_config: Dict[str, Any] = Text2VecOpenAIConfig().to_module_config()
    timeout: int = Field(
        default_factory=lambda: int(os.getenv("WEAVIATE_TIMEOUT", "30"))
    )


class SettingLoader:
    """统一的配置加载器（简单缓存）"""

    _llm_setting: Optional[LLMSetting] = None

    _embedding_setting: Optional[EmbeddingSetting] = None
    _weaviate_config: Optional[WeaviateConfig] = None

    @classmethod
    def get_embedding_setting(cls) -> EmbeddingSetting:
        if cls._embedding_setting is None:
            cls._embedding_setting = EmbeddingSetting()
        return cls._embedding_setting

    @classmethod
    def get_weaviate_config(cls) -> WeaviateConfig:
        if cls._weaviate_config is None:
            cls._weaviate_config = WeaviateConfig()
        return cls._weaviate_config

    @classmethod
    def get_llm_setting(cls) -> LLMSetting:
        if cls._llm_setting is None:
            cls._llm_setting = LLMSetting()
        return cls._llm_setting

    @classmethod
    def set_llm_setting(cls, data: Dict[str, Any]) -> LLMSetting:
        """更新全局 LLM 配置"""
        cls._llm_setting = LLMSetting(**data)
        return cls._llm_setting
