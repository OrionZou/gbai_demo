import uuid
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

from agent_runtime.agents.base import BaseAgent
from agent_runtime.agents.chapter_mixin import ChapterAgentMixin
from agent_runtime.data_format.context import AIContext
from agent_runtime.data_format.qa_format import QAList, QAItem
from agent_runtime.data_format.chapter_format import ChapterStructure, ChapterNode
from agent_runtime.logging.logger import logger


class ChapterClassificationResult(BaseModel):
    """章节分类结果"""

    index: str = Field(..., description="待归类内容的索引编号")
    target_chapter_id: str = Field(..., description="目标章节的ID")
    confidence: float = Field(..., ge=0.0, le=1.0, description="分类置信度，范围0~1")
    reasoning: str = Field(..., description="归类理由")
    create_new_chapter: bool = Field(False, description="是否需要创建新章节")
    new_chapter: Dict[str, Any] = Field(
        default_factory=dict, description="新章节的信息（若需要）"
    )


class ChapterClassificationAgent(BaseAgent, ChapterAgentMixin):
    """
    章节分类Agent
    基于BaseAgent开发，专门负责将CQA内容归类到章节结构中
    """

    DEFAULT_AGENT_NAME = "chapter_classification_agent"

    DEFAULT_SYSTEM_PROMPT = """你是一个专业的内容分类专家，负责将对话内容合理归类到已有的章节结构中。

你的任务：
- 分析单个CQA对话内容的主题和性质
- 在已有章节结构中找到最合适的章节进行归类
- 如果现有结构不合适，建议创建新章节或子章节
- 确保新章节与现有结构协调一致，不超过指定最大层数

分类原则：
- 准确理解对话内容的主题
- 选择最相关的章节进行归类
- 避免创建过多细分章节
- 新建章节要有充分理由
- 严格控制层级深度
- 单个CPA 仅可以归类到唯一最相关的章节中
"""

    CLASSIFY_CONTENT_TEMPLATE = """请将以下问答对话归类到合适的章节中，或建议创建新章节：

现有章节结构：
{{chapter_tree}}

待归类的问答内容：
{% for qa in qa_list.items %}
{{ loop.index }}. Q: {{ qa.question }}
   A: {{ qa.answer }}
{% endfor %}

最大层数限制：{{max_level}}

要求：
1. 分析每个问答对的主题和性质
2. 为每个问答对找到最合适的章节进行归类
3. 如果现有结构不合适，建议创建新章节（不超过{{max_level}}层）
4. 提供归类理由和置信度

请按以下JSON数组格式返回归类结果（每个问答对一个结果）：

[
{% for qa in qa_list.items %}
  {
    "index": {{ loop.index }},
    "target_chapter_id": "章节ID",
    "confidence": 0.85,
    "reasoning": "归类理由",
    "create_new_chapter": false,
    "new_chapter": {
      "title": "新章节标题",
      "parent_id": "父章节ID",
      "description": "章节描述"
    }
  }{% if not loop.last %},{% endif %}
{% endfor %}
]
"""

    def __init__(self, **kwargs):
        super().__init__(
            system_prompt=self.DEFAULT_SYSTEM_PROMPT,
            user_prompt_template=self.CLASSIFY_CONTENT_TEMPLATE,
            **kwargs,
        )

    async def step(self, context: AIContext = None, **kwargs) -> Any:
        """执行一步Agent推理"""
        if context is None:
            working_context = AIContext()
        else:
            working_context = context

        # 添加系统提示词
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

    async def classify_content(
        self,
        qa_list: QAList,
        chapter_structure: ChapterStructure,
        max_level: int = 3,
        context: Optional[AIContext] = None,
    ) -> Tuple[List[ChapterClassificationResult], ChapterStructure]:
        """
        将QA内容分类到章节结构中

        Args:
            qa_list: 待分类的QA对话列表
            chapter_structure: 现有章节结构
            max_level: 最大层数限制
            context: AI上下文，如果为None则在step中创建

        Returns:
            元组：(分类结果列表, 更新后的章节结构)
        """
        try:
            chapter_tree = self._generate_chapter_tree_text(chapter_structure)
            logger.info(f"qa_list items len:{len(qa_list.items)}")

            response = await self.step(
                context=context,
                chapter_tree=chapter_tree,
                qa_list=qa_list,
                max_level=max_level,
            )

            classification_data_list: List[Dict[str, Any]] = (
                self._parse_classification_response(response)
            )

            results = []
            updated_structure = chapter_structure

            for i, classification_data in enumerate(classification_data_list):
                result: ChapterClassificationResult = self._build_classification_result(
                    classification_data, updated_structure
                )

                # 处理新章节创建
                if result.create_new_chapter:
                    new_node = self._create_new_chapter_node(
                        result.new_chapter, updated_structure, max_level
                    )
                    if new_node:
                        updated_structure.add_node(new_node)
                        result.target_chapter_id = new_node.id
                        logger.info(f"创建新章节: {new_node.title} (ID: {new_node.id})")

                # 关联QA案例到对应章节
                self._associate_qa_to_chapter(result, qa_list, updated_structure)

                logger.debug(
                    f"第{i+1}条内容分类结果: {result.target_chapter_id}, "
                    f"置信度: {result.confidence}"
                )
                results.append(result)

            return results, updated_structure

        except Exception as e:
            logger.error(f"内容分类失败: {e}")
            default_results = [
                self._create_default_classification(chapter_structure)
                for _ in qa_list.items
            ]
            return default_results, chapter_structure

    def _generate_chapter_tree_text(self, structure: ChapterStructure) -> str:
        """生成章节树文本"""
        lines = []

        def _build_tree(node_id: str, indent: str = "") -> None:
            if node_id not in structure.nodes:
                return

            node: ChapterNode = structure.nodes[node_id]
            lines.append(f"{indent}- {node.title} (ID: {node.id}, 层级: {node.level})")
            if node.description:
                lines.append(f"{indent}  描述: {node.description}")

            for child_id in node.children:
                _build_tree(child_id, indent + "  ")

        for root_id in structure.root_ids:
            _build_tree(root_id)

        return "\n".join(lines)

    def _parse_classification_response(self, response: str) -> List[Dict[str, Any]]:
        """解析分类响应"""
        result = self._parse_json_array_response(response)
        if result:
            return result

        # 解析失败，返回默认结果
        return [
            {
                "index": "parse_error",
                "target_chapter_id": "default",
                "confidence": 0.5,
                "reasoning": "解析失败，使用默认分类",
                "create_new_chapter": False,
                "new_chapter": {},  # 显式提供空字典
            }
        ]

    def _build_classification_result(
        self,
        classification_data: Dict[str, Any],
        chapter_structure: ChapterStructure,
    ) -> ChapterClassificationResult:
        """构建分类结果对象"""
        try:
            # 安全地提取和转换数据
            index = str(classification_data.get("index", "default"))
            target_id = str(classification_data.get("target_chapter_id", "default"))

            # 安全地处理confidence
            try:
                confidence = float(classification_data.get("confidence", 0.5))
                confidence = max(0.0, min(1.0, confidence))  # 限制在0-1范围内
            except (ValueError, TypeError):
                confidence = 0.5

            reasoning = str(classification_data.get("reasoning", "无理由说明"))
            create_new = bool(classification_data.get("create_new_chapter", False))

            # 安全地处理new_chapter
            new_chapter_raw = classification_data.get("new_chapter")
            if new_chapter_raw is None or not isinstance(new_chapter_raw, dict):
                new_chapter = {}
            else:
                new_chapter = dict(new_chapter_raw)  # 创建副本确保是字典

            # 验证目标章节是否存在
            if target_id not in chapter_structure.nodes and not create_new:
                target_id = self._get_default_chapter_id(chapter_structure)
                reasoning = f"原目标章节不存在，改为默认章节。{reasoning}"

            return ChapterClassificationResult(
                index=index,
                target_chapter_id=target_id,
                confidence=confidence,
                reasoning=reasoning,
                create_new_chapter=create_new,
                new_chapter=new_chapter,
            )
        except Exception as e:
            logger.error(f"构建分类结果对象失败: {e}")
            # 返回安全的默认值
            return ChapterClassificationResult(
                index="error",
                target_chapter_id=self._get_default_chapter_id(chapter_structure),
                confidence=0.5,
                reasoning=f"构建分类结果失败: {str(e)}",
                create_new_chapter=False,
                new_chapter={},
            )

    def _create_new_chapter_node(
        self,
        chapter_info: Dict[str, Any],
        structure: ChapterStructure,  # noqa: ARG002
        max_level: int,  # noqa: ARG002
    ) -> Optional[ChapterNode]:
        """创建新章节节点"""
        title = chapter_info.get("title", "").strip()
        if not title:
            logger.error("新章节标题为空")
            return None

        parent_id = chapter_info.get("parent_id")

        return ChapterNode(
            id=str(uuid.uuid4()),
            title=title,
            level=1,  # 临时值，add_node会自动计算正确的level
            parent_id=parent_id,
            description=chapter_info.get("description", ""),
        )

    def _get_default_chapter_id(self, structure: ChapterStructure) -> str:
        """获取默认章节ID"""
        if structure.root_ids:
            return structure.root_ids[0]
        return "default"

    def _create_default_classification(
        self, structure: ChapterStructure
    ) -> ChapterClassificationResult:
        """创建默认分类结果"""
        target_id = self._get_default_chapter_id(structure)

        return ChapterClassificationResult(
            index="default",
            target_chapter_id=target_id,
            confidence=0.5,
            reasoning="分类失败，使用默认章节",
            create_new_chapter=False,
            new_chapter={},  # 显式提供空字典
        )

    def _associate_qa_to_chapter(
        self,
        result: ChapterClassificationResult,
        qa_list: QAList,
        structure: ChapterStructure,
    ) -> None:
        """将QA案例关联到对应章节"""
        if not result.index or not result.target_chapter_id:
            return

        # 获取QA项并转换为CQA格式
        try:
            qa_index = int(result.index) - 1  # 转换为0-based索引
            if 0 <= qa_index < len(qa_list.items):
                qa_item = qa_list.items[qa_index]

                if result.target_chapter_id in structure.nodes:
                    target_node = structure.nodes[result.target_chapter_id]

                    # 将QA转换为CQA格式添加到节点
                    from agent_runtime.data_format.qa_format import CQAItem

                    cqa_item = QAItem(
                        question=qa_item.question,
                        answer=qa_item.answer,
                        metadata=qa_item.metadata,
                    )
                    target_node.add_qa_item(cqa_item)
                    logger.debug(
                        f"将QA案例 {result.index} 关联到章节 {target_node.title}"
                    )
        except (ValueError, IndexError) as e:
            logger.warning(f"无法关联QA案例 {result.index}: {e}")
