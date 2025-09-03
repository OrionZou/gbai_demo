import json
import re
from typing import List, Dict, Any, Optional
from agent_runtime.data_format.qa_format import CQAList, CQAItem
from agent_runtime.logging.logger import logger


class ChapterAgentMixin:
    """章节Agent共享功能的Mixin类"""

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """解析JSON响应"""
        json_match = re.search(r"\{.*\}", response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败: {e}")
        return {}

    def _parse_json_array_response(self, response: str) -> List[Dict[str, Any]]:
        """解析JSON数组响应"""
        # 先尝试解析数组格式
        json_array_match = re.search(r"\[.*\]", response, re.DOTALL)
        if json_array_match:
            try:
                return json.loads(json_array_match.group())
            except json.JSONDecodeError as e:
                logger.error(f"JSON数组解析失败: {e}")

        # 如果不是数组，尝试解析单个对象
        single_result = self._parse_json_response(response)
        if single_result:
            return [single_result]

        return []

    def _resolve_cqa_ids_from_indices(
        self, indices: List[str], cqa_lists: List[CQAList]
    ) -> List[str]:
        """根据索引列表解析出对应的CQA ID列表"""
        cqa_ids = []
        for index in indices:
            cqa_id = self._get_cqa_id_from_index(index, cqa_lists)
            if cqa_id:
                cqa_ids.append(cqa_id)
        return cqa_ids

    def _get_cqa_id_from_index(
        self, index: str, cqa_lists: List[CQAList]
    ) -> str:
        """根据单个索引获取CQA ID"""
        try:
            parts = index.split('-')
            if len(parts) != 2:
                logger.warning(f"无效的CQA索引格式: {index}")
                return ""

            list_idx = int(parts[0]) - 1
            item_idx = int(parts[1]) - 1

            if (0 <= list_idx < len(cqa_lists) and
                0 <= item_idx < len(cqa_lists[list_idx].items)):
                cqa_item = cqa_lists[list_idx].items[item_idx]
                logger.debug(
                    f"解析索引 {index} -> CQA ID: {cqa_item.cqa_id}"
                )
                return cqa_item.cqa_id
            else:
                logger.warning(f"CQA索引超出范围: {index}")
                return ""

        except (ValueError, IndexError) as e:
            logger.warning(f"解析CQA索引失败: {index}, 错误: {e}")
            return ""

    def _get_cqa_item_from_index(
        self, index: str, cqa_lists: List[CQAList]
    ) -> Optional[CQAItem]:
        """根据索引获取CQA项"""
        try:
            parts = index.split('-')
            if len(parts) != 2:
                return None

            list_idx = int(parts[0]) - 1
            item_idx = int(parts[1]) - 1

            if (0 <= list_idx < len(cqa_lists) and
                0 <= item_idx < len(cqa_lists[list_idx].items)):
                return cqa_lists[list_idx].items[item_idx]

        except (ValueError, IndexError):
            pass

        return None

    def _create_cqa_mapping(
        self, cqa_lists: List[CQAList]
    ) -> Dict[str, CQAItem]:
        """创建CQA ID到CQAItem的映射"""
        cqa_mapping = {}
        for cqa_list in cqa_lists:
            for cqa_item in cqa_list.items:
                cqa_mapping[cqa_item.cqa_id] = cqa_item
        return cqa_mapping