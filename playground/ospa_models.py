"""
OSPA数据模型定义
提供类型安全的数据结构和验证功能
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import pandas as pd


@dataclass
class OSPAItem:
    """OSPA数据项模型"""
    no: int
    O: str  # Observation - 观察/用户输入
    S: str = ""  # State - 状态/场景
    p: str = ""  # prompt - 提示词
    A: str = ""  # Action - Agent输出/标准答案
    A_prime: str = ""  # 候选答案（用于一致性比较）
    consistency: str = ""  # 一致性得分
    confidence_score: str = ""  # 置信度
    error: str = ""  # 错误信息

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'no': self.no,
            'O': self.O,
            'S': self.S,
            'p': self.p,
            'A': self.A,
            'A_prime': self.A_prime,
            'consistency': self.consistency,
            'confidence_score': self.confidence_score,
            'error': self.error
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OSPAItem':
        """从字典创建实例"""
        return cls(no=int(data.get('no', 0)),
                   O=str(data.get('O', '')),
                   S=str(data.get('S', '')),
                   p=str(data.get('p', '')),
                   A=str(data.get('A', '')),
                   A_prime=str(data.get('A_prime', '')),
                   consistency=str(data.get('consistency', '')),
                   confidence_score=str(data.get('confidence_score', '')),
                   error=str(data.get('error', '')))

    def is_valid_for_reward(self) -> bool:
        """检查是否可以进行一致性检测"""
        return bool(self.O.strip() and self.A.strip() and self.A_prime.strip())

    def is_valid_for_backward(self) -> bool:
        """检查是否可以进行backward处理"""
        return bool(self.O.strip() and self.A.strip())

    def is_valid_for_llm_generation(self) -> bool:
        """检查是否可以进行LLM生成"""
        return bool(self.O.strip() and self.p.strip())


@dataclass
class ProcessingResult:
    """处理结果模型"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: str = ""
    generated_answer: str = ""


class OSPAManager:
    """OSPA数据管理器"""

    def __init__(self):
        self.items: List[OSPAItem] = []

    def load_from_list(self, data_list: List[Dict[str, Any]]) -> None:
        """从字典列表加载数据"""
        self.items = [OSPAItem.from_dict(item) for item in data_list]

    def to_list(self) -> List[Dict[str, Any]]:
        """转换为字典列表"""
        return [item.to_dict() for item in self.items]

    def get_valid_items_for_reward(self) -> List[OSPAItem]:
        """获取可以进行一致性检测的数据项"""
        return [item for item in self.items if item.is_valid_for_reward()]

    def get_valid_items_for_backward(self) -> List[OSPAItem]:
        """获取可以进行backward处理的数据项"""
        return [item for item in self.items if item.is_valid_for_backward()]

    def get_valid_items_for_llm(self) -> List[OSPAItem]:
        """获取可以进行LLM生成的数据项"""
        return [
            item for item in self.items if item.is_valid_for_llm_generation()
        ]

    def update_item_by_no(self, no: int, **kwargs: Any) -> bool:
        """根据序号更新数据项"""
        for item in self.items:
            if item.no == no:
                for key, value in kwargs.items():
                    if hasattr(item, key):
                        setattr(item, key, value)
                return True
        return False

    def clear_field(self, field_name: str) -> None:
        """清空指定字段的所有数据"""
        for item in self.items:
            if hasattr(item, field_name):
                setattr(item, field_name, "")

    def to_dataframe(self) -> pd.DataFrame:
        """转换为DataFrame"""
        return pd.DataFrame(self.to_list())

    def load_from_csv(self,
                      file_path: str,
                      column_mapping: Optional[Dict[str, str]] = None) -> int:
        """从CSV文件加载数据"""
        try:
            df = pd.read_csv(file_path)

            # 默认列名映射
            if column_mapping is None:
                column_mapping = self._auto_detect_columns(df.columns)

            self.items = []
            for idx, row in df.iterrows():
                o_col = column_mapping.get('O', '')
                s_col = column_mapping.get('S', '')
                p_col = column_mapping.get('p', '')
                a_col = column_mapping.get('A', '')

                item_data = {
                    'no':
                    idx + 1,
                    'O':
                    str(row.get(o_col, ''))
                    if pd.notna(row.get(o_col, '')) else '',
                    'S':
                    str(row.get(s_col, ''))
                    if pd.notna(row.get(s_col, '')) else '',
                    'p':
                    str(row.get(p_col, ''))
                    if pd.notna(row.get(p_col, '')) else '',
                    'A':
                    str(row.get(a_col, ''))
                    if pd.notna(row.get(a_col, '')) else '',
                    'A_prime':
                    '',
                    'consistency':
                    '',
                    'confidence_score':
                    '',
                    'error':
                    ''
                }
                self.items.append(OSPAItem.from_dict(item_data))

            return len(self.items)
        except Exception as e:
            raise Exception(f"CSV文件加载失败: {str(e)}")

    def _auto_detect_columns(self, columns: List[str]) -> Dict[str, str]:
        """自动检测列名映射"""
        mapping = {}

        for col in columns:
            col_lower = col.lower().strip()
            if col_lower in [
                    'o', 'observation', 'user input', 'user_input', 'question',
                    'q'
            ]:
                mapping['O'] = col
            elif col_lower in [
                    'a', 'action', 'agent output', 'agent_output', 'answer',
                    'response'
            ]:
                mapping['A'] = col
            elif col_lower in ['s', 'state', 'scenario', 'status']:
                mapping['S'] = col
            elif col_lower in ['p', 'prompt', 'instruction']:
                mapping['p'] = col

        return mapping

    def get_statistics(self) -> Dict[str, int]:
        """获取数据统计信息"""
        return {
            'total_items':
            len(self.items),
            'valid_for_reward':
            len(self.get_valid_items_for_reward()),
            'valid_for_backward':
            len(self.get_valid_items_for_backward()),
            'valid_for_llm':
            len(self.get_valid_items_for_llm()),
            'has_consistency':
            sum(1 for item in self.items if item.consistency.strip()),
            'has_s_field':
            sum(1 for item in self.items if item.S.strip()),
            'has_p_field':
            sum(1 for item in self.items if item.p.strip()),
            'has_errors':
            sum(1 for item in self.items if item.error.strip())
        }
