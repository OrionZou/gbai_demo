import json
import uuid
import re
from typing import Dict, Any, Optional

from agent_runtime.agents.base import BaseAgent
from agent_runtime.agents.chapter_mixin import ChapterAgentMixin
from agent_runtime.data_format.context import AIContext
from agent_runtime.data_format.qa_format import QAList, QAItem
from agent_runtime.data_format.chapter_format import ChapterStructure, ChapterNode
from agent_runtime.logging.logger import logger


class ChapterStructureAgent(BaseAgent, ChapterAgentMixin):
    """
    章节结构构建Agent
    基于BaseAgent开发，专门负责构建章节目录结构
    """

    DEFAULT_AGENT_NAME = "chapter_structure_agent"

    DEFAULT_SYSTEM_PROMPT = """你是一个专业的内容结构组织专家，负责基于对话内容构建合理的章节目录结构。

你的任务：
- 分析每个Q & A 问答对的主题和内容结构
- 构建层次清晰的章节结构，层数不超过指定最大层数
- 每个章节包含合理的标题和简短描述
- 为每个章节分配唯一ID
- 为每个Q & A 问答对，关联最相关的章节


组织原则：
- 章节结构要逻辑清晰，层次分明
- 同级章节内容相互独立但逻辑相关
- 章节标题简洁明确，准确概括内容,章节标题命名应该具有显著特点，避免通用含义词汇
- 避免过度细分，保持合理粒度，每个章节的内容分布相对均匀
- 严格控制层级深度不超过指定最大层数"""

    BUILD_STRUCTURE_TEMPLATE = """基于以下问答对话内容，构建一个不超过{{max_level}}层的章节目录结构：

问答对话内容：
{% for qa in qa_list.items %}
{{ loop.index }}. Q: {{ qa.question }}
   A: {{ qa.answer }}
{% endfor %}

要求：
1. 分析问答对话的主要主题和子主题
2. 构建层次清晰的章节结构（最大{{max_level}}层）
3. 每个章节包含合理的标题和简短描述
4. 为每个章节分配唯一ID
5. 为每个章节指定相关的问答对索引

请按以下JSON格式返回章节结构：
{
  "chapters": [
    {
      "id": "chapter_1",
      "title": "章节标题",
      "level": 1,
      "parent_id": null,
      "description": "章节描述",
      "related_qa_indices": [1, 2, 3]
    }
  ]
}"""

    def __init__(self, **kwargs):
        super().__init__(
            system_prompt=self.DEFAULT_SYSTEM_PROMPT,
            user_prompt_template=self.BUILD_STRUCTURE_TEMPLATE,
            **kwargs,
        )

    async def step(self, context: AIContext = None, **kwargs) -> Any:
        """执行一步Agent推理"""
        if context is None:
            working_context = AIContext()
        else:
            working_context = context
        working_context.add_system_prompt(self.system_prompt)
        user_prompt = self._render_user_prompt(**kwargs)
        working_context.add_user_prompt(user_prompt)
        input_token = working_context.get_current_tokens()
        logger.info(f"context input get_current_tokens:{input_token}")
        response = await self.llm_engine.ask(working_context.to_openai_format())

        working_context.add_assistant(response)
        logger.info(
            f"context output get_current_tokens:{working_context.get_current_tokens()-input_token}"
        )
        return response

    async def build_structure(
        self, qa_list: QAList, max_level: int = 3, context: Optional[AIContext] = None
    ) -> ChapterStructure:
        """
        构建章节结构

        Args:
            qa_list: QA对话列表
            max_level: 最大目录层数
            context: AI上下文，如果为None则在step中创建

        Returns:
            构建的章节结构
        """
        try:
            logger.info(f"qa_list items len:{len(qa_list.items)}")
            response = await self.step(context=context, max_level=max_level, qa_list=qa_list)

            structure_data = self._parse_structure_response(response)
            chapter_structure = self._build_chapter_structure_from_qa_list(
                structure_data, max_level, qa_list
            )

            logger.info(f"成功构建章节结构，共{len(chapter_structure.nodes)}个章节")
            return chapter_structure

        except Exception as e:
            logger.error(f"构建章节结构失败: {e}")
            return self._create_default_structure(max_level)

    def _parse_structure_response(self, response: str) -> Dict[str, Any]:
        """解析结构构建响应"""
        result = self._parse_json_response(response)
        return result if result else {"chapters": []}

    def _build_chapter_structure_from_qa_list(
        self,
        structure_data: Dict[str, Any],
        max_level: int,
        qa_list: QAList,
    ) -> ChapterStructure:
        """从数据构建章节结构"""
        structure = ChapterStructure(max_level=max_level)

        chapters = structure_data.get("chapters", [])
        if not chapters:
            logger.warning("LLM返回空的章节结构，使用默认结构")
            return self._create_default_structure(max_level)

        for chapter_data in chapters:
            node = ChapterNode(
                id=chapter_data.get("id", str(uuid.uuid4())),
                title=chapter_data.get("title", "未命名章节"),
                level=1,  # 临时值，add_node会自动计算正确的level
                parent_id=chapter_data.get("parent_id"),
                description=chapter_data.get("description", ""),
            )
            structure.add_node(node)
            
            # 关联QA案例到章节
            related_indices = chapter_data.get("related_qa_indices", [])
            self._associate_qa_to_chapter(node, related_indices, qa_list)

        return structure

    def _associate_qa_to_chapter(self, node: ChapterNode, related_indices: list, qa_list: QAList) -> None:
        """将QA案例关联到章节节点"""
        for qa_index in related_indices:
            if 1 <= qa_index <= len(qa_list.items):
                qa_item = qa_list.items[qa_index - 1]  # 转换为0-based索引
                # 将QA转换为CQA格式添加到节点
                cqa_item = QAItem(
                    question=qa_item.question,
                    answer=qa_item.answer,
                    metadata=qa_item.metadata
                )
                node.add_qa_item(cqa_item)

    def _create_default_structure(self, max_level: int) -> ChapterStructure:
        """创建默认章节结构"""
        structure = ChapterStructure(max_level=max_level)

        default_node = ChapterNode(
            id="default_chapter",
            title="通用内容",
            level=1,  # 临时值，add_node会自动计算正确的level
            description="未分类的对话内容",
        )
        structure.add_node(default_node)

        logger.info("使用默认章节结构")
        return structure

