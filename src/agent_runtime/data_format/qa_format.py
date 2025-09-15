import uuid
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class QAItem(BaseModel):
    """单个问答对"""

    question: str
    answer: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BQAItem(BaseModel):
    """带背景的问答对"""
    bqa_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="bqa唯一标识")
    background: str
    question: str
    answer: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def __str__(self) -> str:
        """友好的转字符串"""
        meta_str = f"[Metadata] {self.metadata}" if self.metadata else ""
        return (
            f"[Background] {self.background} \n"
            f"[Question] {self.question} \n"
            f"[Answer] {self.answer} \n"
            # f"{meta_str}"
        )


class QAList(BaseModel):
    """问答列表"""

    items: List[QAItem] = Field(default_factory=list)
    session_id: str = ""

    def add_qa(
        self, question: str, answer: str, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """添加问答对"""
        if metadata is None:
            metadata = {}
        self.items.append(QAItem(question=question, answer=answer, metadata=metadata))

    def get_history_text(self, end_index: int) -> str:
        """获取指定索引前的历史对话文本"""
        history_parts = []
        for i in range(min(end_index, len(self.items))):
            item = self.items[i]
            history_parts.append(f"Q: {item.question}")
            history_parts.append(f"A: {item.answer}")
        return "\n".join(history_parts)


class BQAList(BaseModel):
    """带背景的问答列表"""

    items: List[BQAItem] = Field(default_factory=list)
    session_id: str = ""

    def add_bqa(
        self,
        background: str,
        question: str,
        answer: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """添加带背景的问答对"""
        if metadata is None:
            metadata = {}
        self.items.append(
            BQAItem(
                background=background, question=question, answer=answer, metadata=metadata
            )
        )

    def __len__(self) -> int:
        """返回问答数量"""
        return len(self.items)
    
    def __iter__(self):
        """支持迭代"""
        return iter(self.items)


# 为了向后兼容，保留旧的CQA类名作为别名
CQAItem = BQAItem
CQAList = BQAList