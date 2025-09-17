"""
BQA拆解服务

这个服务专门用于将多轮对话拆解为独立的BQA内容。
利用BQAAgent来为每个问答对添加必要的背景信息，使其可以独立理解。
"""

import time
import asyncio
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from agent_runtime.clients.openai_llm_client import LLM
from agent_runtime.agents.bqa_agent import BQAAgent
from agent_runtime.data_format.qa_format import QAList, BQAList
from agent_runtime.interface.api_models import (
    BQAExtractRequest,
    BQAExtractResponse,
    BQAExtractSessionResult,
)
from agent_runtime.data_format.context import AIContext
from agent_runtime.logging.logger import logger


class BQAExtractionStats(BaseModel):
    """BQA提取统计信息"""

    sessions_with_context: int = Field(default=0, description="需要上下文的会话数")
    sessions_independent: int = Field(default=0, description="独立会话数")
    avg_context_dependency_ratio: float = Field(
        default=0.0, description="平均上下文依赖比例"
    )
    common_context_patterns: List[str] = Field(
        default_factory=list, description="常见上下文模式"
    )

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
            current_avg * (total_sessions - 1) + dependency_ratio
        ) / total_sessions


class BQAExtractService:
    """
    BQA拆解服务

    将多轮对话转换为独立的BQA格式，每个BQA包含必要的背景信息，
    使得问答对可以独立理解和使用。
    """

    def __init__(self, llm_client: LLM = None):
        """初始化BQA拆解服务"""
        self.llm_client = llm_client or LLM()

        # 初始化BQA Agent
        self.bqa_agent = BQAAgent(llm_engine=self.llm_client)

        # 初始化全局上下文
        self.global_context = AIContext()
        self.global_context.add_system_prompt(
            "你是一个专业的对话分析师，负责将多轮对话拆解为独立的背景-问题-答案格式，"
            "确保每个拆解后的内容都可以独立理解。"
        )

        logger.info("BQAExtractService 初始化完成")

    async def extract_bqa_from_conversations(
        self, request: BQAExtractRequest
    ) -> BQAExtractResponse:
        """
        从多轮对话中提取独立的BQA内容

        Args:
            request: BQA拆解请求

        Returns:
            BQAExtractResponse: 包含拆解结果的响应
        """
        start_time = time.time()
        operation_log = []
        session_results = []
        stats = BQAExtractionStats()

        logger.info(f"开始处理 {len(request.qa_lists)} 个对话会话")
        operation_log.append(f"开始处理 {len(request.qa_lists)} 个对话会话")

        # 根据模式调整BQA Agent的行为
        self._configure_agent_for_mode(request.context_extraction_mode)

        # 创建并发任务
        async def extract_single_session(
            i: int, qa_list: QAList
        ) -> BQAExtractSessionResult:
            session_start_time = time.time()
            logger.debug(f"开始处理第 {i+1} 个对话会话: {qa_list.session_id}")

            try:
                # 使用BQA Agent转换对话
                bqa_list = await self.bqa_agent.transform_qa_to_bqa(
                    qa_list, context=self.global_context
                )

                # 计算处理时间
                processing_time = int((time.time() - session_start_time) * 1000)

                # 分析会话特征
                dependency_ratio = self._analyze_context_dependency(qa_list, bqa_list)
                has_context = dependency_ratio > 0.1
                stats.add_session_stats(has_context, dependency_ratio)

                # 生成提取摘要
                extraction_summary = self._generate_extraction_summary(
                    qa_list, bqa_list, request.context_extraction_mode
                )

                result = BQAExtractSessionResult(
                    session_id=qa_list.session_id or f"session_{i+1}",
                    original_qa_count=len(qa_list.items),
                    extracted_bqa_count=len(bqa_list.items),
                    bqa_list=bqa_list,
                    processing_time_ms=processing_time,
                    extraction_summary=extraction_summary,
                )

                logger.debug(
                    f"第 {i+1} 个会话处理完成: "
                    f"{len(qa_list.items)} QA -> {len(bqa_list.items)} BQA"
                )

                return result

            except Exception as e:
                logger.error(f"处理第 {i+1} 个会话失败: {e}")
                # 创建错误结果
                return BQAExtractSessionResult(
                    session_id=qa_list.session_id or f"session_{i+1}",
                    original_qa_count=len(qa_list.items),
                    extracted_bqa_count=0,
                    bqa_list=BQAList(session_id=qa_list.session_id),
                    processing_time_ms=int((time.time() - session_start_time) * 1000),
                    extraction_summary=f"处理失败: {str(e)}",
                )

        # 执行并发处理
        semaphore = asyncio.Semaphore(request.max_concurrent_processing)

        async def process_with_semaphore(i: int, qa_list: QAList):
            async with semaphore:
                return await extract_single_session(i, qa_list)

        tasks = [
            process_with_semaphore(i, qa_list)
            for i, qa_list in enumerate(request.qa_lists)
        ]

        session_results = await asyncio.gather(*tasks)

        # 计算总体统计
        total_original_qas = sum(result.original_qa_count for result in session_results)
        total_extracted_bqas = sum(
            result.extracted_bqa_count for result in session_results
        )
        total_processing_time = int((time.time() - start_time) * 1000)

        operation_log.append(
            f"完成所有会话处理，总计: {total_original_qas} QA -> {total_extracted_bqas} BQA"
        )
        operation_log.append(
            f"平均上下文依赖比例: {stats.avg_context_dependency_ratio:.2%}"
        )

        # 构建处理摘要
        processing_summary = {
            "mode": request.context_extraction_mode,
            "concurrent_limit": request.max_concurrent_processing,
            "success_rate": len(
                [r for r in session_results if r.extracted_bqa_count > 0]
            )
            / len(session_results),
            "stats": {
                "sessions_with_context": stats.sessions_with_context,
                "sessions_independent": stats.sessions_independent,
                "avg_dependency_ratio": stats.avg_context_dependency_ratio,
            },
        }

        return BQAExtractResponse(
            session_results=session_results,
            total_sessions=len(request.qa_lists),
            total_original_qas=total_original_qas,
            total_extracted_bqas=total_extracted_bqas,
            processing_summary=processing_summary,
            operation_log=operation_log,
            total_processing_time_ms=total_processing_time,
        )

    def _configure_agent_for_mode(self, mode: str) -> None:
        """根据模式配置BQA Agent的行为"""
        if mode == "minimal":
            # 最小化模式：只在必要时添加背景
            self.global_context.add_user_prompt(
                "请采用最小化模式处理，只在问题明确依赖前面内容时才添加背景信息。"
                "对于可以独立理解的问题，背景字段应为空。"
            )
        elif mode == "detailed":
            # 详细模式：为大部分问题添加丰富的背景
            self.global_context.add_user_prompt(
                "请采用详细模式处理，为每个问题尽可能提供丰富的背景信息，"
                "包括对话主题、前面提到的关键概念等，确保独立理解。"
            )
        else:  # auto模式
            # 自动模式：智能判断是否需要背景
            self.global_context.add_user_prompt(
                "请智能判断每个问题是否需要背景信息。如果问题可以独立理解，"
                "背景可以为空；如果依赖前面的内容，请提供必要的背景信息。"
            )

    def _analyze_context_dependency(self, qa_list: QAList, bqa_list: BQAList) -> float:
        """分析对话的上下文依赖程度"""
        if not bqa_list.items:
            return 0.0

        # 计算有背景信息的BQA比例
        with_background_count = sum(
            1 for bqa in bqa_list.items if bqa.background and bqa.background.strip()
        )

        return with_background_count / len(bqa_list.items)

    def _generate_extraction_summary(
        self, qa_list: QAList, bqa_list: BQAList, mode: str
    ) -> str:
        """生成提取摘要"""
        if not bqa_list.items:
            return "提取失败或无内容"

        with_background = sum(
            1 for bqa in bqa_list.items if bqa.background and bqa.background.strip()
        )

        summary_parts = [
            f"模式: {mode}",
            f"转换: {len(qa_list.items)} QA -> {len(bqa_list.items)} BQA",
            f"带背景: {with_background}/{len(bqa_list.items)} ({with_background/len(bqa_list.items):.1%})",
        ]

        return " | ".join(summary_parts)

    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            "service_name": "BQAExtractService",
            "llm_model": getattr(self.llm_client, "model", "unknown"),
            "bqa_agent_status": {
                "agent_name": self.bqa_agent.agent_name,
                "initialized": True,
            },
        }
