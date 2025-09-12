from typing import List, Optional, Dict, Any
import asyncio

from agent_runtime.clients.openai_llm_client import LLM
from agent_runtime.agents.cqa_agent import CQAAgent
from agent_runtime.agents.chapter_structure_agent import ChapterStructureAgent
from agent_runtime.agents.chapter_classification_agent import ChapterClassificationAgent
from agent_runtime.agents.gen_chpt_p_agent import GenChptPAgent
from agent_runtime.data_format.qa_format import QAList, CQAList
from agent_runtime.data_format.chapter_format import ChapterStructure, ChapterNode
from agent_runtime.data_format.ospa import OSPA
from agent_runtime.data_format.backward_v2_format import (
    BackwardV2Request,
    BackwardV2Response,
)
from agent_runtime.logging.logger import logger


class BackwardV2Service:
    """
    Backward V2 服务类
    利用 cqa_agent、chapter_structure_agent、chapter_classification_agent 和 gen_chpt_p_agent
    处理 Q&A 二维列表，生成章节目录和 OSPA
    """

    def __init__(self, llm_client: LLM = None):
        """初始化服务"""
        self.llm_client = llm_client or LLM()
        
        # 初始化全局上下文
        from agent_runtime.data_format.context import AIContext
        self.global_context = AIContext()
        self.global_context.add_system_prompt("你是一个专业的知识结构化处理助手，负责将问答内容转换为结构化的章节和OSPA格式。")

        # 初始化各个 agent
        self.cqa_agent = CQAAgent(llm_engine=self.llm_client)
        self.chapter_structure_agent = ChapterStructureAgent(llm_engine=self.llm_client)
        self.chapter_classification_agent = ChapterClassificationAgent(
            llm_engine=self.llm_client
        )
        self.gen_chpt_p_agent = GenChptPAgent(llm_engine=self.llm_client)

        logger.info("BackwardV2Service 初始化完成")

    def get_global_context(self):
        """获取全局上下文"""
        return self.global_context
    
    def update_global_context(self, context) -> None:
        """更新全局上下文"""
        self.global_context = context
        logger.info("Global context updated for BackwardV2Service")

    async def process(self, request: BackwardV2Request) -> BackwardV2Response:
        """
        处理 Backward V2 请求的主要方法

        Args:
            request: 包含 Q&A 二维列表和可选章节目录的请求

        Returns:
            包含最终章节目录和 OSPA 的响应
        """
        operation_log = []

        # 第一步：使用 cqa_agent 将 Q&A 转换为 CQA（异步并发处理）
        logger.info(
            f"步骤1: 将 {len(request.qa_lists)} 个 QA 列表转换为 CQA 列表（并发处理）"
        )

        # 创建并发任务
        async def transform_single_qa_list(i: int, qa_list: QAList) -> CQAList:
            logger.debug(f"开始处理第 {i+1} 个 QA 列表")
            cqa_list = await self.cqa_agent.transform_qa_to_cqa(qa_list, context=self.global_context)
            logger.debug(
                f"第 {i+1} 个 QA 列表转换完成，包含 {len(cqa_list.items)} 个 CQA"
            )
            return cqa_list

        # 并发执行所有转换任务
        tasks = [
            transform_single_qa_list(i, qa_list)
            for i, qa_list in enumerate(request.qa_lists)
        ]
        cqa_lists = await asyncio.gather(*tasks)

        operation_log.append(
            f"完成 Q&A 到 CQA 的并发转换，共 {len(cqa_lists)} 个对话序列"
        )

        # 第二步：根据是否有章节目录选择不同处理路径
        new_chapter_ids = set()  # 记录新创建的章节ID

        if request.chapter_structure is None:
            # 没有章节目录：使用 chapter_structure_agent 生成新的章节目录
            logger.info("步骤2: 使用 chapter_structure_agent 生成新的章节目录")
            # 需要将QA列表合并为单个QAList来构建章节结构
            from agent_runtime.data_format.qa_format import QAList, QAItem
            merged_qa_list = QAList(session_id="merged")
            for qa_list in request.qa_lists:
                for qa_item in qa_list.items:
                    merged_qa_list.add_qa(qa_item.question, qa_item.answer, qa_item.metadata)
            
            chapter_structure = await self.chapter_structure_agent.build_structure(
                qa_list=merged_qa_list, max_level=request.max_level, context=self.global_context
            )
            # 所有章节都是新的
            new_chapter_ids = set(chapter_structure.nodes.keys())
            operation_log.append(
                f"生成新章节目录，包含 {len(chapter_structure.nodes)} 个章节"
            )
        else:
            # 有章节目录：使用 chapter_classification_agent 更新现有章节目录
            logger.info("步骤2: 使用 chapter_classification_agent 更新现有章节目录")
            existing_node_ids = set(request.chapter_structure.nodes.keys())

            # 合并所有QA列表为单个QAList进行分类
            from agent_runtime.data_format.qa_format import QAList
            merged_qa_list = QAList(session_id="merged_for_classification")
            for qa_list in request.qa_lists:
                for qa_item in qa_list.items:
                    merged_qa_list.add_qa(qa_item.question, qa_item.answer, qa_item.metadata)
            
            classification_results, chapter_structure = (
                await self.chapter_classification_agent.classify_content(
                    qa_list=merged_qa_list,
                    chapter_structure=request.chapter_structure,
                    max_level=request.max_level,
                    context=self.global_context,
                )
            )

            # 记录新创建的章节
            current_node_ids = set(chapter_structure.nodes.keys())
            new_chapter_ids = current_node_ids - existing_node_ids

            operation_log.append(
                f"更新章节目录，分类了 {len(classification_results)} 个内容项，新增 {len(new_chapter_ids)} 个章节"
            )

        # 第三步：使用 gen_chpt_p_agent 生成章节提示词和 OSPA
        logger.info("步骤3: 使用 gen_chpt_p_agent 生成章节提示词和 OSPA")
        ospa_list = await self._generate_ospa(
            chapter_structure,
            cqa_lists,
            new_chapter_ids,
            max_concurrent_llm=request.max_concurrent_llm,
        )
        operation_log.append(f"生成 OSPA 完成，共 {len(ospa_list)} 个条目")

        logger.info(
            f"BackwardV2 处理完成，生成了 {len(chapter_structure.nodes)} 个章节和 {len(ospa_list)} 个 OSPA"
        )

        return BackwardV2Response(
            chapter_structure=chapter_structure,
            ospa_list=ospa_list,
            operation_log=operation_log,
        )

    async def _generate_ospa(
        self,
        chapter_structure: ChapterStructure,
        cqa_lists: List[CQAList],
        new_chapter_ids: Optional[set] = None,
        max_concurrent_llm: int = 3,
    ) -> List[OSPA]:
        """
        为章节结构生成 OSPA

        Args:
            chapter_structure: 章节结构
            cqa_lists: CQA 列表
            new_chapter_ids: 新创建的章节ID集合，如果提供则只为这些章节生成提示词
            max_concurrent_llm: 最大并发生成提示词数量，默认为3

        Returns:
            OSPA 列表
        """
        ospa_list = []

        # 收集需要生成提示词的章节和已有提示词的章节
        nodes_to_generate = []  # 需要生成提示词的章节
        nodes_with_existing_prompts = []  # 已有提示词的章节

        for node in chapter_structure.nodes.values():
            if not node.related_qa_items:
                continue

            # 确定是否需要生成新的提示词
            need_generate_prompt = (
                new_chapter_ids is None  # 没有指定新章节集合，为所有章节生成
                or node.id in new_chapter_ids  # 是新创建的章节
                or not node.content  # 章节没有现有内容
            )

            if need_generate_prompt:
                nodes_to_generate.append(node)
            else:
                nodes_with_existing_prompts.append(node)

        # 异步并发生成需要生成提示词的章节
        if nodes_to_generate:
            logger.info(
                f"开始并发生成 {len(nodes_to_generate)} 个章节的提示词，最大并发数: {max_concurrent_llm}"
            )

            # 创建信号量控制并发数
            semaphore = asyncio.Semaphore(max_concurrent_llm)

            async def generate_single_chapter_prompt(
                node: ChapterNode,
            ) -> tuple[ChapterNode, str]:
                """为单个章节生成提示词"""
                async with semaphore:
                    logger.debug(f"为章节 '{node.title}' 生成提示词（新章节或无内容）")

                    # 准备章节相关的 Q&A 数据
                    chapter_qas = []
                    for qa_item in node.related_qa_items:
                        qa_dict = {
                            "question": qa_item.question,
                            "answer": qa_item.answer,
                        }
                        chapter_qas.append(qa_dict)

                    try:
                        chapter_prompt = (
                            await self.gen_chpt_p_agent.generate_chapter_prompt(
                                chapter_name=node.title,
                                qas=chapter_qas,
                                reason=node.description
                                or f"关于{node.title}的相关内容",
                                context=self.global_context,
                            )
                        )
                        logger.debug(f"章节 '{node.title}' 提示词生成成功")
                        return node, chapter_prompt
                    except Exception as e:
                        logger.error(f"为章节 '{node.title}' 生成提示词失败: {e}")
                        # 使用默认提示词
                        default_prompt = f"请基于{node.title}章节的知识回答问题。"
                        return node, default_prompt

            # 并发执行所有提示词生成任务
            prompt_generation_tasks = [
                generate_single_chapter_prompt(node) for node in nodes_to_generate
            ]

            generated_results = await asyncio.gather(*prompt_generation_tasks)

            # 将生成的提示词保存到章节节点中
            for node, chapter_prompt in generated_results:
                chapter_structure.set_node_content(node.id, chapter_prompt)
                logger.debug(f"已将提示词保存到章节 '{node.title}' (ID: {node.id})")

                # 为每个 QA 创建 OSPA
                for qa_item in node.related_qa_items:
                    ospa = OSPA(
                        o=qa_item.question,  # Objective: 问题
                        s=f"{node.title}",  # Scenario: 章节名称作为场景
                        p=chapter_prompt,  # Prompt: 生成的章节提示词
                        a=qa_item.answer,  # Answer: 答案
                    )
                    ospa_list.append(ospa)

        # 处理已有提示词的章节
        for node in nodes_with_existing_prompts:
            chapter_prompt: str = node.content or ""
            logger.debug(f"章节 '{node.title}' 使用现有提示词")

            if not chapter_prompt:
                chapter_prompt = f"请基于{node.title}章节的知识回答问题。"
                chapter_structure.set_node_content(node.id, chapter_prompt)

            # 为每个 QA 创建 OSPA
            for qa_item in node.related_qa_items:
                ospa = OSPA(
                    o=qa_item.question,  # Objective: 问题
                    s=f"{node.title}",  # Scenario: 章节名称作为场景
                    p=chapter_prompt,  # Prompt: 现有的章节提示词
                    a=qa_item.answer,  # Answer: 答案
                )
                ospa_list.append(ospa)

        return ospa_list
