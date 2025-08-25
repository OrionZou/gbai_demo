import json
from jinja2 import Template
from typing import List, Dict, Any, cast

from agent_runtime.clients.llm.openai_client import LLM
from agent_runtime.data_format.context_ai import AIContext
from agent_runtime.logging.logger import logger


CHAPTER_SYS = """
你是知识手册的编目编辑。你会为一组高度相关的问答素材，起一个短小但具体的“章节名(c)”。不要输出解释。
"""

CHAPTER_USER_TEMPLATE = """
请基于下列Q&A素材，生成一个适合手册目录的章节名。
要求：{style}；不超过12个汉字/或8个英文词。

素材：
{bullets}

只输出章节名本身。
"""


GEN_P_SYS = """
你是提示工程专家。你将为一个章节，写一段“辅助提示词(p)”，用于引导LLM在已知章节主题下，根据问题(q)更容易写出答案(a)。
"""

GEN_P_USER_TEMPLATE_ZH = """
请为下面的章节写一个“辅助提示词 p”（不超过120字，中文），它将与章节名(c)和具体问题(q)一起提供给LLM，以便更容易生成答案(a)。
- 语言：中文
- 风格：指令化、要点式
- 内容：说明应覆盖的知识点、结构建议、注意事项、必要的术语或边界条件
- 避免：空话、与(c)无关的泛化建议

章节名(c)：{c}

示例问题(q)若干（供你把握范围）：
{q_samples}

只输出 p。"""

class BackwardService:

    def __init__(self, llm_client: LLM) -> None:
        self.llm = llm_client

    async def _aggregate_chapters(self,
                                  qas: List[List[str, str]]) -> Dict[str, Any]:
        """调用 LLM 将 Q&A 聚合成章节结构"""

        prompt = ("任务: 请将以下 Q&A 按照主题聚合成章节。\n"
                  f"输入: {{\"qas\": {json.dumps(qas, ensure_ascii=False)}}}\n"
                  "输出: JSON 格式 {"
                  "\"章节名称1\":{"
                  "\"reason\":\"聚合原因\","
                  "\"qas\":[{\"q\":\"...\",\"a\":\"...\"},...]}, ...}")
        try:
            return await self.llm.structured_output_old(
                messages=[{
                    "role": "user",
                    "content": prompt
                }])
        except Exception as e:
            raise ValueError(f"章节聚合结果解析失败: {e}")

    async def _generate_prompt_for_chapter(self, chapter_name: str,
                                           qas: List[Dict[str, str]]) -> str:
        """为指定章节生成辅助提示词"""
        prompt = (
            "任务: 根据以下章节数据，生成一个辅助提示词，"
            "使得 LLM 容易根据 chapter_name、prompt 和 q 生成 a。\n"
            f"输入: {{\"chapter_name\": \"{chapter_name}\", "
            f"\"qas\": {json.dumps(qas, ensure_ascii=False)}}}\n"
            "输出: JSON 格式 {\"chapter_name\":\"...\",\"prompt\":\"辅助提示词\"}")
        try:
            result = await self.llm.structured_output_old(
                messages=[{
                    "role": "user",
                    "content": prompt
                }])
            prompt_val: Any = result.get("prompt", "")
            if not isinstance(prompt_val, str):
                return str(prompt_val)
            return cast(str, prompt_val)
        except Exception as e:
            raise ValueError(f"提示词结果解析失败: {e}")

    async def backward(self, qas: List[Dict[str,
                                            str]]) -> List[Dict[str, Any]]:
        """ orchestrator: 先章节聚合，再生成提示词，并返回结果列表 """

        ctx = AIContext()
        agg_json = await self._aggregate_chapters(qas)

        results: List[Dict[str, Any]] = []
        for chapter_name, chapter_data in agg_json.items():
            chapter_qas = chapter_data.get("qas", [])
            prompt_text = await self._generate_prompt_for_chapter(
                chapter_name, chapter_qas)
            for qa in chapter_qas:
                results.append({
                    "q": qa["q"],
                    "a": qa["a"],
                    "chapter_name": chapter_name,
                    "prompt": prompt_text,
                })
        return results
