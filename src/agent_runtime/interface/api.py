from typing import List, Dict
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel

from agent_runtime.services.reward_service import RewardService, RewardRusult
from agent_runtime.clients.llm.openai_client import LLM
from agent_runtime.config.loader import SettingLoader, LLMSetting
from agent_runtime.services.backward_service import BackwardService, ChapterGroup, OSPA

router = APIRouter()


class RewardRequest(BaseModel):
    question: str
    candidates: List[str]
    target_answer: str


llm_client = LLM()
reward_service = RewardService(llm_client)
backward_service = BackwardService(llm_client)


@router.get("/config")
async def get_config() -> dict:
    """获取当前的 LLM 配置"""
    try:
        config = SettingLoader.get_llm_setting()
        return config.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取配置失败: {e}")


@router.post("/config")
async def set_config(cfg: LLMSetting = Body(
    ...,
    openapi_examples={
        "deepseek_example": {
            "summary": "配置 DeepSeek-Chat 模型",
            "description": "使用 DeepSeek Chat 模型及 API Key 的示例",
            "value": {
                "api_key": "your_key",
                "model": "deepseek-chat",
                "base_url": "https://api.deepseek.com/v1",
                "timeout": 180.0,
                "max_completion_tokens": 2048,
                "temperature": 0
            },
        }
    },
)) -> dict:
    """
    设置 LLM 配置，并更新全局 llm_client backward_service 和 reward_service
    """
    try:
        new_cfg = SettingLoader.set_llm_setting(
            cfg.model_dump(exclude_none=True))
        global llm_client, reward_service, backward_service
        # 重新构建 LLM 客户端 (简化为使用默认构造函数，内部读取新的 SettingLoader 配置)
        llm_client = LLM(llm_setting=new_cfg)
        reward_service = RewardService(llm_client)
        backward_service = BackwardService(llm_client)
        return {"message": "配置已更新", "config": new_cfg.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新配置失败: {e}")


@router.post("/reward")
async def reward_api(request: RewardRequest = Body(
    ...,
    openapi_examples={
        "simple_example": {
            "summary": "简单示例 - 地理题",
            "description": "一个包含五个候选答案的简单例子",
            "value": {
                "question": "世界上最大的海洋是哪个？",
                "candidates": ["大西洋", "太平洋", "印度洋", "北冰洋", "地中海"],
                "target_answer": "太平洋"
            },
        },
        "complex_example": {
            "summary": "复杂示例 - 阅读理解",
            "description": "一个带有五个候选长文本答案的复杂语义比较例子",
            "value": {
                "question":
                "请总结《西游记》中唐僧西天取经的目的。",
                "candidates": [
                    "唐僧带领孙悟空、猪八戒、沙僧历经九九八十一难前往西天取经，为了取得真经。",
                    "唐僧此行是因为皇帝派遣他寻找宝物。", "取经的最终目的，是为了获取佛经，弘扬佛法，普度众生。",
                    "唐僧和徒弟们一路降妖除魔，实际上是为了打败妖怪获得宝藏。", "这个故事主要讲述了团队合作、修行和坚持不懈的精神。"
                ],
                "target_answer":
                "唐僧此次取经的真正目的，是为了弘扬佛法，普度众生。"
            },
        },
    },
)) -> RewardRusult:
    """
    Reward API: 比较多个答案的语义一致性

    你可以在 FastAPI docs (/docs) 中选择示例请求体，快速测试。
    """
    try:
        result = await reward_service.compare_answer(
            question=request.question,
            candidates=request.candidates,
            target_answer=request.target_answer,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reward API 调用失败: {e}")


# ======================= Backward API ==========================
class QAItem(BaseModel):
    """问答对数据模型（API用）
    
    Attributes:
        q (str): 问题内容
        a (str): 答案内容
    """
    q: str
    a: str


class BackwardRequest(BaseModel):
    """反向知识处理请求模型
    
    Attributes:
        qas (List[QAItem]): 问答对列表
        chapters_extra_instructions (str, optional): 章节聚合的额外指令
        gen_p_extra_instructions (str, optional): 提示词生成的额外指令
    """
    qas: List[QAItem]
    chapters_extra_instructions: str = ""
    gen_p_extra_instructions: str = ""


class BackwardResponse(BaseModel):
    """反向知识处理响应模型
    
    Attributes:
        success (bool): 处理是否成功
        message (str): 处理消息
        chapters (Dict[str, ChapterGroup]): 章节名称到章节对象的映射
        ospa (List[OSPA]): 转换后的OSPA格式数据列表
        total_chapters (int): 生成的章节总数
        total_qas (int): 输入的问答对总数
        total_ospa (int): 生成的OSPA条目总数
        processing_time_ms (int): 处理耗时（毫秒）
    """
    success: bool
    message: str
    chapters: Dict[str, ChapterGroup]
    ospa: List[OSPA]
    total_chapters: int
    total_qas: int
    total_ospa: int
    processing_time_ms: int


@router.post("/backward", response_model=BackwardResponse)
async def backward_api(req: BackwardRequest = Body(
    ...,
    openapi_examples={
        "simple_example": {
            "summary": "简单示例 - Python基础",
            "description": "包含几个Python基础问题的简单示例",
            "value": {
                "qas": [{
                    "q": "Python如何定义变量？",
                    "a": "在Python中使用赋值语句定义变量，如 x = 10"
                }, {
                    "q": "Python如何定义函数？",
                    "a": "使用def关键字定义函数，如 def func_name():"
                }, {
                    "q": "什么是Python列表？",
                    "a": "列表是Python中的可变序列，使用[]定义"
                }],
                "chapters_extra_instructions":
                "请将Python相关的问题聚合到一个章节",
                "gen_p_extra_instructions":
                "生成专业的Python技术文档风格提示词"
            }
        },
        "comprehensive_example": {
            "summary": "综合示例 - 多技术栈",
            "description": "包含多个技术领域问题的综合示例",
            "value": {
                "qas": [{
                    "q": "Python如何定义变量？",
                    "a": "在Python中使用赋值语句定义变量"
                }, {
                    "q": "什么是RESTful API？",
                    "a": "RESTful API是遵循REST架构风格的Web服务接口"
                }, {
                    "q": "什么是数据库索引？",
                    "a": "索引是提高数据库查询效率的数据结构"
                }, {
                    "q": "什么是时间复杂度？",
                    "a": "时间复杂度描述算法执行时间与输入规模的关系"
                }, {
                    "q": "什么是版本控制？",
                    "a": "版本控制是管理代码变更历史的系统"
                }],
                "chapters_extra_instructions":
                "按技术领域分类，每个章节包含2-3个相关问答",
                "gen_p_extra_instructions":
                "为每个技术领域生成专业、准确的技术文档风格提示词"
            }
        }
    })) -> BackwardResponse:
    """
    反向知识处理API
    
    将问答对聚合成有意义的章节结构，并为每个章节生成辅助提示词。
    这些提示词可用于指导后续的问答生成和知识检索。
    
    主要功能：
    1. 语义聚合：将相关的Q&A按主题聚合成章节
    2. 提示词生成：为每个章节生成专用的辅助提示词
    3. 知识结构化：提供完整的知识组织结构
    4. OSPA转换：将结构化数据转换为标准OSPA格式
    
    适用场景：
    - 知识库构建和组织
    - 智能问答系统优化
    - 技术文档结构化处理
    - 教学内容章节规划
    
    Returns:
        BackwardResponse: 包含处理结果的详细信息，包括章节、OSPA数据和统计信息
        
    Raises:
        HTTPException: 当输入验证失败或处理过程中发生错误时
    """
    # 输入验证
    if not req.qas:
        raise HTTPException(status_code=400, detail="问答对列表不能为空")
    
    if len(req.qas) > 100:  # 设置合理的上限
        raise HTTPException(status_code=400, detail="问答对数量不能超过100个")
    
    # 验证问答对内容
    for i, qa in enumerate(req.qas):
        if not qa.q.strip():
            raise HTTPException(status_code=400, detail=f"第{i+1}个问答对的问题不能为空")
        if not qa.a.strip():
            raise HTTPException(status_code=400, detail=f"第{i+1}个问答对的答案不能为空")
        if len(qa.q) > 1000:
            raise HTTPException(status_code=400, detail=f"第{i+1}个问题长度不能超过1000字符")
        if len(qa.a) > 2000:
            raise HTTPException(status_code=400, detail=f"第{i+1}个答案长度不能超过2000字符")
    
    import time
    start_time = time.time()
    
    try:
        # 调用BackwardService处理
        chapter_groups, ospa = await backward_service.backward(
            qas=[(qa.q, qa.a) for qa in req.qas],
            chapters_extra_instructions=req.chapters_extra_instructions,
            gen_p_extra_instructions=req.gen_p_extra_instructions)

        # 计算处理时间
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        return BackwardResponse(
            success=True,
            message=f"成功处理 {len(req.qas)} 个问答对，生成 {len(chapter_groups)} 个章节",
            chapters={
                chapter.chapter_name: chapter
                for chapter in chapter_groups
            },
            ospa=ospa,
            total_chapters=len(chapter_groups),
            total_qas=len(req.qas),
            total_ospa=len(ospa),
            processing_time_ms=processing_time_ms)
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"输入数据格式错误: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"反向知识处理失败: {str(e)}")
