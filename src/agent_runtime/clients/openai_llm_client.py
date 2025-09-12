from __future__ import annotations
import json
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel
from openai import AsyncOpenAI, AuthenticationError, OpenAIError
from tenacity import retry, stop_after_attempt, wait_random_exponential

from agent_runtime.config.loader import LLMSetting

from agent_runtime.clients.utils import fix_json

from agent_runtime.logging.logger import logger

ToolChoiceLiteral = Literal["none", "auto", "required"]


class LLM:
    # SINGLETON_KEY = "config_name"  # 按 config_name 分组单例

    def __init__(
        self,
        config_name: str = "openai",
        llm_setting: LLMSetting = LLMSetting(),
    ):
        # if self._mark_initialized_once():
        #     return  # 已初始化过（同一 key 再次调用会直接返回）

        # 基础配置
        self.model: str = llm_setting.model
        self.base_url: Optional[str] = llm_setting.base_url
        self.api_key: Optional[str] = llm_setting.api_key
        self.timeout: Optional[float] = llm_setting.timeout

        # 采样与配额
        self.max_completion_tokens: int = llm_setting.max_completion_tokens
        self.temperature: float = llm_setting.temperature
        self.top_p: float = llm_setting.top_p
        self.stream: bool = llm_setting.stream
        # OpenAI 客户端
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
        )

    # ----------------- 基础对话 -----------------
    @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
    async def ask(
        self,
        messages: List[Dict[str, Any]],
        stream: Optional[bool] = None,
        temperature: Optional[float] = None,
    ) -> str:
        stream = self.stream if stream is None else stream
        try:
            if not stream:
                rsp = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_completion_tokens=self.max_completion_tokens,
                    temperature=(
                        temperature if temperature is not None else self.temperature
                    ),
                    stream=False,
                )
                if not rsp.choices or not rsp.choices[0].message.content:
                    raise ValueError("Empty or invalid response from LLM")
                return rsp.choices[0].message.content

            # streaming
            rsp = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_completion_tokens=self.max_completion_tokens,
                temperature=(
                    temperature if temperature is not None else self.temperature
                ),
                stream=True,
            )
            chunks: List[str] = []
            async for chunk in rsp:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    chunks.append(delta)
            #         print(delta, end="", flush=True)
            # print()
            text = "".join(chunks).strip()
            if not text:
                raise ValueError("Empty response from streaming LLM")
            return text

        except ValueError as ve:
            logger.error(f"Validation error: {ve}")
            raise
        except OpenAIError as oe:
            # 可按需细分 RateLimitError / APIError 等
            if isinstance(oe, AuthenticationError):
                logger.error("Authentication failed. Check API key.")
            else:
                logger.error(f"OpenAI API error: {oe}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in ask: {e}")
            raise

    # ----------------- 工具调用 -----------------
    @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
    async def ask_tool(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: ToolChoiceLiteral = "auto",
        temperature: Optional[float] = None,
        timeout: Optional[float] = None,
    ):
        """
        使用 function/tool-calling。返回底层 message（与 OpenAI SDK 对齐）。
        """
        if tool_choice not in ("none", "auto", "required"):
            raise ValueError(f"Invalid tool_choice: {tool_choice}")

        try:
            # 如果需要 per-request timeout，可通过 with_options 临时覆盖
            client = (
                self.client.with_options(timeout=timeout) if timeout else self.client
            )
            rsp = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=(
                    temperature if temperature is not None else self.temperature
                ),
                tools=tools,
                tool_choice=tool_choice,  # OpenAI Python SDK 兼容 "none"/"auto"/"required"
            )
            if not rsp.choices or not rsp.choices[0].message:
                raise ValueError("Invalid or empty response from LLM (no message)")
            return rsp.choices[0].message

        except ValueError as ve:
            logger.error(f"Validation error in ask_tool: {ve}")
            raise
        except OpenAIError as oe:
            if isinstance(oe, AuthenticationError):
                logger.error("Authentication failed. Check API key.")
            else:
                logger.error(f"OpenAI API error in ask_tool: {oe}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in ask_tool: {e}")
            raise

    # ------------- 结构化输出（Pydantic 解析） -------------
    @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
    async def structured_output(
        self,
        messages: List[Dict[str, Any]],
        response_format: BaseModel,  # 传入 Pydantic BaseModel 的“类”（不是实例）
        temperature: Optional[float] = None,
    ) -> BaseModel:
        """
        使用 beta.parse 返回结构化对象（Pydantic BaseModel 实例）。
        """
        try:
            rsp = await self.client.chat.completions.parse(
                model=self.model,
                messages=messages,
                temperature=(
                    temperature if temperature is not None else self.temperature
                ),
                response_format=response_format,
            )
            parsed = rsp.choices[0].message.parsed
            if parsed is None:
                raise ValueError("Empty parsed response from LLM")
            return parsed

        except ValueError as ve:
            logger.error(f"Value error in structured_output: {ve}")
            raise
        except OpenAIError as oe:
            logger.error(f"OpenAI API error in structured_output: {oe}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in structured_output: {e}")
            raise

    # ------------- 结构化输出（Pydantic 解析） -------------
    @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
    async def structured_output_old(
        self,
        messages: List[Dict[str, Any]],
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        使用 json_object 格式返回结构化 JSON 对象。
        """

        try:
            rsp = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,  # 按照 openai.ChatCompletion API 要求传入
                temperature=self.temperature if temperature is None else temperature,
                response_format={"type": "json_object"},
            )
            message = rsp.choices[0].message
            if not message or not message.content:
                raise ValueError("Empty response content from LLM")
            parsed: Any = fix_json(message.content)
            if not isinstance(parsed, dict) and not isinstance(parsed, list):
                raise ValueError("Response is not a valid JSON object")
            return parsed
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error in structured_output_old: {e}")
            raise ValueError(
                f"Failed to parse LLM response as JSON: {message.content}"
            ) from e
        except ValueError as ve:
            logger.error(f"Value error in structured_output_old: {ve}")
            raise
        except OpenAIError as oe:
            logger.error(f"OpenAI API error in structured_output_old: {oe}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in structured_output_old: {e}")
            raise
