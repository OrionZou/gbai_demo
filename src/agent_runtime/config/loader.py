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
    base_url: str = Field(default_factory=lambda: os.getenv(
        "LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
                          description="API base URL")
    api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("LLM_API_KEY", None),
        description="API key")
    timeout: float = float(os.getenv("LLM_TIMEOUT", "180.0"))
    max_completion_tokens: int = Field(
        default_factory=lambda: int(
            os.getenv("LLM_MAX_COMPLETION_TOKENS", 2048)),
        description="Maximum number of tokens per request")
    temperature: float = Field(
        default_factory=lambda: float(os.getenv("LLM_TEMPERATURE", "0.0")),
        ge=0.0,
        le=2.0,
        description="Sampling temperature")
    top_p: float = Field(
        default_factory=lambda: float(os.getenv("LLM_TOP_P", "1.0")),
        ge=0.0,
        le=1.0,
        description="Nucleus sampling p")
    stream: bool = Field(
        default_factory=lambda: _parse_bool(os.getenv("LLM_STREAM"), True),
        description="Stream chat completion")

    api_type: Literal["openai", "azure"] = Field(
        default_factory=lambda: os.getenv("LLM_API_TYPE", "openai") or
        "openai",  # 转换成 str 再保证符合 Literal
        description="Backend type")
    api_version: Optional[str] = Field(
        default_factory=lambda: os.getenv("LLM_API_VERSION", None),
        description="Azure OpenAI API version (if api_type=='azure')")

    @model_validator(mode="after")
    def _azure_checks(self) -> "LLMSetting":
        if self.api_type == "azure":
            if not self.base_url:
                raise ValueError("For Azure, base_url is required "
                                 "例如: https://<res>.openai.azure.com")
            if not self.api_version:
                raise ValueError("For Azure, api_version is required")
        return self


class SettingLoader:
    """统一的配置加载器（简单缓存）"""
    _llm_setting: Optional[LLMSetting] = None

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
