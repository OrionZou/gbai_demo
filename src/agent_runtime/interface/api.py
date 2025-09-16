import time
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Body

from agent_runtime.services.reward_service import RewardService, RewardRusult
from agent_runtime.clients.openai_llm_client import LLM
from agent_runtime.config.loader import SettingLoader, LLMSetting
from agent_runtime.services.backward_service import BackwardService
from agent_runtime.services.agent_prompt_service import (
    AgentPromptService, AgentPromptInfo, AgentPromptUpdate
)
from agent_runtime.services.bqa_extract_service import BQAExtractService

# 导入核心数据结构
from agent_runtime.data_format import (
    ChapterStructure, OSPA, QAItem, QAList, BQAExtractRequest, BQAExtractResponse
)

# 导入API模型
from agent_runtime.interface.api_models import (
    LLMAskRequest, LLMAskResponse, RewardRequest, BackwardRequest, BackwardResponse
)

router = APIRouter()


@router.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "service": "agent_runtime"}


# API模型已移动到 interface.api_models 中


llm_client = LLM()
reward_service = RewardService(llm_client)
backward_service = BackwardService(llm_client)
agent_prompt_service = AgentPromptService(llm_client)
bqa_extract_service = BQAExtractService(llm_client)


@router.get("/config")
async def get_config() -> dict:
    """获取当前的 LLM 配置"""
    try:
        config = SettingLoader.get_llm_setting()
        return config.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取配置失败: {e}")


@router.get("/config/agents")
async def get_agents_status() -> dict:
    """获取所有Agent实例的状态信息"""
    try:
        from agent_runtime.agents.base import BaseAgent
        
        agent_instances_info = BaseAgent.get_all_agent_instances()
        current_config = SettingLoader.get_llm_setting()
        
        return {
            "current_llm_config": {
                "model": current_config.model,
                "api_key": current_config.api_key[:8] + "..." if current_config.api_key else "None",
                "base_url": current_config.base_url,
                "temperature": current_config.temperature
            },
            "total_agents": len(agent_instances_info),
            "agent_instances": agent_instances_info,
            "services_status": {
                "reward_service": {
                    "llm_model": getattr(reward_service.llm_client, 'model', 'unknown')
                },
                "backward_service": {
                    "llm_model": getattr(backward_service.llm_client, 'model', 'unknown')  
                },
                "agent_prompt_service": {
                    "llm_model": getattr(agent_prompt_service.llm_client, 'model', 'unknown')
                },
                "bqa_extract_service": {
                    "llm_model": getattr(bqa_extract_service.llm_client, 'model', 'unknown')
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取Agent状态失败: {e}")


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
    设置 LLM 配置，并更新全局 llm_client、所有services 和所有Agent实例
    """
    try:
        # 导入BaseAgent类用于更新所有Agent实例
        from agent_runtime.agents.base import BaseAgent
        
        new_cfg = SettingLoader.set_llm_setting(
            cfg.model_dump(exclude_none=True))
        global llm_client, reward_service, backward_service, agent_prompt_service, bqa_extract_service
        
        # 重新构建 LLM 客户端
        llm_client = LLM(llm_setting=new_cfg)
        
        # 更新所有已存在的Agent实例的LLM引擎
        BaseAgent.update_all_agents_llm_engine(llm_client)
        
        # 重新构建所有services
        reward_service = RewardService(llm_client)
        backward_service = BackwardService(llm_client)
        agent_prompt_service = AgentPromptService(llm_client)
        bqa_extract_service = BQAExtractService(llm_client)
        
        # 获取更新后的Agent实例信息
        agent_instances_info = BaseAgent.get_all_agent_instances()
        
        return {
            "message": "配置已更新，所有services和agent实例已同步更新", 
            "config": new_cfg.model_dump(),
            "updated_agents": len(agent_instances_info),
            "agent_instances": agent_instances_info
        }
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
# API模型已移动到 interface.api_models 中


@router.post("/backward", response_model=BackwardResponse)
async def backward_api(req: BackwardRequest = Body(
    ...,
    openapi_examples={
        "simple_example": {
            "summary": "简单示例 - Python基础",
            "description": "包含几个Python基础问题的简单示例",
            "value": {
                "qas": [{
                    "question": "Python如何定义变量？",
                    "answer": "在Python中使用赋值语句定义变量，如 x = 10"
                }, {
                    "question": "Python如何定义函数？",
                    "answer": "使用def关键字定义函数，如 def func_name():"
                }, {
                    "question": "什么是Python列表？",
                    "answer": "列表是Python中的可变序列，使用[]定义"
                }],
                "max_level": 3,
                "max_concurrent_llm": 10
            }
        },
        "comprehensive_example": {
            "summary": "综合示例 - 多技术栈",
            "description": "包含多个技术领域问题的综合示例",
            "value": {
                "qas": [{
                    "question": "Python如何定义变量？",
                    "answer": "在Python中使用赋值语句定义变量"
                }, {
                    "question": "什么是RESTful API？",
                    "answer": "RESTful API是遵循REST架构风格的Web服务接口"
                }, {
                    "question": "什么是数据库索引？",
                    "answer": "索引是提高数据库查询效率的数据结构"
                }, {
                    "question": "什么是时间复杂度？",
                    "answer": "时间复杂度描述算法执行时间与输入规模的关系"
                }, {
                    "question": "什么是版本控制？",
                    "answer": "版本控制是管理代码变更历史的系统"
                }],
                "chapter_structure": {
                    "nodes": {
                        "chapter_1": {
                            "id": "chapter_1",
                            "title": "编程基础",
                            "level": 1,
                            "parent_id": None,
                            "children": [],
                            "description": "基础编程概念",
                            "content": "",
                            "related_qa_items": [],
                            "chapter_number": "1."
                        }
                    },
                    "root_ids": ["chapter_1"],
                    "max_level": 3
                },
                "max_level": 3,
                "max_concurrent_llm": 10
            }
        }
    })) -> BackwardResponse:
    """
    反向知识处理API
    
    处理问答对生成或更新章节结构，并为每个章节生成辅助提示词。
    这些提示词可用于指导后续的问答生成和知识检索。
    
    主要功能：
    1. 章节创建或更新：根据是否提供现有章节结构选择不同处理策略
    2. 智能提示词生成：只为新增或变化的章节生成提示词，保留现有提示词
    3. 知识结构化：提供完整的知识组织结构
    4. OSPA转换：将结构化数据转换为标准OSPA格式
    
    处理策略：
    - 无现有章节结构：使用chapter_structure_agent创建新结构
    - 有现有章节结构：使用chapter_classification_agent更新结构
    
    适用场景：
    - 知识库构建和增量更新
    - 智能问答系统优化
    - 技术文档结构化处理
    - 教学内容章节规划
    
    Returns:
        BackwardResponse: 包含处理结果的详细信息，包括章节结构、OSPA数据和统计信息
        
    Raises:
        HTTPException: 当输入验证失败或处理过程中发生错误时
    """
    # 输入验证
    if not req.qas:
        raise HTTPException(status_code=400, detail="问答对列表不能为空")
    
    if len(req.qas) > 100:  # 设置最大长度为100
        raise HTTPException(status_code=400, detail="问答对数量不能超过100个")
    
    # 验证问答对内容
    for i, qa in enumerate(req.qas):
        if not qa.question.strip():
            raise HTTPException(status_code=400, detail=f"第{i+1}个问答对的问题不能为空")
        if not qa.answer.strip():
            raise HTTPException(status_code=400, detail=f"第{i+1}个问答对的答案不能为空")
        if len(qa.question) > 1000:
            raise HTTPException(status_code=400, detail=f"第{i+1}个问题长度不能超过1000字符")
        if len(qa.answer) > 2000:
            raise HTTPException(status_code=400, detail=f"第{i+1}个答案长度不能超过2000字符")
    
    # 验证新参数
    if req.max_level < 1 or req.max_level > 5:
        raise HTTPException(status_code=400, detail="最大层级必须在1-5之间")
    
    if req.max_concurrent_llm < 1 or req.max_concurrent_llm > 20:
        raise HTTPException(status_code=400, detail="最大并发LLM数量必须在1-20之间")
    
    import time
    start_time = time.time()
    
    try:
        # 构建QAList
        qa_list = QAList(session_id="api_request")
        for qa in req.qas:
            qa_list.add_qa(qa.question, qa.answer)
        
        # 处理可选的章节结构
        existing_structure = None
        if req.chapter_structure:
            existing_structure = ChapterStructure.from_dict(
                req.chapter_structure, max_level=req.max_level
            )
        
        # 调用BackwardService处理
        final_structure, ospa = await backward_service.backward(
            qa_list=qa_list,
            chapter_structure=existing_structure,
            max_level=req.max_level,
            max_concurrent_llm=req.max_concurrent_llm
        )

        # 计算处理时间
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # 返回playground期望的格式
        chapter_structure_dict = {
            "nodes": {},
            "root_ids": final_structure.root_ids,
            "max_level": final_structure.max_level
        }
        
        # 序列化节点数据，保持扁平结构
        for node_id, node in final_structure.nodes.items():
            chapter_structure_dict["nodes"][node_id] = {
                "id": node.id,
                "title": node.title,
                "level": node.level,
                "parent_id": node.parent_id,
                "children": node.children,
                "description": node.description,
                "reason": node.reason,
                "content": node.content,
                "related_qa_items": [
                    {
                        "question": qa.question,
                        "answer": qa.answer,
                        "metadata": qa.metadata
                    } for qa in node.related_qa_items
                ],
                "chapter_number": node.chapter_number
            }
        
        return BackwardResponse(
            success=True,
            message=f"成功处理 {len(req.qas)} 个问答对，生成 {len(final_structure.nodes)} 个章节",
            chapter_structure=chapter_structure_dict,
            ospa=ospa,
            total_chapters=len(final_structure.nodes),
            total_qas=len(req.qas),
            total_ospa=len(ospa),
            processing_time_ms=processing_time_ms
        )
            
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


# ======================= BQA Extract API ==========================


@router.post("/bqa/extract", response_model=BQAExtractResponse)
async def extract_bqa_from_conversations(request: BQAExtractRequest = Body(
    ...,
    openapi_examples={
        "simple_example": {
            "summary": "简单示例 - 多轮对话拆解",
            "description": "将多个多轮对话拆解为独立的BQA内容",
            "value": {
                "qa_lists": [
                    {
                        "items": [
                            {"question": "什么是Python？", "answer": "Python是一种高级编程语言"},
                            {"question": "它有什么特点？", "answer": "Python具有简洁易读、功能强大等特点"},
                            {"question": "如何安装它？", "answer": "可以从官网下载安装包或使用包管理器安装Python"}
                        ],
                        "session_id": "python_intro"
                    },
                    {
                        "items": [
                            {"question": "什么是机器学习？", "answer": "机器学习是人工智能的一个分支"},
                            {"question": "常用算法有哪些？", "answer": "包括线性回归、决策树、神经网络等"},
                            {"question": "怎么开始学习？", "answer": "建议先学习基础数学和编程，然后学习算法原理"}
                        ],
                        "session_id": "ml_intro"
                    }
                ],
                "context_extraction_mode": "auto",
                "preserve_session_info": True,
                "max_concurrent_processing": 2
            }
        },
        "minimal_mode": {
            "summary": "最小化模式 - 只在必要时添加背景",
            "description": "只在问题明确依赖前面内容时才添加背景信息",
            "value": {
                "qa_lists": [
                    {
                        "items": [
                            {"question": "什么是RESTful API？", "answer": "RESTful API是一种网络应用程序的设计风格"},
                            {"question": "它的优点是什么？", "answer": "具有简单、可扩展、无状态等优点"},
                            {"question": "如何设计？", "answer": "需要遵循REST架构原则，使用标准HTTP方法"}
                        ],
                        "session_id": "api_design"
                    }
                ],
                "context_extraction_mode": "minimal",
                "preserve_session_info": True,
                "max_concurrent_processing": 1
            }
        },
        "detailed_mode": {
            "summary": "详细模式 - 丰富的背景信息",
            "description": "为每个问题提供详细的背景信息，确保独立理解",
            "value": {
                "qa_lists": [
                    {
                        "items": [
                            {"question": "什么是Docker？", "answer": "Docker是一种容器化平台"},
                            {"question": "与虚拟机有什么区别？", "answer": "Docker更轻量，共享主机内核"},
                            {"question": "如何使用？", "answer": "通过Dockerfile定义镜像，然后运行容器"}
                        ],
                        "session_id": "docker_basics"
                    }
                ],
                "context_extraction_mode": "detailed",
                "preserve_session_info": True,
                "max_concurrent_processing": 1
            }
        }
    }
)) -> BQAExtractResponse:
    """
    BQA拆解接口 - 将多轮对话拆解为独立内容

    这个接口使用BQAAgent将多轮对话转换为带背景信息的独立问答对（BQA），
    使得每个问答对都包含必要的背景信息，可以独立理解和使用。

    主要功能：
    1. 多轮对话分析：分析对话中问题之间的依赖关系
    2. 背景信息提取：为需要的问题添加背景信息
    3. 独立性转换：确保每个BQA可以独立理解
    4. 并发处理：支持多个对话会话的并发处理

    提取模式：
    - auto: 智能判断是否需要背景信息
    - minimal: 只在必要时添加最少的背景信息
    - detailed: 为大部分问题提供详细的背景信息

    适用场景：
    - 知识库内容准备：将对话内容转换为可独立使用的知识条目
    - 问答系统训练：为训练数据添加上下文信息
    - 内容重组：将连续对话拆解为独立的信息单元
    - 搜索索引：创建可独立搜索的内容条目

    Args:
        request: BQAExtractRequest 包含多轮对话列表和处理参数

    Returns:
        BQAExtractResponse: 包含拆解后的BQA内容和处理统计

    Raises:
        HTTPException: 当输入验证失败或处理过程中发生错误时
    """
    # 输入验证
    if not request.qa_lists:
        raise HTTPException(status_code=400, detail="对话列表不能为空")

    if len(request.qa_lists) > 50:  # 设置合理的会话上限
        raise HTTPException(status_code=400, detail="对话会话数量不能超过50个")

    # 验证每个对话会话
    total_qas = 0
    for i, qa_list in enumerate(request.qa_lists):
        if not qa_list.items:
            raise HTTPException(status_code=400, detail=f"第{i+1}个对话会话不能为空")

        if len(qa_list.items) > 100:  # 单个会话的QA对上限
            raise HTTPException(status_code=400, detail=f"第{i+1}个对话会话的问答对不能超过100个")

        # 验证问答对内容
        for j, qa in enumerate(qa_list.items):
            if not qa.question.strip():
                raise HTTPException(status_code=400, detail=f"第{i+1}个会话第{j+1}个问题不能为空")
            if not qa.answer.strip():
                raise HTTPException(status_code=400, detail=f"第{i+1}个会话第{j+1}个答案不能为空")
            if len(qa.question) > 2000:
                raise HTTPException(status_code=400, detail=f"第{i+1}个会话第{j+1}个问题长度不能超过2000字符")
            if len(qa.answer) > 4000:
                raise HTTPException(status_code=400, detail=f"第{i+1}个会话第{j+1}个答案长度不能超过4000字符")

        total_qas += len(qa_list.items)

    if total_qas > 500:  # 总问答对数量限制
        raise HTTPException(status_code=400, detail=f"总问答对数量不能超过500个，当前{total_qas}个")

    import time
    start_time = time.time()

    try:
        # 调用BQA拆解服务
        response: BQAExtractResponse = await bqa_extract_service.extract_bqa_from_conversations(request)

        # 计算总处理时间
        total_time = int((time.time() - start_time) * 1000)
        response.total_processing_time_ms = total_time

        # 添加API调用信息到操作日志
        response.operation_log.insert(0, f"API调用开始，处理 {len(request.qa_lists)} 个对话会话")
        response.operation_log.append(f"API调用完成，总耗时: {total_time}ms")

        return response

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"输入数据格式错误: {str(e)}")
    except Exception as e:
        import traceback
        error_detail = f"BQA拆解处理失败: {str(e)}"
        # 在开发环境中可以添加详细错误信息
        # error_detail += f"\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)


