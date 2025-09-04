from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from agent_runtime.data_format.qa_format import CQAList, CQAItem


class ChapterRequest(BaseModel):
    """章节构建请求"""

    existing_chapters: Optional[Dict[str, Any]] = None  # 已有章节目录字典
    cqa_lists: List[CQAList]  # CQA对话列表
    max_level: int = 3  # 最大目录层数


class ChapterNode(BaseModel):
    """章节节点"""

    id: str
    title: str
    level: int  # 层级（1为最高层级）
    parent_id: Optional[str] = None
    children: List[str] = Field(default_factory=list)
    description: Optional[str] = ""
    related_cqa_items: List[CQAItem] = Field(
        default_factory=list
    )  # 关联的CQA案例对象
    related_cqa_ids: List[str] = Field(default_factory=list)  # 关联的CQA案例ID
    chapter_number: str = ""  # 章节编号，如 "1.", "1.1", "2.1.1"

    def add_child(self, child_id: str) -> None:
        if child_id not in self.children:
            self.children.append(child_id)

    def add_cqa_item(self, cqa_item: CQAItem) -> None:
        """添加CQA案例对象"""
        if cqa_item not in self.related_cqa_items:
            self.related_cqa_items.append(cqa_item)
            # 同时添加CQA ID
            if cqa_item.cqa_id not in self.related_cqa_ids:
                self.related_cqa_ids.append(cqa_item.cqa_id)


class ChapterStructure(BaseModel):
    """章节结构"""

    nodes: Dict[str, ChapterNode] = Field(default_factory=dict)
    root_ids: List[str] = Field(default_factory=list)
    max_level: int = 3

    def add_node(self, node: ChapterNode) -> None:
        # 自动计算并设置节点层级
        if node.parent_id is None:
            # 根节点，层级为1
            node.level = 1
            if node.id not in self.root_ids:
                self.root_ids.append(node.id)
        else:
            if node.parent_id in self.nodes:
                # 子节点，层级为父节点层级+1，但不超过最大层级
                parent_level = self.nodes[node.parent_id].level
                node.level = min(parent_level + 1, self.max_level)
                self.nodes[node.parent_id].add_child(node.id)
            else:
                # 父节点不存在，作为根节点处理
                node.level = 1
                node.parent_id = None
                if node.id not in self.root_ids:
                    self.root_ids.append(node.id)

        self.nodes[node.id] = node

        # 自动生成章节编号
        self._generate_chapter_numbers()

    def get_node(self, node_id: str) -> Optional[ChapterNode]:
        return self.nodes.get(node_id)

    def _generate_chapter_numbers(self) -> None:
        """自动生成章节编号"""
        # 重置所有章节编号
        for node in self.nodes.values():
            node.chapter_number = ""

        # 为根节点编号
        for i, root_id in enumerate(self.root_ids, 1):
            if root_id in self.nodes:
                self._number_node(root_id, str(i))

    def _number_node(self, node_id: str, number_prefix: str) -> None:
        """递归为节点及其子节点编号"""
        if node_id not in self.nodes:
            return

        node = self.nodes[node_id]
        node.chapter_number = f"{number_prefix}."

        # 为子节点编号
        for i, child_id in enumerate(node.children, 1):
            child_number = f"{number_prefix}.{i}"
            self._number_node(child_id, child_number)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {}

        def _build_dict(node_id: str) -> Dict[str, Any]:
            if node_id not in self.nodes:
                return {}

            node = self.nodes[node_id]
            node_dict = {
                "id": node.id,
                "title": node.title,
                "level": node.level,
                "description": node.description,
                "related_cqa_ids": node.related_cqa_ids,
                "children": {},
            }

            for child_id in node.children:
                child_dict = _build_dict(child_id)
                if child_dict:
                    node_dict["children"][child_id] = child_dict

            return node_dict

        for root_id in self.root_ids:
            result[root_id] = _build_dict(root_id)

        return result

    @classmethod
    def from_dict(
        cls, data: Dict[str, Any], max_level: int = 3
    ) -> "ChapterStructure":
        """从字典创建章节结构"""
        structure = cls(max_level=max_level)

        def _parse_node(
            node_data: Dict[str, Any], parent_id: Optional[str] = None
        ) -> None:
            node = ChapterNode(
                id=node_data.get("id", ""),
                title=node_data.get("title", ""),
                level=1,  # 临时值，add_node会自动计算正确的level
                parent_id=parent_id,
                description=node_data.get("description", ""),
                related_cqa_ids=node_data.get("related_cqa_ids", []),
            )

            structure.add_node(node)

            # 处理子节点
            children = node_data.get("children", {})
            for child_data in children.values():
                _parse_node(child_data, node.id)

        for root_data in data.values():
            _parse_node(root_data)

        return structure

    def structure_str(self, show_cqa_info: bool = True) -> str:
        """打印章节结构"""
        lines = []

        def _build_tree_display(node_id: str, indent: str = "") -> None:
            if node_id not in self.nodes:
                return

            node = self.nodes[node_id]
            # 显示章节编号、标题和层级
            chapter_info = f"{indent}{node.chapter_number} {node.title}"
            if node.level > 1:
                chapter_info += f" (层级: {node.level})"
            lines.append(chapter_info)

            # 显示描述
            if node.description:
                lines.append(f"{indent}  描述: {node.description}")

            # 显示关联的CQA信息
            if show_cqa_info and node.related_cqa_items:
                cqa_count = len(node.related_cqa_items)
                lines.append(f"{indent}  关联CQA: {cqa_count}个")
                for i, cqa_item in enumerate(node.related_cqa_items[:3], 1):
                    question = cqa_item.question
                    if len(question) > 50:
                        question_preview = question[:50] + "..."
                    else:
                        question_preview = question
                    lines.append(f"{indent}    {i}. {question_preview}")
                if len(node.related_cqa_items) > 3:
                    remaining = len(node.related_cqa_items) - 3
                    lines.append(f"{indent}    ... 还有 {remaining} 个")

            # 递归显示子节点
            for child_id in node.children:
                _build_tree_display(child_id, indent + "  ")

        # 显示标题
        lines.append(f"章节结构 (最大层级: {self.max_level})")
        lines.append("=" * 50)

        # 显示根节点
        for root_id in self.root_ids:
            _build_tree_display(root_id)

        return "\n".join(lines)

    def __str__(self) -> str:
        """字符串表示"""
        return self.structure_str()

    def get_summary(self) -> str:
        """获取章节结构摘要"""
        total_nodes = len(self.nodes)
        total_cqas = sum(
            len(node.related_cqa_items) for node in self.nodes.values()
        )

        return (
            f"章节结构摘要: {total_nodes}个章节, "
            f"{total_cqas}个关联CQA, "
            f"最大层级: {self.max_level}"
        )


class ChapterResponse(BaseModel):
    """章节构建响应"""

    chapter_structure: ChapterStructure
    content_mapping: Dict[str, List[str]] = Field(
        default_factory=dict
    )  # 节点ID到CQA ID的映射
    operation_log: List[str] = Field(default_factory=list)  # 操作日志
