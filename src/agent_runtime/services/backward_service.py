import asyncio
from typing import List, Tuple, Optional

from agent_runtime.data_format.ospa import OSPA
from agent_runtime.data_format.qa_format import QAList
from agent_runtime.data_format.chapter_format import ChapterStructure
from agent_runtime.clients.openai_llm_client import LLM
from agent_runtime.data_format.context import AIContext
from agent_runtime.logging.logger import logger
from agent_runtime.agents.chapter_structure_agent import ChapterStructureAgent
from agent_runtime.agents.chapter_classification_agent import (
    ChapterClassificationAgent,
)
from agent_runtime.agents.gen_chpt_p_agent import GenChptPAgent


class BackwardService:
    """反向知识处理服务
    
    该服务负责将问答对(Q&A)处理成章节结构，并为每个章节生成
    辅助提示词，用于指导后续的问答生成和知识检索。
    
    主要功能：
    1. 创建或更新章节结构
    2. 为章节生成专用的辅助提示词
    3. 生成OSPA格式的输出
    
    Attributes:
        llm_client (LLM): 大语言模型客户端，用于执行各种任务
        chapter_structure_agent (ChapterStructureAgent): 章节结构创建Agent
        chapter_classification_agent (ChapterClassificationAgent): 章节分类Agent
        gen_chpt_p_agent (GenChptPAgent): 章节提示词生成Agent
    """

    def __init__(self, llm_client: Optional[LLM] = None) -> None:
        """初始化反向知识处理服务
        
        Args:
            llm_client (LLM): 大语言模型客户端实例
        """
        self.llm_client = llm_client or LLM()
        
        # 初始化全局上下文
        self.global_context = AIContext()
        
        # 初始化专用的Agent实例
        self.chapter_structure_agent = ChapterStructureAgent(
            llm_engine=self.llm_client
        )
        self.chapter_classification_agent = ChapterClassificationAgent(
            llm_engine=self.llm_client
        )
        self.gen_chpt_p_agent = GenChptPAgent(llm_engine=self.llm_client)

        logger.info("BackwardService initialized with global context and agents")

    def get_global_context(self) -> AIContext:
        """获取全局上下文"""
        return self.global_context
    
    def update_global_context(self, context: AIContext) -> None:
        """更新全局上下文"""
        self.global_context = context
        logger.info("Global context updated for BackwardService")

    async def backward(
        self,
        qa_list: QAList,
        chapter_structure: Optional[ChapterStructure] = None,
        max_level: int = 3,
        max_concurrent_llm: int = 3,
    ) -> Tuple[ChapterStructure, List[OSPA]]:
        """处理QA列表，生成或更新章节结构并创建OSPA
        
        Args:
            qa_list: QA对话列表
            chapter_structure: 可选的现有章节结构
            max_level: 最大层级深度
            max_concurrent_llm: 最大并发LLM调用数量
            
        Returns:
            元组：(章节结构, OSPA列表)
        """
        logger.info(f"开始处理QA列表，包含 {len(qa_list.items)} 个问答对")
        
        # 记录现有章节ID以识别新增章节
        existing_node_ids = (
            set(chapter_structure.nodes.keys()) if chapter_structure else set()
        )
        
        if chapter_structure is None:
            # 创建新章节结构
            logger.info("使用chapter_structure_agent创建新章节结构")
            final_structure = await self.chapter_structure_agent.build_structure(
                qa_list=qa_list,
                max_level=max_level,
                context=self.global_context
            )
            # 所有章节都是新的
            new_chapter_ids = set(final_structure.nodes.keys())
        else:
            # 更新现有章节结构
            logger.info("使用chapter_classification_agent更新现有章节结构")
            _, final_structure = (
                await self.chapter_classification_agent.classify_content(
                    qa_list=qa_list,
                    chapter_structure=chapter_structure,
                    max_level=max_level,
                    # context=self.global_context
                )
            )
            # 识别新增章节
            current_node_ids = set(final_structure.nodes.keys())
            new_chapter_ids = current_node_ids - existing_node_ids
            
        logger.info(
            f"章节结构处理完成，共 {len(final_structure.nodes)} 个章节，"
            f"其中 {len(new_chapter_ids)} 个为新增"
        )
        
        # 生成章节提示词
        await self._generate_chapter_prompts(
            final_structure, new_chapter_ids, max_concurrent_llm
        )
        
        # 生成OSPA
        ospa_list = self._generate_ospa_from_structure(final_structure)
        
        logger.info(f"处理完成，生成了 {len(ospa_list)} 个OSPA条目")
        return final_structure, ospa_list
    
    async def _generate_chapter_prompts(
        self,
        chapter_structure: ChapterStructure,
        new_chapter_ids: set,
        max_concurrent_llm: int = 3,
    ) -> None:
        """为章节生成提示词
        
        Args:
            chapter_structure: 章节结构
            new_chapter_ids: 新创建的章节ID集合
            max_concurrent_llm: 最大并发LLM调用数量
        """
        # 收集需要生成提示词的章节
        nodes_to_generate = []
        
        for node in chapter_structure.nodes.values():
            if not node.related_qa_items:
                continue
                
            # 确定是否需要生成新的提示词
            need_generate_prompt = (
                node.id in new_chapter_ids  # 是新创建的章节
                or not node.content  # 章节没有现有内容
            )
            
            if need_generate_prompt:
                nodes_to_generate.append(node)
        
        # 异步并发生成需要生成提示词的章节
        if nodes_to_generate:
            logger.info(
                f"开始并发生成 {len(nodes_to_generate)} 个章节的提示词，"
                f"最大并发数: {max_concurrent_llm}"
            )
            
            # 创建信号量控制并发数
            semaphore = asyncio.Semaphore(max_concurrent_llm)
            
            async def generate_single_chapter_prompt(node):
                """为单个章节生成提示词"""
                async with semaphore:
                    logger.debug(f"为章节 '{node.title}' 生成提示词")
                    
                    # 准备章节相关的Q&A数据
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
                                reason=(
                                    node.description 
                                    or f"关于{node.title}的相关内容"
                                ),
                                # context=self.global_context,
                            )
                        )
                        logger.debug(f"章节 '{node.title}' 提示词生成成功")
                        return node, chapter_prompt
                    except Exception as e:
                        logger.error(
                            f"为章节 '{node.title}' 生成提示词失败: {e}"
                        )
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
                logger.debug(
                    f"已将提示词保存到章节 '{node.title}' (ID: {node.id})"
                )
    
    def _generate_ospa_from_structure(
        self, chapter_structure: ChapterStructure
    ) -> List[OSPA]:
        """从章节结构生成OSPA列表
        
        Args:
            chapter_structure: 章节结构
            
        Returns:
            OSPA列表
        """
        ospa_list = []
        
        for node in chapter_structure.nodes.values():
            if not node.related_qa_items:
                continue
                
            chapter_prompt = (
                node.content or f"请基于{node.title}章节的知识回答问题。"
            )
            
            # 为每个QA创建OSPA
            for qa_item in node.related_qa_items:
                ospa = OSPA(
                    o=qa_item.question,  # Objective: 问题
                    s=f"{node.title}",  # Scenario: 章节名称作为场景
                    p=chapter_prompt,  # Prompt: 章节提示词
                    a=qa_item.answer,  # Answer: 答案
                )
                ospa_list.append(ospa)
        
        return ospa_list
