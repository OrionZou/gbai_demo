"""
API 请求和响应格式统一定义

这个文件包含了所有Agent Runtime API的请求和响应格式，
与核心数据结构分离，专门用于API接口定义。
"""
import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from agent_runtime.data_format.qa_format import QAItem
from agent_runtime.data_format.ospa import OSPA
from agent_runtime.data_format.bqa_extract_format import (
    BQAExtractRequest, BQAExtractResponse
)


# ======================= LLM API Models ==========================

class LLMAskRequest(BaseModel):
    """LLM Ask API 请求模型

    Attributes:
        messages (List[Dict[str, Any]]): 消息列表，遵循 OpenAI 格式
        stream (Optional[bool]): 是否启用流式输出，默认使用配置中的设置
        temperature (Optional[float]): 生成温度，范围 0.0-2.0，默认使用配置中的设置
    """
    messages: List[Dict[str, Any]] = Field(
        ...,
        description="消息列表，每个消息包含 role 和 content 字段",
        min_items=1
    )
    stream: Optional[bool] = Field(
        None,
        description="是否启用流式输出"
    )
    temperature: Optional[float] = Field(
        None,
        description="生成温度，控制输出的随机性",
        ge=0.0,
        le=2.0
    )


class LLMAskResponse(BaseModel):
    """LLM Ask API 响应模型

    Attributes:
        success (bool): 请求是否成功
        message (str): 响应消息或错误信息
        content (Optional[str]): LLM 生成的内容
        model (str): 使用的模型名称
        processing_time_ms (int): 处理耗时（毫秒）
    """
    success: bool
    message: str
    content: Optional[str] = None
    model: str
    processing_time_ms: int


# ======================= Reward API Models ==========================

class RewardRequest(BaseModel):
    """Reward API 请求模型"""
    question: str
    candidates: List[str]
    target_answer: str


# ======================= Backward API Models ==========================

class BackwardRequest(BaseModel):
    """反向知识处理请求模型

    Attributes:
        qas (List[QAItem]): 问答对列表
        chapter_structure (Optional[Dict]): 可选的现有章节结构
        max_level (int): 最大层级深度
        max_concurrent_llm (int): 最大并发LLM调用数量
    """
    qas: List[QAItem]
    chapter_structure: Optional[Dict] = None
    max_level: int = 3
    max_concurrent_llm: int = 10


class BackwardResponse(BaseModel):
    """反向知识处理响应模型

    Attributes:
        success (bool): 处理是否成功
        message (str): 处理消息
        chapter_structure (Dict): 最终的章节结构
        ospa (List[OSPA]): 转换后的OSPA格式数据列表
        total_chapters (int): 生成的章节总数
        total_qas (int): 输入的问答对总数
        total_ospa (int): 生成的OSPA条目总数
        processing_time_ms (int): 处理耗时（毫秒）
    """
    success: bool
    message: str
    chapter_structure: Dict
    ospa: List[OSPA]
    total_chapters: int
    total_qas: int
    total_ospa: int
    processing_time_ms: int


# ======================= Chat V2 API Models ==========================

from agent_runtime.data_format.v2_core import Memory, Setting
from agent_runtime.data_format.tools import RequestTool
from agent_runtime.data_format.feedback import Feedback, FeedbackSetting


class ChatRequest(BaseModel):
    """聊天请求格式"""
    user_message: str = ""
    edited_last_response: str = ""
    recall_last_user_message: bool = False
    settings: Setting
    memory: Memory
    request_tools: List[RequestTool] = []


class ChatResponse(BaseModel):
    """聊天响应格式"""
    response: str
    memory: Memory
    result_type: str = "Success"
    llm_calling_times: int = 0
    total_input_token: int = 0
    total_output_token: int = 0


class LearnRequest(BaseModel):
    """学习请求格式"""
    settings: FeedbackSetting
    feedbacks: List[Feedback]


class LearnResponse(BaseModel):
    """学习响应格式"""
    status: str
    data: List[str]


class GetFeedbackParam(BaseModel):
    """获取反馈参数"""
    agent_name: str
    vector_db_url: str
    offset: int = 0
    limit: int = -1


class DeleteFeedbackParam(BaseModel):
    """删除反馈参数"""
    agent_name: str
    vector_db_url: str


# ======================= BQA Extract API Models ==========================

# BQAExtractRequest 和 BQAExtractResponse 已在 data_format.bqa_extract_format 中定义
# 这里重新导出以保持API接口的一致性
__all__ = [
    # LLM API
    "LLMAskRequest",
    "LLMAskResponse",
    # Reward API
    "RewardRequest",
    # Backward API
    "BackwardRequest",
    "BackwardResponse",
    # Chat V2 API
    "ChatRequest",
    "ChatResponse",
    "LearnRequest",
    "LearnResponse",
    "GetFeedbackParam",
    "DeleteFeedbackParam",
    # BQA Extract API (re-exported)
    "BQAExtractRequest",
    "BQAExtractResponse",
]