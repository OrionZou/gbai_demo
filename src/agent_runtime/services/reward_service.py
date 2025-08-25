import json
from typing import List, Literal, Any
from pydantic import BaseModel, Field, ConfigDict
from jinja2 import Template

from agent_runtime.clients.llm.openai_client import LLM
from agent_runtime.data_format.context_ai import AIContext
from agent_runtime.logging.logger import logger

Label = Literal["equivalent", "partially_equivalent", "different",
                "unsupported"]


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


class PairwiseJudge(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    index: int = Field(..., description="候选答案在输入数组中的下标")
    label: Label
    confidence: float = Field(..., ge=0, le=1)
    reason: str


class RewardRusult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    question: str
    target_answer: str
    results: List[PairwiseJudge]


SYSTEM_PROMPT = """
你是答案一致性评审器。仅依据“目标答案”的含义来判断每个候选答案与其是否一致。
标签定义：
- equivalent：与目标答案事实与结论等价；措辞不同不影响含义/范围。
- partially_equivalent：主体一致，但范围/前提/时间/数量等有限定差异或缺失。
- different：结论不同或互相矛盾。
- unsupported：与问题或目标答案无关、空泛，或加入目标答案未支持的推断/闲聊。
要求：
- 输出 JSON，键为 label/confidence/reason。
- confidence 给出0-1之间的小数，随判断把握调整。
- reason 简洁中文说明关键差异点。
"""

USER_PROMPT_TEMPLATE = """
问题：
{{ question }}

目标答案：
{{ target }}

候选答案：
{% for ans in candidates %}
{{ loop.index }}. {{ ans }}
{% endfor %}

输出 JSON 格式的列表，列表元素表示每个候选答案，：
[
{% for a in candidates %}
  {
    "index": {{ loop.index0 }},
    "label": "equivalent | partially_equivalent | different | unsupported",
    "confidence": 0.0-1.0,
    "reason": "简要中文理由"
  }{% if not loop.last %},{% endif %}
{% endfor %}
]
"""
user_template = Template(USER_PROMPT_TEMPLATE)


class RewardService:

    def __init__(self, llm_client: LLM):
        self.llm_client = llm_client

    async def compare_answer(self, question: str, candidates: List[str],
                             target_answer: str) -> RewardRusult:
        """
        使用 LLM 比较候选答案与目标答案的语义匹配度。
        返回结构包含：原因、分数
        """
        ctx = AIContext()

        ctx.add_system_prompt(SYSTEM_PROMPT)
        rendered_prompt = user_template.render(question=question,
                                               target=target_answer,
                                               candidates=candidates)
        ctx.add_user_prompt(rendered_prompt)
        logger.debug("LLM INPUT: {}", ctx.to_openai_format())
        json_data = await self.llm_client.structured_output_old(
            messages=ctx.to_openai_format())
        json_list = normalize_to_list(json_data)
        logger.debug(f"json_list:{json_list}")
        results = []
        for data in json_list:
            results.append(PairwiseJudge(**data))
        return RewardRusult(question=question,
                            target_answer=target_answer,
                            results=results)
