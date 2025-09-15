import json
import re
from typing import List, Dict, Any, Optional
from agent_runtime.data_format.qa_format import BQAList, BQAItem
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

    def _resolve_bqa_ids_from_indices(
        self, indices: List[str], bqa_lists: List[BQAList]
    ) -> List[str]:
        """根据索引列表解析出对应的BQA ID列表"""
        bqa_ids = []
        for index in indices:
            bqa_id = self._get_bqa_id_from_index(index, bqa_lists)
            if bqa_id:
                bqa_ids.append(bqa_id)
        return bqa_ids

    def _get_bqa_id_from_index(
        self, index: str, bqa_lists: List[BQAList]
    ) -> str:
        """根据单个索引获取BQA ID"""
        try:
            parts = index.split('-')
            if len(parts) != 2:
                logger.warning(f"无效的BQA索引格式: {index}")
                return ""

            list_idx = int(parts[0]) - 1
            item_idx = int(parts[1]) - 1

            if (0 <= list_idx < len(bqa_lists) and
                0 <= item_idx < len(bqa_lists[list_idx].items)):
                bqa_item = bqa_lists[list_idx].items[item_idx]
                logger.debug(
                    f"解析索引 {index} -> BQA ID: {bqa_item.bqa_id}"
                )
                return bqa_item.bqa_id
            else:
                logger.warning(f"BQA索引超出范围: {index}")
                return ""

        except (ValueError, IndexError) as e:
            logger.warning(f"解析BQA索引失败: {index}, 错误: {e}")
            return ""

    def _get_bqa_item_from_index(
        self, index: str, bqa_lists: List[BQAList]
    ) -> Optional[BQAItem]:
        """根据索引获取BQA项"""
        try:
            parts = index.split('-')
            if len(parts) != 2:
                return None

            list_idx = int(parts[0]) - 1
            item_idx = int(parts[1]) - 1

            if (0 <= list_idx < len(bqa_lists) and
                0 <= item_idx < len(bqa_lists[list_idx].items)):
                return bqa_lists[list_idx].items[item_idx]

        except (ValueError, IndexError):
            pass

        return None

    def _create_bqa_mapping(
        self, bqa_lists: List[BQAList]
    ) -> Dict[str, BQAItem]:
        """创建BQA ID到BQAItem的映射"""
        bqa_mapping = {}
        for bqa_list in bqa_lists:
            for bqa_item in bqa_list.items:
                bqa_mapping[bqa_item.bqa_id] = bqa_item
        return bqa_mapping