import json
import asyncio
from jinja2 import Template
from typing import List, Dict, Any, Tuple, Optional
from pydantic import BaseModel, Field, ConfigDict

from agent_runtime.clients.llm.openai_client import LLM
from agent_runtime.data_format.context_ai import AIContext
from agent_runtime.logging.logger import logger


# -----------------------------
# 数据模型
# -----------------------------
class QAItem(BaseModel):
    """问答对数据模型
    
    Attributes:
        q (str): 问题内容
        a (str): 答案内容
    """
    q: str
    a: str


class ChapterGroup(BaseModel):
    """章节组数据模型
    
    包含章节的基本信息、聚合原因、相关问答对和生成的辅助提示词
    
    Attributes:
        chapter_name (str): 章节名称
        reason (str): 章节聚合原因
        qas (List[QAItem]): 章节包含的问答对列表
        prompt (Optional[str]): 章节级辅助提示词，用于指导LLM基于该章节回答问题
    """
    chapter_name: str
    reason: str
    qas: List[QAItem]
    prompt: Optional[str] = None  # 章节级辅助提示词


class OSPA(BaseModel):
    """OSPA数据模型
    
    OSPA是用于结构化知识表示的四元组模型，包含目标、场景、提示和答案四个维度。
    
    Attributes:
        o (str): Objective - 目标，通常是用户的问题或查询内容
        s (str): Scenario - 场景，描述问题所属的上下文或章节信息
        p (str): Prompt - 提示，指导LLM如何基于特定场景回答问题的提示词
        a (str): Answer - 答案，对应问题的标准答案
    """
    o: str  # Objective - 目标问题
    s: str  # Scenario - 场景上下文
    p: str  # Prompt - 辅助提示词
    a: str  # Answer - 标准答案


def chapter_to_ospa(chapter: ChapterGroup) -> List[OSPA]:
    """将单个章节组转换为OSPA列表
    
    该函数将一个章节组中的所有问答对转换为OSPA格式，
    其中场景信息来自章节名称和聚合原因，提示词来自章节的专用提示词。
    
    Args:
        chapter (ChapterGroup): 需要转换的章节组
        
    Returns:
        List[OSPA]: 转换后的OSPA列表，每个问答对对应一个OSPA条目
        
    Example:
        >>> chapter = ChapterGroup(chapter_name="Python基础", reason="Python语法相关", qas=[...])
        >>> ospa_list = chapter_to_ospa(chapter)
        >>> print(f"生成了 {len(ospa_list)} 个OSPA条目")
    """
    ospa_list = []
    s_value = f"章节: {chapter.chapter_name}。聚合原因: {chapter.reason}"
    p_value = chapter.prompt or f"回答时请限定在章节『{chapter.chapter_name}』的知识范围内。"

    for qa in chapter.qas:
        ospa_list.append(OSPA(o=qa.q, s=s_value, p=p_value, a=qa.a))
    return ospa_list


def chapters_to_ospa(chapters: List[ChapterGroup]) -> List[OSPA]:
    """将多个章节组批量转换为OSPA列表
    
    该函数是chapter_to_ospa的批量版本，将多个章节组合并转换为统一的OSPA列表。
    
    Args:
        chapters (List[ChapterGroup]): 需要转换的章节组列表
        
    Returns:
        List[OSPA]: 所有章节转换后的OSPA条目合集
        
    Example:
        >>> chapters = [chapter1, chapter2, chapter3]
        >>> all_ospa = chapters_to_ospa(chapters)
        >>> print(f"总共生成了 {len(all_ospa)} 个OSPA条目")
    """
    result = []
    for ch in chapters:
        result.extend(chapter_to_ospa(ch))
    return result


# -----------------------------
# 系统提示词模板
# -----------------------------
CHAPTER_SYS = (
    "你是优秀的技术编辑，擅长为知识手册将 Q&A 素材进行主题化分章与聚合。"
    "要求：\n"
    "1) 先观察所有 Q 与 A 的主题相似度，进行语义聚类；\n"
    "2) 生成清晰、去重、非重叠的章节名；\n"
    "3) 每个章节配简短的聚合原因；\n"
    "4) 严格输出 JSON，字段为：chapters=[{chapter_name, reason, qas=[{q,a}]}];\n")
"""章节聚合系统提示词
用于指导LLM将问答对按语义相似度聚合成有意义的章节结构
"""

CHAPTER_USER_TEMPLATE = """
请将以下 Q&A 素材聚合为章节 JSON：

【输入 Q&A 列表】：
{% for qa in qas %}
{{ loop.index }}. {{ qa }}
{% endfor %}

【补充约束】：
{% if extra_instructions -%}
{{ extra_instructions }}
{%- endif %}

【输出 JSON 严格格式】：
{
  "chapters": [
    {
      "chapter_name": "...",
      "reason": "...",
      "qas": [{"q":"...", "a":"..."}]
    }
  ]
}

"""
"""章节聚合用户提示词模板
使用Jinja2模板语法，支持动态插入问答对列表和额外指令
"""

chapter_user_template = Template(CHAPTER_USER_TEMPLATE)

GEN_P_SYS = """
你是提示词工程专家与技术编辑。目标：为给定的章节，产出一个'辅助提示词 prompt'，该提示词将与 {chapter_name, q} 一起提供给 LLM，用于更准确地生成 a。

要求：
 - 严格限定知识范围：只依据本章节的主题与提供的 Q&A 语料，不得臆造外部事实；
 - 当问题超出本章节范围或缺乏依据时，应指导回答者明确说明'依据不足'并给出继续提问方向；
 - 语气专业、克制、面向技术文档；
 - 输出语言与输入示例主要语言一致（若示例以中文为主则输出中文）；
 - 优先使用示例中的术语与命名，保持一致性；
 - 回答策略：若是概念性问题先给定义与边界；若是流程/配置问题给步骤或要点清单；
 - 禁止包含与问题无关的客套话、个人观点、链接；
"""
"""章节提示词生成系统提示词
用于指导LLM为每个章节生成专用的辅助提示词，确保提示词质量和一致性
"""

GEN_P_USER_TEMPLATE_ZH = """
章节名称：{{ chapter_name }}

{% if reason %}
章节聚合理由：{{ reason }}
{% endif %}

【补充约束】：
{% if extra_instructions -%}
{{ extra_instructions }}
{%- endif %}

【章节相关示例】：
{% for qa in qas %}
{{ loop.index }}. {{ qa }}
{% endfor %}

请生成一个可复用的章节级辅助提示词，用于指导 LLM 依据该章节回答此主题下的问题。
"""
"""章节提示词生成用户提示词模板
中文版本，用于为特定章节生成专用的辅助提示词。支持动态插入章节信息、示例和额外约束。
"""

gen_p_user_template = Template(GEN_P_USER_TEMPLATE_ZH)


# -----------------------------
# 工具函数
# -----------------------------
def normalize_to_list(json_data: Any) -> List[Any]:
    """将各种可能的 LLM 返回结构统一转换成列表格式
    
    这个函数处理 LLM 可能返回的各种数据格式，确保返回统一的列表结构。
    
    Args:
        json_data (Any): LLM 返回的原始数据
        
    Returns:
        List[Any]: 标准化后的列表
        
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


# -----------------------------
# 核心服务类
# -----------------------------
class BackwardService:
    """反向知识处理服务
    
    该服务负责将问答对(Q&A)聚合成有意义的章节结构，并为每个章节生成
    辅助提示词，用于指导后续的问答生成和知识检索。
    
    主要功能：
    1. 将散乱的Q&A对按语义相似度聚合成章节
    2. 为每个章节生成专用的辅助提示词
    3. 提供完整的知识结构化工作流
    
    Attributes:
        llm_client (LLM): 大语言模型客户端，用于执行聚合和生成任务
    """

    def __init__(self, llm_client: LLM) -> None:
        """初始化反向知识处理服务
        
        Args:
            llm_client (LLM): 大语言模型客户端实例
        """
        self.llm_client = llm_client

    async def _aggregate_chapters(
            self,
            qas: List[Tuple[str, str]],
            extra_instructions: str = "",
            ctx: Optional[AIContext] = None) -> List[ChapterGroup]:
        """调用 LLM 将 Q&A 聚合成章节结构
        
        该方法使用大语言模型分析问答对的语义相似度，将相关的Q&A
        聚合到同一个章节中，并生成章节名称和聚合理由。
        
        Args:
            qas (List[Tuple[str, str]]): 问答对列表，每个元组包含(问题, 答案)
            extra_instructions (str, optional): 额外的聚合指令. Defaults to "".
            ctx (Optional[AIContext], optional): AI上下文对象. Defaults to None.
            
        Returns:
            List[ChapterGroup]: 聚合后的章节组列表
            
        Raises:
            Exception: 当LLM调用失败或返回格式不正确时抛出异常
        """
        if ctx is None:
            ctx = AIContext()

        ctx.add_system_prompt(CHAPTER_SYS)
        rendered_prompt = chapter_user_template.render(
            qas=qas, extra_instructions=extra_instructions)

        ctx.add_user_prompt(rendered_prompt)

        logger.debug("LLM INPUT: {}", ctx.to_openai_format())
        json_data = await self.llm_client.structured_output_old(
            messages=ctx.to_openai_format())
        json_list = normalize_to_list(json_data)

        logger.debug(f"json_list:{json_list}")

        results = []
        for data in json_list:
            results.append(ChapterGroup(**data))
        return results

    async def _generate_chapter_prompt(
            self,
            chapter_group: ChapterGroup,
            extra_instructions: str = "",
            ctx: Optional[AIContext] = None) -> ChapterGroup:
        """为每个章节生成辅助提示词
        
        基于章节的主题和包含的Q&A示例，生成一个专用的提示词，
        该提示词将指导LLM如何基于该章节的知识回答相关问题。
        
        Args:
            chapter_group (ChapterGroup): 需要生成提示词的章节组
            extra_instructions (str, optional): 额外的生成指令. Defaults to "".
            ctx (Optional[AIContext], optional): AI上下文对象. Defaults to None.
            
        Returns:
            ChapterGroup: 包含生成的提示词的章节组
            
        Raises:
            Exception: 当LLM调用失败时抛出异常
        """
        if ctx is None:
            ctx = AIContext()

        ctx.add_system_prompt(GEN_P_SYS)
        rendered_prompt = gen_p_user_template.render(
            chapter_name=chapter_group.chapter_name,
            reason=chapter_group.reason,
            qas=chapter_group.qas,
            extra_instructions=extra_instructions)
        ctx.add_user_prompt(rendered_prompt)

        prompt_val = await self.llm_client.ask(messages=ctx.to_openai_format(),
                                               temperature=0.3)
        chapter_group.prompt = prompt_val

        return chapter_group

    async def backward(
        self,
        qas: List[Tuple[str, str]],
        chapters_extra_instructions: str = "",
        gen_p_extra_instructions: str = "",
    ) -> Tuple[List[ChapterGroup], List[OSPA]]:
        """完整的反向知识处理工作流
        
        这是服务的主要入口方法，执行完整的知识结构化处理流程：
        1. 将问答对聚合成语义相关的章节
        2. 为每个章节生成专用的辅助提示词
        
        Args:
            qas (List[Tuple[str, str]]): 问答对列表，每个元组包含(问题, 答案)
            chapters_extra_instructions (str, optional): 章节聚合的额外指令. Defaults to "".
            gen_p_extra_instructions (str, optional): 提示词生成的额外指令. Defaults to "".
            
        Returns:
            List[ChapterGroup]: 处理完成的章节组列表，每个章节都包含辅助提示词
            
        Raises:
            Exception: 当任何步骤失败时抛出异常
            
        Example:
            >>> service = BackwardService(llm_client)
            >>> qas = [("Python如何定义变量？", "使用赋值语句定义变量")]
            >>> chapters = await service.backward(qas)
            >>> print(f"生成了 {len(chapters)} 个章节")
        """
        logger.info(f"开始反向知识处理，输入 {len(qas)} 个问答对")

        # 第一步：章节聚合
        ctx = AIContext()
        logger.debug("执行章节聚合...")
        agg_chapter_groups = await self._aggregate_chapters(
            qas, extra_instructions=chapters_extra_instructions, ctx=ctx)

        logger.info(f"章节聚合完成，生成了 {len(agg_chapter_groups)} 个章节")

        # 第二步：并行生成每个章节的提示词
        logger.debug("开始为各章节生成辅助提示词...")
        tasks = [
            self._generate_chapter_prompt(
                chapter_group,
                extra_instructions=gen_p_extra_instructions,
                ctx=AIContext()  # 为每个任务创建独立的上下文
            ) for chapter_group in agg_chapter_groups
        ]

        chapter_groups = await asyncio.gather(*tasks)

        logger.info(f"反向知识处理完成，共生成 {len(chapter_groups)} 个完整章节")

        ospa = chapters_to_ospa(chapter_groups)
        return chapter_groups, ospa
