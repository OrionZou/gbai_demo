from typing import List, Dict, Any, Optional
import json
from pathlib import Path
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
    content: Optional[str] = ""  # 章节内容，如生成的提示词
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

    def set_node_content(self, node_id: str, content: str) -> bool:
        """为指定节点设置内容
        
        Args:
            node_id: 节点ID
            content: 要设置的内容
            
        Returns:
            bool: 设置是否成功
        """
        if node_id in self.nodes:
            self.nodes[node_id].content = content
            return True
        return False

    def add_node_content(self, node_id: str, additional_content: str, separator: str = "\n\n") -> bool:
        """为指定节点追加内容
        
        Args:
            node_id: 节点ID
            additional_content: 要追加的内容
            separator: 内容分隔符，默认为双换行
            
        Returns:
            bool: 追加是否成功
        """
        if node_id in self.nodes:
            current_content = self.nodes[node_id].content or ""
            if current_content:
                self.nodes[node_id].content = current_content + separator + additional_content
            else:
                self.nodes[node_id].content = additional_content
            return True
        return False

    def get_node_content(self, node_id: str) -> Optional[str]:
        """获取指定节点的内容
        
        Args:
            node_id: 节点ID
            
        Returns:
            str: 节点内容，如果节点不存在则返回None
        """
        if node_id in self.nodes:
            return self.nodes[node_id].content
        return None

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
                "content": node.content,
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
                content=node_data.get("content", ""),
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

            # 显示章节内容
            if node.content:
                content_preview = node.content
                if len(content_preview) > 100:
                    content_preview = content_preview[:100] + "..."
                lines.append(f"{indent}  内容: {content_preview}")

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

    def to_json_string(self, indent: int = 2, ensure_ascii: bool = False) -> str:
        """导出为JSON字符串
        
        Args:
            indent: JSON缩进空格数，None表示紧凑格式
            ensure_ascii: 是否确保ASCII编码，False支持中文字符
            
        Returns:
            str: JSON格式的章节结构字符串
        """
        # 构建完整的数据结构
        json_data = {
            "metadata": {
                "max_level": self.max_level,
                "total_nodes": len(self.nodes),
                "total_cqas": sum(len(node.related_cqa_items) for node in self.nodes.values()),
                "root_count": len(self.root_ids)
            },
            "nodes": {},
            "root_ids": self.root_ids,
            "max_level": self.max_level
        }
        
        # 序列化每个节点
        for node_id, node in self.nodes.items():
            json_data["nodes"][node_id] = {
                "id": node.id,
                "title": node.title,
                "level": node.level,
                "parent_id": node.parent_id,
                "children": node.children,
                "description": node.description,
                "content": node.content,
                "related_cqa_items": [
                    {
                        "cqa_id": cqa.cqa_id,
                        "question": cqa.question,
                        "answer": cqa.answer,
                        "context": cqa.context
                    } for cqa in node.related_cqa_items
                ],
                "related_cqa_ids": node.related_cqa_ids,
                "chapter_number": node.chapter_number
            }
        
        return json.dumps(json_data, indent=indent, ensure_ascii=ensure_ascii)

    def save_to_json_file(self, file_path: str, indent: int = 2, ensure_ascii: bool = False) -> bool:
        """保存章节结构到JSON文件
        
        Args:
            file_path: 文件路径
            indent: JSON缩进空格数
            ensure_ascii: 是否确保ASCII编码
            
        Returns:
            bool: 保存是否成功
        """
        try:
            json_string = self.to_json_string(indent=indent, ensure_ascii=ensure_ascii)
            
            # 确保目录存在
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(json_string)
            
            return True
        except Exception as e:
            print(f"保存JSON文件失败: {e}")
            return False

    @classmethod
    def from_json_string(cls, json_string: str) -> "ChapterStructure":
        """从JSON字符串创建章节结构
        
        Args:
            json_string: JSON格式的章节结构字符串
            
        Returns:
            ChapterStructure: 章节结构对象
            
        Raises:
            ValueError: JSON格式不正确
            KeyError: 缺少必要字段
        """
        try:
            data = json.loads(json_string)
            
            # 验证必要字段
            if not isinstance(data, dict) or "nodes" not in data:
                raise ValueError("JSON数据格式不正确，缺少'nodes'字段")
            
            max_level = data.get("max_level", 3)
            structure = cls(max_level=max_level)
            
            # 第一步：创建所有节点（不设置父子关系）
            nodes_data = data["nodes"]
            temp_nodes = {}
            
            for node_id, node_data in nodes_data.items():
                # 重建CQAItem对象
                cqa_items = []
                for cqa_data in node_data.get("related_cqa_items", []):
                    from agent_runtime.data_format.qa_format import CQAItem
                    cqa_item = CQAItem(
                        cqa_id=cqa_data.get("cqa_id", ""),
                        question=cqa_data.get("question", ""),
                        answer=cqa_data.get("answer", ""),
                        context=cqa_data.get("context", "")
                    )
                    cqa_items.append(cqa_item)
                
                node = ChapterNode(
                    id=node_data.get("id", node_id),
                    title=node_data.get("title", ""),
                    level=node_data.get("level", 1),
                    parent_id=node_data.get("parent_id"),
                    children=node_data.get("children", []).copy(),
                    description=node_data.get("description", ""),
                    content=node_data.get("content", ""),
                    related_cqa_items=cqa_items,
                    related_cqa_ids=node_data.get("related_cqa_ids", []).copy(),
                    chapter_number=node_data.get("chapter_number", "")
                )
                temp_nodes[node_id] = node
            
            # 第二步：设置节点关系和添加到结构中
            structure.nodes = temp_nodes
            structure.root_ids = data.get("root_ids", [])
            
            # 重新生成章节编号以确保一致性
            structure._generate_chapter_numbers()
            
            return structure
            
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON解析失败: {e}")
        except Exception as e:
            raise ValueError(f"创建章节结构失败: {e}")

    @classmethod
    def load_from_json_file(cls, file_path: str) -> "ChapterStructure":
        """从JSON文件加载章节结构
        
        Args:
            file_path: JSON文件路径
            
        Returns:
            ChapterStructure: 章节结构对象
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: JSON格式不正确
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json_string = f.read()
            
            return cls.from_json_string(json_string)
            
        except FileNotFoundError:
            raise FileNotFoundError(f"JSON文件不存在: {file_path}")
        except Exception as e:
            raise ValueError(f"加载JSON文件失败: {e}")


class ChapterResponse(BaseModel):
    """章节构建响应"""

    chapter_structure: ChapterStructure
    content_mapping: Dict[str, List[str]] = Field(
        default_factory=dict
    )  # 节点ID到CQA ID的映射
    operation_log: List[str] = Field(default_factory=list)  # 操作日志
