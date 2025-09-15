"""
BQA拆解接口的数据格式定义

这个模块定义了将多轮对话拆解为独立内容BQA的请求和响应格式
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from agent_runtime.data_format.qa_format import QAList, BQAList


class BQAExtractRequest(BaseModel):
    """BQA拆解请求"""

    qa_lists: List[QAList] = Field(
        ...,
        description="Q&A对话列表，每个QAList代表一个多轮对话"
    )

    context_extraction_mode: str = Field(
        default="auto",
        description="背景提取模式：auto（自动判断）、minimal（最小化）、detailed（详细）"
    )

    preserve_session_info: bool = Field(
        default=True,
        description="是否保留会话信息"
    )

    max_concurrent_processing: int = Field(
        default=3,
        description="最大并发处理数量"
    )

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
        default_factory=list,
        description="各个会话的拆解结果"
    )

    total_sessions: int = Field(..., description="总会话数")
    total_original_qas: int = Field(..., description="总原始QA对数")
    total_extracted_bqas: int = Field(..., description="总提取BQA数")

    processing_summary: Dict[str, Any] = Field(
        default_factory=dict,
        description="处理摘要信息"
    )

    operation_log: List[str] = Field(
        default_factory=list,
        description="操作日志"
    )

    total_processing_time_ms: int = Field(..., description="总处理时间（毫秒）")


class BQAExtractionStats(BaseModel):
    """BQA提取统计信息"""

    sessions_with_context: int = Field(default=0, description="需要上下文的会话数")
    sessions_independent: int = Field(default=0, description="独立会话数")
    avg_context_dependency_ratio: float = Field(default=0.0, description="平均上下文依赖比例")
    common_context_patterns: List[str] = Field(default_factory=list, description="常见上下文模式")

    def add_session_stats(self, has_context: bool, dependency_ratio: float):
        """添加会话统计"""
        if has_context:
            self.sessions_with_context += 1
        else:
            self.sessions_independent += 1

        # 更新平均依赖比例
        total_sessions = self.sessions_with_context + self.sessions_independent
        current_avg = self.avg_context_dependency_ratio
        self.avg_context_dependency_ratio = (
            (current_avg * (total_sessions - 1) + dependency_ratio) / total_sessions
        )