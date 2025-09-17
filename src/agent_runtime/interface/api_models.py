"""
API 请求和响应格式统一定义

这个文件包含了所有Agent Runtime API的请求和响应格式，
与核心数据结构分离，专门用于API接口定义。
"""

from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator

from agent_runtime.data_format.qa_format import QAItem, QAList, BQAList
from agent_runtime.data_format.ospa import OSPA
from agent_runtime.data_format.message import Message


# ======================= LLM API Models ==========================


class LLMAskRequest(BaseModel):
    """LLM Ask API 请求模型

    Attributes:
        messages (List[Dict[str, Any]]): 消息列表，遵循 OpenAI 格式
        stream (Optional[bool]): 是否启用流式输出，默认使用配置中的设置
        temperature (Optional[float]): 生成温度，范围 0.0-2.0，默认使用配置中的设置
    """

    messages: List[Dict[str, Any]] = Field(
        ..., description="消息列表，每个消息包含 role 和 content 字段", min_items=1
    )
    stream: Optional[bool] = Field(None, description="是否启用流式输出")
    temperature: Optional[float] = Field(
        None, description="生成温度，控制输出的随机性", ge=0.0, le=2.0
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

from agent_runtime.data_format.fsm import Memory
from agent_runtime.data_format.tool import RequestTool
from agent_runtime.data_format.feedback import Feedback
from agent_runtime.data_format.fsm import StateMachine


class Setting(BaseModel):
    """聊天配置类 - 用于Chat API接口"""

    api_key: str
    chat_model: str = "gpt-4o-mini"
    base_url: str = "https://api.openai.com/v1/"
    top_p: float = 1.0
    temperature: float = 1.0

    embedding_api_key: Optional[str] = None
    embedding_model: str = "text-embedding-3-large"
    embedding_base_url: str = "https://api.openai.com/v1/"
    embedding_vector_dim: int = 1024

    top_k: int = 5
    vector_db_url: str = ""
    agent_name: str

    global_prompt: str = ""
    max_history_len: int = 128
    state_machine: StateMachine = StateMachine()

    @model_validator(mode="after")
    def default_embedding_api_key(self):
        if self.embedding_api_key is None:
            self.embedding_api_key = self.api_key
        return self


class FeedbackSetting(BaseModel):
    """Runtime configuration for the feedback subsystem."""

    vector_db_url: str  # e.g. "http://weaviate.my-cluster.com:8080"
    top_k: int = 5
    agent_name: str

    embedding_api_key: str
    embedding_model: str = ""
    embedding_base_url: str = "https://api.openai.com/v1/"
    embedding_vector_dim: int = 1024


class ChatRequest(BaseModel):
    """聊天请求格式"""

    user_message: Union[str, List[Message]] = Field(
        ..., description="用户消息：可以是字符串（向后兼容）或 ChatML 消息列表格式"
    )
    edited_last_response: str = ""
    recall_last_user_message: bool = False
    settings: Setting
    memory: Memory
    request_tools: List[RequestTool] = []

    @field_validator("user_message")
    @classmethod
    def validate_user_message(cls, v):
        """验证并规范化 user_message 格式"""
        if isinstance(v, str):
            # 字符串格式，转换为 ChatML 格式
            return [Message(role="user", content=v)]
        elif isinstance(v, list):
            # 已经是列表格式，验证每个元素
            if not v:
                raise ValueError("user_message list cannot be empty")

            # 如果是字典列表，转换为 Message 对象
            chat_messages = []
            for item in v:
                if isinstance(item, dict):
                    chat_messages.append(Message(**item))
                elif isinstance(item, Message):
                    chat_messages.append(item)
                else:
                    raise ValueError("Invalid message format in user_message list")

            return chat_messages
        else:
            raise ValueError("user_message must be string or list of Message objects")

    def get_messages(self) -> List[Message]:
        """获取标准化的消息列表"""
        return (
            self.user_message
            if isinstance(self.user_message, list)
            else [Message(role="user", content=self.user_message)]
        )

    def get_user_content(self) -> str:
        """获取用户消息内容（向后兼容）"""
        if isinstance(self.user_message, str):
            return self.user_message
        elif isinstance(self.user_message, list) and self.user_message:
            # 返回最后一个用户消息的内容
            user_messages = [msg for msg in self.user_message if msg.role == "user"]
            if user_messages:
                return user_messages[-1].content
            # 如果没有用户消息，返回最后一个消息的内容
            return self.user_message[-1].content
        return ""


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


class BQAExtractRequest(BaseModel):
    """BQA拆解请求"""

    qa_lists: List[QAList] = Field(
        ..., description="Q&A对话列表，每个QAList代表一个多轮对话"
    )

    context_extraction_mode: str = Field(
        default="auto",
        description="背景提取模式：auto（自动判断）、minimal（最小化）、detailed（详细）",
    )

    preserve_session_info: bool = Field(default=True, description="是否保留会话信息")

    max_concurrent_processing: int = Field(default=3, description="最大并发处理数量")

    def model_post_init(self, __context) -> None:
        """模型初始化后的验证"""
        # 验证模式
        valid_modes = ["auto", "minimal", "detailed"]
        if self.context_extraction_mode not in valid_modes:
            raise ValueError(f"context_extraction_mode必须是{valid_modes}中的一个")

        # 验证并发数量
        if self.max_concurrent_processing < 1 or self.max_concurrent_processing > 10:
            raise ValueError("max_concurrent_processing必须在1-10之间")


class BQAExtractSessionResult(BaseModel):
    """单个会话的BQA拆解结果"""

    session_id: str = Field(..., description="会话ID")
    original_qa_count: int = Field(..., description="原始QA对数量")
    extracted_bqa_count: int = Field(..., description="提取的BQA数量")
    bqa_list: BQAList = Field(..., description="拆解后的BQA列表")
    processing_time_ms: int = Field(..., description="处理时间（毫秒）")
    extraction_summary: str = Field(default="", description="提取摘要")


class BQAExtractResponse(BaseModel):
    """BQA拆解响应"""

    session_results: List[BQAExtractSessionResult] = Field(
        default_factory=list, description="各个会话的拆解结果"
    )

    total_sessions: int = Field(..., description="总会话数")
    total_original_qas: int = Field(..., description="总原始QA对数")
    total_extracted_bqas: int = Field(..., description="总提取BQA数")

    processing_summary: Dict[str, Any] = Field(
        default_factory=dict, description="处理摘要信息"
    )

    operation_log: List[str] = Field(default_factory=list, description="操作日志")

    total_processing_time_ms: int = Field(..., description="总处理时间（毫秒）")


# 这里重新导出以保持API接口的一致性
__all__ = [
    # Core Data Models
    "Setting",
    "FeedbackSetting",
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
