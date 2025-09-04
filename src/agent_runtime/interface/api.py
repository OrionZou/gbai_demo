import time
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field

from agent_runtime.services.reward_service import RewardService, RewardRusult
from agent_runtime.clients.llm.openai_client import LLM
from agent_runtime.config.loader import SettingLoader, LLMSetting
from agent_runtime.services.backward_service import BackwardService, ChapterGroup, OSPA
from agent_runtime.services.backward_v2_service import BackwardV2Service
from agent_runtime.services.agent_prompt_service import (
    AgentPromptService, AgentPromptInfo, AgentPromptUpdate
)
from agent_runtime.data_format.backward_v2_format import BackwardV2Request, BackwardV2Response
from agent_runtime.data_format.qa_format import QAItem as QAItemData, QAList

router = APIRouter()


@router.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "service": "agent_runtime"}


class RewardRequest(BaseModel):
    question: str
    candidates: List[str]
    target_answer: str


class LLMAskRequest(BaseModel):
    """LLM Ask API 请求模型
    
    Attributes:
        messages (List[Dict[str, Any]]): 消息列表，遵循 OpenAI 格式
        stream (Optional[bool]): 是否启用流式输出，默认使用配置中的设置
        temperature (Optional[float]): 生成温度，范围 0.0-2.0，默认使用配置中的设置
    """
    messages: List[Dict[str, Any]] = Field(
        ...,
        description="消息列表，每个消息包含 role 和 content 字段",
        min_items=1
    )
    stream: Optional[bool] = Field(
        None,
        description="是否启用流式输出"
    )
    temperature: Optional[float] = Field(
        None,
        description="生成温度，控制输出的随机性",
        ge=0.0,
        le=2.0
    )


class LLMAskResponse(BaseModel):
    """LLM Ask API 响应模型
    
    Attributes:
        success (bool): 请求是否成功
        message (str): 响应消息或错误信息
        content (Optional[str]): LLM 生成的内容
        model (str): 使用的模型名称
        processing_time_ms (int): 处理耗时（毫秒）
    """
    success: bool
    message: str
    content: Optional[str] = None
    model: str
    processing_time_ms: int


llm_client = LLM()
reward_service = RewardService(llm_client)
backward_service = BackwardService(llm_client)
backward_v2_service = BackwardV2Service(llm_client)
agent_prompt_service = AgentPromptService(llm_client)


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
        global llm_client, reward_service, backward_service, backward_v2_service, agent_prompt_service
        # 重新构建 LLM 客户端 (简化为使用默认构造函数，内部读取新的 SettingLoader 配置)
        llm_client = LLM(llm_setting=new_cfg)
        reward_service = RewardService(llm_client)
        backward_service = BackwardService(llm_client)
        backward_v2_service = BackwardV2Service(llm_client)
        agent_prompt_service = AgentPromptService(llm_client)
        return {"message": "配置已更新", "config": new_cfg.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新配置失败: {e}")


@router.post("/llm/ask", response_model=LLMAskResponse)
async def llm_ask_api(request: LLMAskRequest = Body(
    ...,
    openapi_examples={
        "simple_question": {
            "summary": "简单问答示例",
            "description": "一个简单的单轮对话示例",
            "value": {
                "messages": [
                    {
                        "role": "user",
                        "content": "什么是人工智能？"
                    }
                ],
                "temperature": 0.7
            }
        },
        "multi_turn_conversation": {
            "summary": "多轮对话示例",
            "description": "包含系统提示和多轮对话的示例",
            "value": {
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个专业的Python编程助手。"
                    },
                    {
                        "role": "user",
                        "content": "如何在Python中创建一个列表？"
                    },
                    {
                        "role": "assistant",
                        "content": "在Python中，你可以用方括号[]创建列表，例如：my_list = [1, 2, 3]"
                    },
                    {
                        "role": "user",
                        "content": "如何向列表中添加元素？"
                    }
                ],
                "temperature": 0.3,
                "stream": False
            }
        },
        "creative_writing": {
            "summary": "创意写作示例",
            "description": "使用较高温度进行创意写作的示例",
            "value": {
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个创意写作助手，擅长编写有趣的故事。"
                    },
                    {
                        "role": "user",
                        "content": "请写一个关于机器人和人类友谊的短故事开头。"
                    }
                ],
                "temperature": 1.2,
                "stream": True
            }
        }
    }
)) -> LLMAskResponse:
    """
    LLM Ask API: 与语言模型进行对话
    
    这个API允许你与配置的语言模型进行对话，支持单轮和多轮对话。
    
    主要功能：
    1. 单轮问答：发送单个问题获取回答
    2. 多轮对话：维护对话历史进行连续交流
    3. 系统提示：使用系统角色设定模型行为
    4. 温度控制：调节回答的创造性和随机性
    5. 流式输出：支持实时流式响应（可选）
    
    参数说明：
    - messages: 遵循OpenAI格式的消息列表，每个消息包含role（系统/用户/助手）和content
    - temperature: 0.0-2.0，数值越高输出越有创造性，越低越确定性
    - stream: 是否启用流式输出
    
    适用场景：
    - 问答系统
    - 对话机器人
    - 内容生成
    - 代码助手
    - 创意写作
    
    你可以在 FastAPI docs (/docs) 中选择示例请求体，快速测试不同场景。
    
    Returns:
        LLMAskResponse: 包含生成内容和处理信息的响应
        
    Raises:
        HTTPException: 当输入验证失败或LLM调用出错时
    """
    # 输入验证
    if not request.messages:
        raise HTTPException(status_code=400, detail="消息列表不能为空")
    
    if len(request.messages) > 50:  # 合理的消息数量限制
        raise HTTPException(status_code=400, detail="消息数量不能超过50条")
    
    # 验证消息格式
    for i, msg in enumerate(request.messages):
        if not isinstance(msg, dict):
            raise HTTPException(status_code=400, detail=f"第{i+1}条消息格式错误，应为字典")
        
        if "role" not in msg or "content" not in msg:
            raise HTTPException(status_code=400, detail=f"第{i+1}条消息缺少必需字段 'role' 或 'content'")
        
        if msg["role"] not in ["system", "user", "assistant"]:
            raise HTTPException(status_code=400, detail=f"第{i+1}条消息的role无效，应为 'system', 'user' 或 'assistant'")
        
        if not isinstance(msg["content"], str) or not msg["content"].strip():
            raise HTTPException(status_code=400, detail=f"第{i+1}条消息的content不能为空")
        
        if len(msg["content"]) > 10000:  # 单条消息长度限制
            raise HTTPException(status_code=400, detail=f"第{i+1}条消息内容长度不能超过10000字符")
    
    start_time = time.time()
    
    try:
        # 调用LLM ask方法
        content = await llm_client.ask(
            messages=request.messages,
            stream=request.stream,
            temperature=request.temperature
        )
        
        # 计算处理时间
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        return LLMAskResponse(
            success=True,
            message="LLM调用成功",
            content=content,
            model=llm_client.model,
            processing_time_ms=processing_time_ms
        )
        
    except ValueError as e:
        processing_time_ms = int((time.time() - start_time) * 1000)
        raise HTTPException(status_code=400, detail=f"输入参数错误: {str(e)}")
    except Exception as e:
        processing_time_ms = int((time.time() - start_time) * 1000)
        raise HTTPException(status_code=500, detail=f"LLM调用失败: {str(e)}")


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


# ======================= Agent Prompt Management APIs ==========================







@router.get("/agents/names")
async def get_supported_agent_names() -> List[str]:
    """
    获取所有支持的Agent名称
    
    Returns:
        List[str]: 支持的Agent名称列表
    """
    try:
        return agent_prompt_service.get_supported_agent_names()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取Agent名称失败: {e}")




@router.get("/agents/{agent_name}/prompts")
async def get_agent_prompts(agent_name: str) -> AgentPromptInfo:
    """
    获取指定Agent的提示词信息
    
    Args:
        agent_name: Agent名称
        
    Returns:
        AgentPromptInfo: Agent提示词信息
    """
    try:
        # 验证agent_name是否有效
        supported_agents = agent_prompt_service.get_supported_agent_names()
        if agent_name not in supported_agents:
            raise HTTPException(
                status_code=400,
                detail=f"无效的Agent名称: {agent_name}，支持的名称: {supported_agents}"
            )
        
        return agent_prompt_service.get_agent_prompt_info(agent_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取Agent提示词失败: {e}")


@router.put("/agents/{agent_name}/prompts")
async def update_agent_prompts(
    agent_name: str,
    request: AgentPromptUpdate = Body(
        ...,
        openapi_examples={
            "update_system_prompt": {
                "summary": "更新系统提示词",
                "description": "只更新RewardAgent的系统提示词",
                "value": {
                    "system_prompt": "你是改进版的答案一致性评审器，请更仔细地分析每个候选答案的语义匹配度。"
                }
            },
            "update_user_template": {
                "summary": "更新用户模板",
                "description": "只更新RewardAgent的用户提示词模板",
                "value": {
                    "user_prompt_template": "问题：{{ question }}\n\n目标答案：{{ target_answer }}\n\n请分析以下候选答案：\n{% for ans in candidates %}- {{ ans }}\n{% endfor %}"
                }
            },
            "update_both": {
                "summary": "同时更新系统提示词和用户模板",
                "description": "同时更新RewardAgent的系统提示词和用户模板",
                "value": {
                    "system_prompt": "你是专业的答案评审器，需要判断候选答案与目标答案的一致性。",
                    "user_prompt_template": "评审任务：\n问题：{{ question }}\n目标答案：{{ target_answer }}\n候选答案：\n{% for ans in candidates %}{{ loop.index }}. {{ ans }}\n{% endfor %}\n\n请给出评审结果。"
                }
            }
        }
    )
) -> AgentPromptInfo:
    """
    更新指定Agent的提示词
    
    Args:
        agent_name: Agent名称
        request: 更新请求
        
    Returns:
        AgentPromptInfo: 更新后的Agent提示词信息
    """
    try:
        # 验证agent_name是否有效
        supported_agents = agent_prompt_service.get_supported_agent_names()
        if agent_name not in supported_agents:
            raise HTTPException(
                status_code=400,
                detail=f"无效的Agent名称: {agent_name}，支持的名称: {supported_agents}"
            )
        
        return agent_prompt_service.update_agent_prompts(agent_name, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新Agent提示词失败: {e}")




@router.post("/agents/{agent_name}/prompts/reset")
async def reset_agent_prompts(agent_name: str) -> AgentPromptInfo:
    """
    重置指定Agent的提示词为默认值
    
    Args:
        agent_name: Agent名称
        
    Returns:
        AgentPromptInfo: 重置后的Agent提示词信息
    """
    try:
        # 验证agent_name是否有效
        supported_agents = agent_prompt_service.get_supported_agent_names()
        if agent_name not in supported_agents:
            raise HTTPException(
                status_code=400,
                detail=f"无效的Agent名称: {agent_name}，支持的名称: {supported_agents}"
            )
        
        return agent_prompt_service.reset_agent_to_default(agent_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重置Agent提示词失败: {e}")


@router.post("/agents/{agent_name}/prompts/validate")
async def validate_agent_template_variables(
    agent_name: str,
    request: Dict[str, Any] = Body(
        ...,
        openapi_examples={
            "reward_agent_validation": {
                "summary": "RewardAgent变量验证",
                "description": "验证RewardAgent需要的模板变量",
                "value": {
                    "question": "什么是Python？",
                    "target_answer": "Python是一种编程语言",
                    "candidates": ["Python是脚本语言", "Python是解释型语言", "Python是面向对象语言"]
                }
            }
        }
    )
) -> Dict[str, Any]:
    """
    验证Agent模板变量是否有效
    
    Args:
        agent_name: Agent名称
        request: 测试变量字典
        
    Returns:
        Dict[str, Any]: 验证结果，包含是否有效、缺失变量、多余变量和渲染预览
    """
    try:
        # 验证agent_name是否有效
        supported_agents = agent_prompt_service.get_supported_agent_names()
        if agent_name not in supported_agents:
            raise HTTPException(
                status_code=400,
                detail=f"无效的Agent名称: {agent_name}，支持的名称: {supported_agents}"
            )
        
        return agent_prompt_service.validate_template_variables(agent_name, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"验证模板变量失败: {e}")


# ======================= Backward V2 API ==========================

class QAListRequest(BaseModel):
    """QA列表请求模型（API用）"""
    items: List[QAItem]
    session_id: str = ""


@router.post("/backward_v2", response_model=BackwardV2Response)
async def backward_v2_api(request: BackwardV2Request = Body(
    ...,
    openapi_examples={
        "simple_example": {
            "summary": "简单示例 - 无现有章节目录",
            "description": "包含两个对话序列，无现有章节目录，需要生成新的章节结构",
            "value": {
                "qa_lists": [
                    {
                        "items": [
                            {"question": "Python如何定义变量？", "answer": "在Python中使用赋值语句定义变量，如 x = 10"},
                            {"question": "如何查看变量类型？", "answer": "使用type()函数可以查看变量类型，如 type(x)"}
                        ],
                        "session_id": "session_1"
                    },
                    {
                        "items": [
                            {"question": "什么是RESTful API？", "answer": "RESTful API是遵循REST架构风格的Web服务接口"},
                            {"question": "API设计有什么原则？", "answer": "API设计要遵循统一接口、无状态、可缓存等原则"}
                        ],
                        "session_id": "session_2"
                    }
                ],
                "max_level": 3
            }
        },
        "with_existing_chapters": {
            "summary": "复杂示例 - 有现有章节目录",
            "description": "包含现有章节目录，需要更新章节结构",
            "value": {
                "qa_lists": [
                    {
                        "items": [
                            {"question": "什么是Docker容器？", "answer": "Docker容器是轻量级的虚拟化技术"},
                            {"question": "容器与虚拟机的区别？", "answer": "容器共享宿主机内核，虚拟机有独立的操作系统"}
                        ],
                        "session_id": "session_3"
                    }
                ],
                "chapter_structure": {
                    "nodes": {
                        "chapter_1": {
                            "id": "chapter_1",
                            "title": "基础知识",
                            "level": 1,
                            "parent_id": None,
                            "children": [],
                            "description": "基础技术概念",
                            "related_cqa_items": [],
                            "related_cqa_ids": [],
                            "chapter_number": "1."
                        }
                    },
                    "root_ids": ["chapter_1"],
                    "max_level": 3
                },
                "max_level": 3
            }
        }
    }
)) -> BackwardV2Response:
    """
    Backward V2 API - 改进版的知识反向处理接口
    
    利用 cqa_agent、chapter_structure_agent、chapter_classification_agent 和 gen_chpt_p_agent 
    这四个专门的 agent 处理 Q&A 二维列表，生成章节目录和 OSPA。
    
    主要功能：
    1. Q&A 转 CQA：使用 cqa_agent 将问答对转换为带上下文的格式
    2. 章节构建或更新：
       - 无现有章节：使用 chapter_structure_agent 生成新章节目录
       - 有现有章节：使用 chapter_classification_agent 更新现有目录
    3. 提示词生成：使用 gen_chpt_p_agent 为每个章节生成专用提示词
    4. OSPA 转换：将最终结果转换为 OSPA 格式
    
    与 backward API 的区别：
    - backward_v2 支持多轮对话的二维列表输入
    - 支持现有章节目录的更新和分类
    - 使用更专业的 agent 进行处理
    - 提供更详细的操作日志
    
    适用场景：
    - 多轮对话知识库的构建
    - 现有知识结构的增量更新
    - 复杂知识体系的结构化处理
    - 教学内容的智能组织
    
    Args:
        request: BackwardV2Request 包含 Q&A 二维列表和可选的章节目录
        
    Returns:
        BackwardV2Response: 包含最终章节结构、OSPA 列表和操作日志
        
    Raises:
        HTTPException: 当输入验证失败或处理过程中发生错误时
    """
    # 输入验证
    if not request.qa_lists:
        raise HTTPException(status_code=400, detail="Q&A列表不能为空")
    
    if len(request.qa_lists) > 20:  # 设置合理的对话序列上限
        raise HTTPException(status_code=400, detail="对话序列数量不能超过20个")
    
    # 验证每个对话序列
    total_qas = 0
    for i, qa_list in enumerate(request.qa_lists):
        if not qa_list.items:
            raise HTTPException(status_code=400, detail=f"第{i+1}个对话序列不能为空")
        
        if len(qa_list.items) > 50:  # 单个对话序列的问答对上限
            raise HTTPException(status_code=400, detail=f"第{i+1}个对话序列的问答对不能超过50个")
        
        # 验证问答对内容
        for j, qa in enumerate(qa_list.items):
            if not qa.question.strip():
                raise HTTPException(status_code=400, detail=f"第{i+1}个对话序列第{j+1}个问题不能为空")
            if not qa.answer.strip():
                raise HTTPException(status_code=400, detail=f"第{i+1}个对话序列第{j+1}个答案不能为空")
            if len(qa.question) > 1000:
                raise HTTPException(status_code=400, detail=f"第{i+1}个对话序列第{j+1}个问题长度不能超过1000字符")
            if len(qa.answer) > 2000:
                raise HTTPException(status_code=400, detail=f"第{i+1}个对话序列第{j+1}个答案长度不能超过2000字符")
        
        total_qas += len(qa_list.items)
    
    if total_qas > 200:  # 总问答对数量限制
        raise HTTPException(status_code=400, detail=f"总问答对数量不能超过200个，当前{total_qas}个")
    
    # 验证最大层级
    if request.max_level < 1 or request.max_level > 5:
        raise HTTPException(status_code=400, detail="最大层级必须在1-5之间")
    
    import time
    start_time = time.time()
    
    try:
        # 调用 BackwardV2Service 处理
        response = await backward_v2_service.process(request)
        
        # 计算处理时间
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # 添加处理时间到操作日志
        response.operation_log.append(f"总处理时间: {processing_time_ms}ms")
        
        return response
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"输入数据格式错误: {str(e)}")
    except Exception as e:
        import traceback
        error_detail = f"Backward V2 处理失败: {str(e)}"
        # 在开发环境中可以添加详细错误信息
        # error_detail += f"\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)
