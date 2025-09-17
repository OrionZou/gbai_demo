from typing import List, Annotated
from fastapi import APIRouter, HTTPException, status, Body, Query
import json

from agent_runtime.services.chat_v1_5_service import ChatService
from agent_runtime.services.feedback_service import FeedbackService
from agent_runtime.clients.weaviate_client import WeaviateClient
from agent_runtime.clients.openai_embedding_client import OpenAIEmbeddingClient
from agent_runtime.interface.api_models import (
    ChatRequest,
    ChatResponse,
    Setting,
    LearnRequest,
    LearnResponse,
    FeedbackSetting,
)
from agent_runtime.data_format.feedback import Feedback
from agent_runtime.data_format.fsm import Memory

from agent_runtime.logging.logger import logger

router = APIRouter()


def _get_feedback_service(settings: FeedbackSetting) -> FeedbackService:
    """
    创建 FeedbackService 实例

    Args:
        settings: FeedbackSetting配置对象，包含向量数据库URL和嵌入API配置

    Returns:
        FeedbackService: 反馈服务实例
    """
    # 创建WeaviateClient
    weaviate_client = WeaviateClient(
        base_url=settings.vector_db_url,
        embedding_api_key=settings.embedding_api_key,
        timeout=30,
    )

    # 创建OpenAI嵌入客户端
    embedding_client = OpenAIEmbeddingClient(
        api_key=settings.embedding_api_key,
        model_name=settings.embedding_model,
        dimensions=settings.embedding_vector_dim,
        base_url=settings.embedding_base_url,
    )

    # 创建FeedbackService
    return FeedbackService(
        weaviate_client=weaviate_client, embedding_client=embedding_client
    )


def _get_chat_service(settings: Setting) -> ChatService:
    """
    创建 ChatService 实例

    Args:
        settings: 配置对象，包含LLM相关配置参数

    Returns:
        ChatService: 聊天服务实例
    """
    from agent_runtime.config.loader import LLMSetting
    from agent_runtime.clients.openai_llm_client import LLM

    # 创建LLM设置
    llm_setting = LLMSetting(
        model=settings.chat_model,
        base_url=settings.base_url,
        api_key=settings.api_key,
        temperature=settings.temperature,
        top_p=settings.top_p,
    )

    # 创建LLM引擎
    llm_engine = LLM(llm_setting=llm_setting)

    # 创建ChatService并传入LLM引擎
    chat_service = ChatService()

    # 更新agents的LLM引擎
    chat_service.update_agents_llm_engine(llm_engine)

    # 创建FeedbackSetting对象
    feedback_setting = FeedbackSetting(
        vector_db_url=settings.vector_db_url,
        agent_name=settings.agent_name,
        embedding_api_key=settings.embedding_api_key,
        embedding_model=settings.embedding_model,
        embedding_base_url=settings.embedding_base_url,
        embedding_vector_dim=settings.embedding_vector_dim,
        top_k=settings.top_k,
    )

    # 创建FeedbackService并链接到ChatService
    feedback_service = _get_feedback_service(feedback_setting)
    chat_service.link_feedback_service(feedback_service)

    return chat_service


@router.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def generate_chat(
    request: Annotated[
        ChatRequest,
        Body(
            openapi_examples={
                "openai_simple": {
                    "summary": "Simple Chat Example with OpenAI (String Format)",
                    "description": "Simple chat example with OpenAI using string format (backward compatible).",
                    "value": {
                        "user_message": "你好",
                        "edited_last_response": "",
                        "recall_last_user_message": False,
                        "settings": {
                            "api_key": "your_api_key",
                            "chat_model": "gpt-4o",
                            "base_url": "https://api.openai.com/v1/",
                            "top_p": 1.0,
                            "temperature": 1.0,
                            "top_k": 5,
                            "vector_db_url": "http://weaviate:8080",
                            "global_prompt": "你是一個專業的顧問，有耐心且親切地回答使用者任何問題，使用繁體中文:台灣。",
                            "max_history_len": 256,
                            "state_machine": {},
                            "agent_name": "TestAgent",
                        },
                        "memory": {
                            "history": [],
                        },
                        "request_tools": [],
                    },
                },
                "openai_chatml": {
                    "summary": "OpenAI Chat with ChatML Messages Format",
                    "description": "Chat example using ChatML format with multiple messages.",
                    "value": {
                        "user_message": [
                            {
                                "role": "system",
                                "content": "你是一个专业的AI助手，请用中文回答问题。",
                            },
                            {"role": "user", "content": "你好，请介绍一下你自己"},
                        ],
                        "edited_last_response": "",
                        "recall_last_user_message": False,
                        "settings": {
                            "api_key": "your_api_key",
                            "chat_model": "gpt-4o",
                            "base_url": "https://api.openai.com/v1/",
                            "top_p": 1.0,
                            "temperature": 1.0,
                            "top_k": 5,
                            "vector_db_url": "http://weaviate:8080",
                            "global_prompt": "你是一個專業的顧問，有耐心且親切地回答使用者任何問題，使用繁體中文:台灣。",
                            "max_history_len": 256,
                            "state_machine": {},
                            "agent_name": "TestAgent",
                        },
                        "memory": {
                            "history": [],
                        },
                        "request_tools": [],
                    },
                },
                "deepinfra_simple": {
                    "summary": "Simple Chat Example with Deepinfra",
                    "description": "Simple chat example with Deepinfra.",
                    "value": {
                        "user_message": "你好",
                        "edited_last_response": "",
                        "recall_last_user_message": False,
                        "settings": {
                            "api_key": "your_api_key",
                            "chat_model": "deepseek-ai/DeepSeek-V3",
                            "base_url": "https://api.deepinfra.com/v1/openai",
                            "top_p": 1.0,
                            "temperature": 1.0,
                            "top_k": 5,
                            "vector_db_url": "http://weaviate:8080",
                            "global_prompt": "你是一個專業的顧問，有耐心且親切地回答使用者任何問題，使用繁體中文:台灣。",
                            "max_history_len": 256,
                            "state_machine": {},
                            "agent_name": "TestAgent",
                        },
                        "memory": {
                            "history": [],
                        },
                        "request_tools": [],
                    },
                },
                "deepseek_simple": {
                    "summary": "Simple Chat Example with Deepseek",
                    "description": "Simple chat example with Deepseek.",
                    "value": {
                        "user_message": "你好",
                        "edited_last_response": "",
                        "recall_last_user_message": False,
                        "settings": {
                            "api_key": "your_api_key",
                            "chat_model": "deepseek-chat",
                            "base_url": "https://api.deepseek.com/v1",
                            "top_p": 1.0,
                            "temperature": 1.0,
                            "top_k": 5,
                            "vector_db_url": "http://weaviate:8080",
                            "global_prompt": "你是一個專業的顧問，有耐心且親切地回答使用者任何問題，使用繁體中文:台灣。",
                            "max_history_len": 256,
                            "state_machine": {},
                            "agent_name": "TestAgent",
                        },
                        "memory": {
                            "history": [],
                        },
                        "request_tools": [],
                    },
                },
                "openai_completed": {
                    "summary": "OpenAI API completed example",
                    "description": "Chat example with OpenAI API, using a state machine and request tools.",
                    "value": {
                        "user_message": "你好",
                        "edited_last_response": "",
                        "recall_last_user_message": False,
                        "settings": {
                            "api_key": "your_api_key",
                            "chat_model": "gpt-4o",
                            "base_url": "https://api.openai.com/v1/",
                            "top_p": 1.0,
                            "temperature": 1.0,
                            "top_k": 5,
                            "vector_db_url": "http://weaviate:8080",
                            "global_prompt": "你是一個專業的顧問，有耐心且親切地回答使用者任何問題，使用繁體中文:台灣。",
                            "max_history_len": 256,
                            "agent_name": "TestAgent",
                            "state_machine": {
                                "initial_state_name": "打招呼",
                                "states": [
                                    {
                                        "name": "打招呼",
                                        "scenario": "顧問主動問候使用者",
                                        "instruction": "有禮貌的問候使用者",
                                    },
                                    {
                                        "name": "時間問題",
                                        "scenario": "使用者提出跟時間相關的問題",
                                        "instruction": "適時地使用工具並回答使用者的時間問題",
                                    },
                                    {
                                        "name": "天氣問題",
                                        "scenario": "使用者提出跟天氣相關的問題",
                                        "instruction": "適時地使用工具並回答使用者的天氣問題",
                                    },
                                    {
                                        "name": "異議處理",
                                        "scenario": "使用者提到其他的話題",
                                        "instruction": "試圖引導使用者回原本的話題",
                                    },
                                ],
                                "out_transitions": {
                                    "打招呼": ["時間問題", "天氣問題"],
                                    "時間問題": ["天氣問題"],
                                    "天氣問題": ["時間問題"],
                                },
                            },
                        },
                        "memory": {},
                        "request_tools": [
                            {
                                "name": "get_time",
                                "description": "Get current time.",
                                "url": "https://timeapi.io/api/time/current/coordinate",
                                "method": "GET",
                                "headers": {"Content-Type": "application/json"},
                                "request_params": {
                                    "latitude": {
                                        "type": ["number", "null"],
                                        "description": "The latitude coordinate.",
                                    },
                                    "longitude": {
                                        "type": ["number", "null"],
                                        "description": "The longitude coordinate.",
                                    },
                                },
                                "request_json": None,
                            },
                            {
                                "name": "get_weather",
                                "description": "Get weather.",
                                "url": "https://api.open-meteo.com/v1/forecast?current=temperature_2m,wind_speed_10m,weather_code",
                                "method": "GET",
                                "headers": {"Content-Type": "application/json"},
                                "request_params": {
                                    "latitude": {
                                        "type": "number",
                                        "description": "The latitude coordinate.",
                                    },
                                    "longitude": {
                                        "type": "number",
                                        "description": "The longitude coordinate.",
                                    },
                                },
                                "request_json": None,
                            },
                        ],
                    },
                },
                "openai_chatml_conversation": {
                    "summary": "OpenAI Multi-turn Conversation with ChatML",
                    "description": "Multi-turn conversation example using ChatML format.",
                    "value": {
                        "user_message": [
                            {
                                "role": "system",
                                "content": "你是一个专业的技术顾问，擅长解答编程和技术问题。",
                            },
                            {"role": "user", "content": "什么是 REST API？"},
                            {
                                "role": "assistant",
                                "content": "REST API 是一种基于 HTTP 协议的 Web 服务架构风格，它使用标准的 HTTP 方法（GET、POST、PUT、DELETE）来操作资源。",
                            },
                            {"role": "user", "content": "能给我一个具体的例子吗？"},
                        ],
                        "edited_last_response": "",
                        "recall_last_user_message": False,
                        "settings": {
                            "api_key": "your_api_key",
                            "chat_model": "gpt-4o",
                            "base_url": "https://api.openai.com/v1/",
                            "top_p": 1.0,
                            "temperature": 0.7,
                            "top_k": 5,
                            "vector_db_url": "http://weaviate:8080",
                            "global_prompt": "你是一个专业的技术顾问，请详细且准确地回答技术问题。",
                            "max_history_len": 256,
                            "state_machine": {},
                            "agent_name": "TechAdvisor",
                        },
                        "memory": {
                            "history": [],
                        },
                        "request_tools": [],
                    },
                },
            }
        ),
    ],
) -> ChatResponse:
    """
    Generate a chat response based on the user message and conversation memory.
    """
    try:
        logger.info(f"Processing chat request for agent: {request.settings.agent_name}")

        # 创建ChatService实例（每次调用新建）
        chat_service = _get_chat_service(request.settings)

        settings = Setting(**request.settings.model_dump())
        memory = Memory(**request.memory.model_dump())

        # request_tools 已经是 RequestTool 对象列表，直接使用
        request_tools = request.request_tools

        # 从 ChatRequest 中获取用户消息内容（兼容 str 和 ChatML 格式）
        user_message_content = request.get_user_content()

        # 调用ChatService的chat_step方法
        result = await chat_service.chat_step(
            user_message=user_message_content,
            edited_last_response=request.edited_last_response,
            recall_last_user_message=request.recall_last_user_message,
            settings=settings,
            memory=memory,
            request_tools=request_tools,
        )

        # 构建响应
        response = ChatResponse(
            response=result["response"],
            memory=result["memory"].model_dump(),
            result_type=result["result_type"],
            llm_calling_times=result["llm_calling_times"],
            total_input_token=result["total_input_token"],
            total_output_token=result["total_output_token"],
        )

        logger.info(f"Chat request completed for agent: {request.settings.agent_name}")
        return response

    except Exception as e:
        logger.exception("Error generating chat response", exc_info=e)
        raise HTTPException(500, detail="Failed to generate chat response") from e


@router.post("/learn", response_model=LearnResponse, status_code=status.HTTP_200_OK)
async def learn_from_feedback(
    request: Annotated[
        LearnRequest,
        Body(
            openapi_examples={
                "openai_example": {
                    "summary": "Learn from feedback with OpenAI API",
                    "description": "Learn from feedback with OpenAI API.",
                    "value": {
                        "settings": {
                            "vector_db_url": "http://weaviate:8080",
                            "agent_name": "TestAgent",
                            "embedding_api_key": "your-openai-api-key-here",
                            "embedding_model": "text-embedding-3-small",
                            "embedding_base_url": "https://api.openai.com/v1/",
                        },
                        "feedbacks": [
                            {
                                "observation_name": "send_message_to_user",
                                "observation_content": '{"user_message": "有沒有推薦的烤肉地點呢？"}',
                                "action_name": "send_message_to_user",
                                "action_content": '{"agent_message": "抱歉，我無法處理這個問題"}',
                                "state_name": "異議處理",
                            }
                        ],
                    },
                },
                "deepinfra_example": {
                    "summary": "Learn from feedback with Deepinfra API",
                    "description": "Learn from feedback with Deepinfra API.",
                    "value": {
                        "settings": {
                            "vector_db_url": "http://weaviate:8080",
                            "agent_name": "TestAgent",
                            "embedding_api_key": "your-openai-api-key-here",
                            "embedding_model": "text-embedding-3-small",
                            "embedding_base_url": "https://api.openai.com/v1/",
                        },
                        "feedbacks": [
                            {
                                "observation_name": "send_message_to_user",
                                "observation_content": json.dumps(
                                    {"user_message": "有沒有推薦的烤肉地點呢？"},
                                    ensure_ascii=False,
                                ),
                                "action_name": "send_message_to_user",
                                "action_content": json.dumps(
                                    {"agent_message": "抱歉，我無法處理這個問題"},
                                    ensure_ascii=False,
                                ),
                                "state_name": "異議處理",
                            }
                        ],
                    },
                },
            }
        ),
    ],
) -> LearnResponse:
    """
    Learn from feedbacks and update the model.
    """
    try:
        # 转换 feedbacks
        feedbacks = []
        for feedback_data in request.feedbacks:
            feedback = Feedback(**feedback_data.model_dump())
            feedbacks.append(feedback)

        # 创建完整的FeedbackSetting对象
        feedback_setting = FeedbackSetting(
            vector_db_url=request.settings.vector_db_url,
            agent_name=request.settings.agent_name,
            embedding_api_key=request.settings.embedding_api_key,  # 需要根据实际情况调整
            embedding_model=request.settings.embedding_model,
            embedding_base_url=request.settings.embedding_base_url,
            embedding_vector_dim=1024,
            top_k=5,
        )

        # 获取FeedbackService实例并调用add_feedbacks方法
        feedback_service = _get_feedback_service(feedback_setting)
        await feedback_service.add_feedbacks(
            settings=feedback_setting, feedbacks=feedbacks
        )

        # 构建响应
        response = LearnResponse(
            status="Success", data=[f"Successfully learned {len(feedbacks)} feedbacks"]
        )

        logger.info(f"Learn request completed for agent: {request.settings.agent_name}")
        return response

    except Exception as e:
        logger.exception("Error learning from feedback", exc_info=e)
        raise HTTPException(500, detail="Failed to learn from feedback") from e


@router.get("/feedbacks", response_model=List[Feedback], status_code=status.HTTP_200_OK)
async def get_all_feedbacks_endpoint(
    agent_name: str = Query(..., description="Agent名称"),
    vector_db_url: str = Query(..., description="向量数据库URL"),
    offset: int = Query(0, description="偏移量"),
    limit: int = Query(-1, description="限制数量"),
) -> List[Feedback]:
    """
    Get all feedbacks through FeedbackService.
    """
    try:
        # 创建FeedbackSetting对象
        feedback_settings = FeedbackSetting(
            vector_db_url=vector_db_url,
            agent_name=agent_name,
            embedding_api_key="dummy",
            embedding_model="text-embedding-3-small",
            embedding_base_url="https://api.openai.com/v1/",
            embedding_vector_dim=1024,
            top_k=5,
        )

        # 直接调用 FeedbackService
        feedback_service = _get_feedback_service(feedback_settings)
        feedbacks = await feedback_service.get_feedbacks(
            agent_name=agent_name, offset=offset, limit=limit
        )

        logger.info(f"Retrieved {len(feedbacks)} feedbacks for agent: {agent_name}")
        return feedbacks
    except Exception as e:
        logger.exception("Error getting feedbacks", exc_info=e)
        raise HTTPException(500, detail="Failed to get feedbacks") from e


@router.delete("/feedbacks", status_code=status.HTTP_204_NO_CONTENT)
async def delete_all_feedbacks_endpoint(
    agent_name: str = Query(..., description="Agent名称"),
    vector_db_url: str = Query(..., description="向量数据库URL"),
) -> None:
    """
    Delete all feedbacks through FeedbackService.
    """
    try:
        # 创建FeedbackSetting对象
        feedback_settings = FeedbackSetting(
            vector_db_url=vector_db_url,
            agent_name=agent_name,
            embedding_api_key="dummy",
            embedding_model="text-embedding-3-small",
            embedding_base_url="https://api.openai.com/v1/",
            embedding_vector_dim=1024,
            top_k=5,
        )

        # 直接调用 FeedbackService
        feedback_service = _get_feedback_service(feedback_settings)
        await feedback_service.delete_all_feedbacks(agent_name)

        logger.info(f"Deleted all feedbacks for agent: {agent_name}")
    except Exception as e:
        logger.exception("Error deleting feedbacks", exc_info=e)
        raise HTTPException(500, detail="Failed to delete feedbacks") from e


@router.delete("/collections/{agent_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collection(
    agent_name: str,
    vector_db_url: str = Query(..., description="Vector database URL"),
):
    """
    删除指定agent的整个集合

    Args:
        agent_name: Agent名称
        vector_db_url: 向量数据库URL
    """
    try:
        # 创建临时FeedbackSetting
        feedback_settings = FeedbackSetting(
            vector_db_url=vector_db_url,
            agent_name=agent_name,
            embedding_api_key="dummy",  # 删除操作不需要真实的embedding key
            top_k=5,
        )

        # 获取FeedbackService实例并删除集合
        feedback_service = _get_feedback_service(feedback_settings)
        await feedback_service.delete_collection(agent_name)

        logger.info(f"Deleted collection for agent: {agent_name}")
    except Exception as e:
        logger.exception("Error deleting collection", exc_info=e)
        raise HTTPException(500, detail="Failed to delete collection") from e
