import json
from typing import Any, Optional, List


def fix_json(json_str: str) -> Optional[Any]:
    """
    修复 JSON 字符串，主要应对缺少 list 开头 [ { 的情况。
    """
    s = json_str.strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        # 尝试补齐
        fixed = s

        # 如果不是以 '[' 开头，说明可能缺 [
        if not fixed.startswith("["):
            if fixed.startswith("{"):
                fixed = "[" + fixed  # 补 [
            else:
                # 有时可能直接是 key:value，没有 {，这里不做复杂修复
                fixed = "[{" + fixed

        # 如果不是以 ']' 结尾，补 ]
        if not fixed.endswith("]"):
            # 如果末尾是 '}', 那么直接补 ]
            if fixed.endswith("}"):
                fixed = fixed + "]"
            # 如果末尾是 '},' 之类，去掉逗号再补 ]
            elif fixed.endswith("},"):
                fixed = fixed[:-1] + "]"
            else:
                fixed = fixed + "]"

        try:
            return json.loads(fixed)
        except json.JSONDecodeError as e:
            raise ValueError(f"修复失败: {e}\n修复后字符串为:\n{fixed}")


def normalize_to_list(json_data: Any) -> List[Any]:
    """把各种可能的 LLM 返回结构统一成 list。
    规则：
      1) str → 尝试 json 解析，否则返回 [str]
      2) list → 原样返回
      3) dict →
         3.1 若含 'chapters' 且为 list，则返回该 list
         3.2 若只有一个键且该值为 list，返回该 list
         3.3 若有若干键，挑第一个值为 list 的返回
         3.4 否则把整个 dict 包成单元素列表
      4) None → []
      5) 其他标量 → [value]
    """
    if json_data is None:
        return []
    if isinstance(json_data, str):
        try:
            parsed = json.loads(json_data)
            return normalize_to_list(parsed)
        except Exception:
            return [json_data]
    if isinstance(json_data, list):
        return json_data
    if isinstance(json_data, dict):
        if isinstance(json_data.get("chapters"), list):
            return json_data["chapters"]
        if len(json_data) == 1:
            sole_val = next(iter(json_data.values()))
            if isinstance(sole_val, list):
                return sole_val
        # 选第一个值为 list 的键
        for v in json_data.values():
            if isinstance(v, list):
                return v
        return [json_data]
    # 标量或其他对象
    return [json_data]
