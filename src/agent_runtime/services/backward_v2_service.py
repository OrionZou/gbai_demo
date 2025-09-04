from typing import List, Optional, Dict, Any

from agent_runtime.clients.llm.openai_client import LLM
from agent_runtime.agents.cqa_agent import CQAAgent
from agent_runtime.agents.chapter_structure_agent import ChapterStructureAgent
from agent_runtime.agents.chapter_classification_agent import ChapterClassificationAgent
from agent_runtime.agents.gen_chpt_p_agent import GenChptPAgent
from agent_runtime.data_format.qa_format import QAList, CQAList
from agent_runtime.data_format.chapter_format import ChapterStructure, ChapterNode
from agent_runtime.data_format.ospa import OSPA
from agent_runtime.data_format.backward_v2_format import BackwardV2Request, BackwardV2Response
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
        
        # 初始化各个 agent
        self.cqa_agent = CQAAgent(llm_engine=self.llm_client)
        self.chapter_structure_agent = ChapterStructureAgent(llm_engine=self.llm_client)  
        self.chapter_classification_agent = ChapterClassificationAgent(llm_engine=self.llm_client)
        self.gen_chpt_p_agent = GenChptPAgent(llm_engine=self.llm_client)
        
        logger.info("BackwardV2Service 初始化完成")
    
    async def process(self, request: BackwardV2Request) -> BackwardV2Response:
        """
        处理 Backward V2 请求的主要方法
        
        Args:
            request: 包含 Q&A 二维列表和可选章节目录的请求
            
        Returns:
            包含最终章节目录和 OSPA 的响应
        """
        operation_log = []
        
        # 第一步：使用 cqa_agent 将 Q&A 转换为 CQA
        logger.info(f"步骤1: 将 {len(request.qa_lists)} 个 QA 列表转换为 CQA 列表")
        cqa_lists = []
        for i, qa_list in enumerate(request.qa_lists):
            cqa_list = await self.cqa_agent.transform_qa_to_cqa(qa_list)
            cqa_lists.append(cqa_list)
            logger.debug(f"第 {i+1} 个 QA 列表转换完成，包含 {len(cqa_list.items)} 个 CQA")
        
        operation_log.append(f"完成 Q&A 到 CQA 的转换，共 {len(cqa_lists)} 个对话序列")
        
        # 第二步：根据是否有章节目录选择不同处理路径
        if request.chapter_structure is None:
            # 没有章节目录：使用 chapter_structure_agent 生成新的章节目录
            logger.info("步骤2: 使用 chapter_structure_agent 生成新的章节目录")
            chapter_structure = await self.chapter_structure_agent.build_structure(
                cqa_lists=cqa_lists, 
                max_level=request.max_level
            )
            operation_log.append(f"生成新章节目录，包含 {len(chapter_structure.nodes)} 个章节")
        else:
            # 有章节目录：使用 chapter_classification_agent 更新现有章节目录
            logger.info("步骤2: 使用 chapter_classification_agent 更新现有章节目录")
            classification_results, chapter_structure = await self.chapter_classification_agent.classify_content(
                cqa_lists=cqa_lists,
                chapter_structure=request.chapter_structure,
                max_level=request.max_level
            )
            operation_log.append(f"更新章节目录，分类了 {len(classification_results)} 个内容项")
        
        # 第三步：使用 gen_chpt_p_agent 生成章节提示词和 OSPA
        logger.info("步骤3: 使用 gen_chpt_p_agent 生成章节提示词和 OSPA")
        ospa_list = await self._generate_ospa(chapter_structure, cqa_lists)
        operation_log.append(f"生成 OSPA 完成，共 {len(ospa_list)} 个条目")
        
        logger.info(f"BackwardV2 处理完成，生成了 {len(chapter_structure.nodes)} 个章节和 {len(ospa_list)} 个 OSPA")
        
        return BackwardV2Response(
            chapter_structure=chapter_structure,
            ospa_list=ospa_list,
            operation_log=operation_log
        )
    
    async def _generate_ospa(self, chapter_structure: ChapterStructure, cqa_lists: List[CQAList]) -> List[OSPA]:
        """
        为章节结构生成 OSPA
        
        Args:
            chapter_structure: 章节结构
            cqa_lists: CQA 列表
            
        Returns:
            OSPA 列表
        """
        ospa_list = []
        
        # 遍历每个章节节点
        for node in chapter_structure.nodes.values():
            if not node.related_cqa_items:
                continue
                
            # 为每个章节生成专用提示词
            logger.debug(f"为章节 '{node.title}' 生成提示词")
            
            # 准备章节相关的 Q&A 数据
            chapter_qas = []
            for cqa_item in node.related_cqa_items:
                qa_dict = {
                    "question": cqa_item.question,
                    "answer": cqa_item.answer,
                    "context": cqa_item.context
                }
                chapter_qas.append(qa_dict)
            
            # 使用 gen_chpt_p_agent 生成章节提示词
            try:
                chapter_prompt = await self.gen_chpt_p_agent.generate_chapter_prompt(
                    chapter_name=node.title,
                    qas=chapter_qas,
                    reason=node.description or f"关于{node.title}的相关内容"
                )
                
                # 为每个 CQA 创建 OSPA
                for cqa_item in node.related_cqa_items:
                    ospa = OSPA(
                        o=cqa_item.question,  # Objective: 问题
                        s=f"{node.title}",    # Scenario: 章节名称作为场景
                        p=chapter_prompt,     # Prompt: 生成的章节提示词
                        a=cqa_item.answer     # Answer: 答案
                    )
                    ospa_list.append(ospa)
                    
            except Exception as e:
                logger.error(f"为章节 '{node.title}' 生成提示词失败: {e}")
                # 使用默认提示词
                default_prompt = f"请基于{node.title}章节的知识回答问题。"
                for cqa_item in node.related_cqa_items:
                    ospa = OSPA(
                        o=cqa_item.question,
                        s=f"{node.title}",
                        p=default_prompt,
                        a=cqa_item.answer
                    )
                    ospa_list.append(ospa)
        
        return ospa_list