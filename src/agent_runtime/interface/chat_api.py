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

    # 更新agents的LLM引擎（带session_id用于token统计）
    session_id = f"{settings.agent_name}_{id(chat_service)}"
    chat_service.update_agents_llm_engine(llm_engine, session_id)

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
                "openai_string_format": {
                    "summary": "OpenAI Chat with String Format",
                    "description": "基本的 OpenAI 聊天，使用簡單字串格式的用戶訊息（向後兼容）。",
                    "value": {
                        "user_message": "您好，請問您今天可以如何協助我？",
                        "edited_last_response": "",
                        "recall_last_user_message": False,
                        "settings": {
                            "api_key": "your-openai-api-key",
                            "chat_model": "gpt-4o",
                            "base_url": "https://api.openai.com/v1/",
                            "top_p": 1.0,
                            "temperature": 0.7,
                            "top_k": 5,
                            "vector_db_url": "http://weaviate:8080",
                            "global_prompt": "您是一個樂於助人的 AI 助手。請提供清晰準確的回應，使用繁體中文。",
                            "max_history_len": 256,
                            "state_machine": {},
                            "agent_name": "OpenAIAgent",
                        },
                        "memory": {
                            "history": [],
                        },
                        "request_tools": [],
                    },
                },
                "openai_chatml_messages": {
                    "summary": "OpenAI Chat with ChatML Messages Format",
                    "description": "使用 ChatML 訊息格式的 OpenAI 聊天，包含系統、用戶和助手角色。",
                    "value": {
                        "user_message": [
                            {
                                "role": "system",
                                "content": "您是一個樂於助人的 AI 助手，提供詳細準確的回應，使用繁體中文。",
                            },
                            {"role": "user", "content": "什麼是人工智慧？它是如何運作的？"},
                        ],
                        "edited_last_response": "",
                        "recall_last_user_message": False,
                        "settings": {
                            "api_key": "your-openai-api-key",
                            "chat_model": "gpt-4o",
                            "base_url": "https://api.openai.com/v1/",
                            "top_p": 1.0,
                            "temperature": 0.7,
                            "top_k": 5,
                            "vector_db_url": "http://weaviate:8080",
                            "global_prompt": "您是一位專業的 AI 助手，具備科技和科學領域的專業知識，請使用繁體中文回應。",
                            "max_history_len": 256,
                            "state_machine": {},
                            "agent_name": "OpenAIAssistant",
                        },
                        "memory": {
                            "history": [],
                        },
                        "request_tools": [],
                    },
                },
                "deepinfra_completed_chatml": {
                    "summary": "DeepInfra completed example with ChatML Messages Format",
                    "description": "完整的 DeepInfra 聊天範例，使用 ChatML 格式，具備多輪對話和進階功能。",
                    "value": {
                        "user_message": [
                            {
                                "role": "system",
                                "content": "您是由 DeepInfra 基礎架構驅動的 AI 助手。請提供全面且結構良好的回應，使用繁體中文。",
                            },
                            {"role": "user", "content": "使用雲端基礎的 AI 推理有什麼好處？"},
                            {
                                "role": "assistant",
                                "content": "雲端基礎的 AI 推理提供幾個主要優點，包括可擴展性、成本效益，以及無需預先投資即可存取強大硬體。",
                            },
                            {"role": "user", "content": "請您詳細說明可擴展性這個方面好嗎？"},
                        ],
                        "edited_last_response": "",
                        "recall_last_user_message": False,
                        "settings": {
                            "api_key": "your-deepinfra-api-key",
                            "chat_model": "meta-llama/Meta-Llama-3.1-405B-Instruct",
                            "base_url": "https://api.deepinfra.com/v1/openai",
                            "top_p": 0.9,
                            "temperature": 0.7,
                            "top_k": 5,
                            "vector_db_url": "http://weaviate:8080",
                            "global_prompt": "您是具備雲端運算和 AI 基礎架構專業知識的知識型 AI 助手。請提供詳細實用的見解，使用繁體中文。",
                            "max_history_len": 512,
                            "state_machine": {
                                "initial_state_name": "諮詢服務",
                                "states": [
                                    {
                                        "name": "諮詢服務",
                                        "scenario": "提供 AI 和雲端主題的專家諮詢",
                                        "instruction": "進行詳細的技術討論並提供專家見解",
                                    },
                                    {
                                        "name": "深度分析",
                                        "scenario": "使用者需要詳細技術資訊",
                                        "instruction": "提供全面的技術解釋和實際範例",
                                    },
                                    {
                                        "name": "解決方案設計",
                                        "scenario": "使用者需要協助設計解決方案",
                                        "instruction": "根據需求協助設計和架構 AI 解決方案",
                                    },
                                ],
                                "out_transitions": {
                                    "諮詢服務": ["深度分析", "解決方案設計"],
                                    "深度分析": ["解決方案設計", "諮詢服務"],
                                    "解決方案設計": ["深度分析", "諮詢服務"],
                                },
                            },
                            "agent_name": "DeepInfraConsultant",
                        },
                        "memory": {
                            "history": [],
                        },
                        "request_tools": [],
                    },
                },
                "deepseek_completed_chatml": {
                    "summary": "Deepseek completed example with ChatML Messages Format",
                    "description": "完整的 Deepseek 聊天範例，使用 ChatML 格式，具備進階對話管理功能。",
                    "value": {
                        "user_message": [
                            {
                                "role": "system",
                                "content": "您是由 Deepseek 驅動的智慧 AI 助手。請提供有用、準確且深思熟慮的回應，使用繁體中文。",
                            },
                            {"role": "user", "content": "請問您可以解釋大型語言模型是如何運作的嗎？"},
                        ],
                        "edited_last_response": "",
                        "recall_last_user_message": False,
                        "settings": {
                            "api_key": "your-deepseek-api-key",
                            "chat_model": "deepseek-chat",
                            "base_url": "https://api.deepseek.com/v1",
                            "top_p": 0.95,
                            "temperature": 0.8,
                            "top_k": 5,
                            "vector_db_url": "http://weaviate:8080",
                            "global_prompt": "您是專精於科技和科學解釋的專家 AI 助手。請提供清晰詳細的回應，使用繁體中文。",
                            "max_history_len": 512,
                            "state_machine": {
                                "initial_state_name": "介紹",
                                "states": [
                                    {
                                        "name": "介紹",
                                        "scenario": "與使用者的初次互動",
                                        "instruction": "介紹自己並了解使用者的需求",
                                    },
                                    {
                                        "name": "技術解釋",
                                        "scenario": "使用者要求技術解釋",
                                        "instruction": "提供詳細準確的技術解釋並舉例說明",
                                    },
                                    {
                                        "name": "澄清說明",
                                        "scenario": "使用者需要澄清或有後續問題",
                                        "instruction": "詢問澄清問題並提供針對性的解釋",
                                    },
                                ],
                                "out_transitions": {
                                    "介紹": ["技術解釋", "澄清說明"],
                                    "技術解釋": ["澄清說明", "技術解釋"],
                                    "澄清說明": ["技術解釋", "介紹"],
                                },
                            },
                            "agent_name": "DeepseekExpert",
                        },
                        "memory": {
                            "history": [],
                        },
                        "request_tools": [],
                    },
                },
                "openai_completed_chatml": {
                    "summary": "OpenAI API completed example with ChatML Messages Format",
                    "description": "完整的 OpenAI 聊天範例，使用 ChatML 格式，包含狀態機、工具和對話歷史。",
                    "value": {
                        "user_message": [
                            {
                                "role": "system",
                                "content": "您是一位專業助手，協助使用者獲取時間和天氣資訊。請提供準確有用的回應，使用繁體中文。",
                            },
                            {"role": "user", "content": "您好！請問您可以幫我查詢現在的時間嗎？"},
                        ],
                        "edited_last_response": "",
                        "recall_last_user_message": False,
                        "settings": {
                            "api_key": "your-openai-api-key",
                            "chat_model": "gpt-4o",
                            "base_url": "https://api.openai.com/v1/",
                            "top_p": 1.0,
                            "temperature": 0.7,
                            "top_k": 5,
                            "vector_db_url": "http://weaviate:8080",
                            "global_prompt": "您是專門提供時間和天氣資訊的專業助手，請使用繁體中文回應。",
                            "max_history_len": 256,
                            "agent_name": "TimeWeatherAgent",
                            "state_machine": {
                                "initial_state_name": "打招呼",
                                "states": [
                                    {
                                        "name": "打招呼",
                                        "scenario": "助手向使用者問候",
                                        "instruction": "禮貌地問候使用者並詢問如何協助",
                                    },
                                    {
                                        "name": "時間查詢",
                                        "scenario": "使用者詢問時間相關問題",
                                        "instruction": "使用適當的工具準確回答時間相關問題",
                                    },
                                    {
                                        "name": "天氣查詢",
                                        "scenario": "使用者詢問天氣相關問題",
                                        "instruction": "使用適當的工具提供天氣資訊",
                                    },
                                    {
                                        "name": "一般協助",
                                        "scenario": "使用者詢問其他主題",
                                        "instruction": "禮貌地引導對話回到時間和天氣主題",
                                    },
                                ],
                                "out_transitions": {
                                    "打招呼": ["時間查詢", "天氣查詢", "一般協助"],
                                    "時間查詢": ["天氣查詢", "一般協助"],
                                    "天氣查詢": ["時間查詢", "一般協助"],
                                    "一般協助": ["時間查詢", "天氣查詢"],
                                },
                            },
                        },
                        "memory": {
                            "history": [],
                        },
                        "request_tools": [
                            {
                                "name": "get_time",
                                "description": "取得指定座標的目前時間",
                                "url": "https://timeapi.io/api/time/current/coordinate",
                                "method": "GET",
                                "headers": {"Content-Type": "application/json"},
                                "request_params": {
                                    "latitude": {
                                        "type": ["number", "null"],
                                        "description": "緯度座標",
                                    },
                                    "longitude": {
                                        "type": ["number", "null"],
                                        "description": "經度座標",
                                    },
                                },
                                "request_json": None,
                            },
                            {
                                "name": "get_weather",
                                "description": "取得目前天氣資訊",
                                "url": "https://api.open-meteo.com/v1/forecast?current=temperature_2m,wind_speed_10m,weather_code",
                                "method": "GET",
                                "headers": {"Content-Type": "application/json"},
                                "request_params": {
                                    "latitude": {
                                        "type": "number",
                                        "description": "緯度座標",
                                    },
                                    "longitude": {
                                        "type": "number",
                                        "description": "經度座標",
                                    },
                                },
                                "request_json": None,
                            },
                        ],
                    },
                },
                "openai_with_image": {
                    "summary": "OpenAI Chat with Image",
                    "description": "包含圖像處理功能的 OpenAI 聊天範例，使用多模態 ChatML 格式。",
                    "value": {
                        "user_message": [
                            {
                                "role": "system",
                                "content": "您是一位樂於助人的 AI 助手，能夠分析圖像並回答視覺內容相關問題。請提供詳細準確的描述，使用繁體中文。",
                            },
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": "您在這張圖片中看到什麼？請詳細描述。"
                                    },
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAYEBQYFBAYGBQYHBwYIChAKCgkJChQODwwQFxQYGBcUFhYaHSUfGhsjHBYWICwgIyYnKSopGR8tMC0oMCUoKSj/2wBDAQcHBwoIChMKChMoGhYaKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCj/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCdABmX/9k=",
                                            "detail": "high"
                                        }
                                    }
                                ]
                            }
                        ],
                        "edited_last_response": "",
                        "recall_last_user_message": False,
                        "settings": {
                            "api_key": "your-openai-api-key",
                            "chat_model": "gpt-4o",
                            "base_url": "https://api.openai.com/v1/",
                            "top_p": 1.0,
                            "temperature": 0.7,
                            "top_k": 5,
                            "vector_db_url": "http://weaviate:8080",
                            "global_prompt": "您是專業的圖像分析助手。請提供詳細準確的視覺內容描述和見解，使用繁體中文。",
                            "max_history_len": 256,
                            "state_machine": {},
                            "agent_name": "VisionAssistant",
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

        # 处理用户消息格式
        if isinstance(request.user_message, list):
            # ChatML格式，需要特殊处理多模态内容
            user_message = request.get_messages()
        else:
            # 字符串格式，保持向后兼容
            user_message = request.user_message

        # 调用ChatService的chat_step方法
        result = await chat_service.chat_step(
            user_message=user_message,
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
