from typing import List, Annotated
from fastapi import APIRouter, HTTPException, status, Body, Query
import json

from agent_runtime.services.chat_v2_service import ChatV2Service
from agent_runtime.interface.api_models import (
    ChatRequest,
    ChatResponse,
    LearnRequest,
    LearnResponse,
    GetFeedbackParam,
    DeleteFeedbackParam
)
from agent_runtime.data_format.feedback import Feedback
from agent_runtime.logging.logger import logger

router = APIRouter()
chat_service = ChatV2Service()


@router.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def generate_chat(
    request: Annotated[
        ChatRequest,
        Body(
            openapi_examples={
                "openai_simple": {
                    "summary": "Simple Chat Example with OpenAI",
                    "description": "Simple chat example with OpenAI.",
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
                        "request_tools": []
                    }
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
                        "request_tools": []
                    }
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
                        "request_tools": []
                    }
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
                                        "instruction": "有禮貌的問候使用者"
                                    },
                                    {
                                        "name": "時間問題",
                                        "scenario": "使用者提出跟時間相關的問題",
                                        "instruction": "適時地使用工具並回答使用者的時間問題"
                                    },
                                    {
                                        "name": "天氣問題",
                                        "scenario": "使用者提出跟天氣相關的問題",
                                        "instruction": "適時地使用工具並回答使用者的天氣問題"
                                    },
                                    {
                                        "name": "異議處理",
                                        "scenario": "使用者提到其他的話題",
                                        "instruction": "試圖引導使用者回原本的話題"
                                    }
                                ],
                                "out_transitions": {
                                    "打招呼": ["時間問題", "天氣問題"],
                                    "時間問題": ["天氣問題"],
                                    "天氣問題": ["時間問題"],
                                }
                            },
                        },
                        "memory": {},
                        "request_tools": [
                            {
                                "name": "get_time",
                                        "description": "Get current time.",
                                        "url": "https://timeapi.io/api/time/current/coordinate",
                                        "method": "GET",
                                        "headers": {
                                            "Content-Type": "application/json"
                                        },
                                "request_params": {
                                            "latitude": {
                                                "type": ["number", "null"],
                                                "description": "The latitude coordinate."
                                            },
                                            "longitude": {
                                                "type": ["number", "null"],
                                                "description": "The longitude coordinate."
                                            }
                                        },
                                "request_json": None
                            },
                            {
                                "name": "get_weather",
                                        "description": "Get weather.",
                                        "url": "https://api.open-meteo.com/v1/forecast?current=temperature_2m,wind_speed_10m,weather_code",
                                        "method": "GET",
                                        "headers": {
                                            "Content-Type": "application/json"
                                        },
                                "request_params": {
                                            "latitude": {
                                                "type": "number",
                                                "description": "The latitude coordinate."
                                            },
                                            "longitude": {
                                                "type": "number",
                                                "description": "The longitude coordinate."
                                            }
                                        },
                                "request_json": None
                            }
                        ],
                    }
                }
            })
    ]
) -> ChatResponse:
    """
    Generate a chat response based on the user message and conversation memory.
    """
    try:
        response = await chat_service.generate_chat(request)
        return response
    except Exception as e:
        logger.exception("Error learning from feedback", exc_info=e)
        raise HTTPException(
            500, detail="Failed to generate chat response") from e


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
                        },
                        "feedbacks": [
                            {
                                "observation_name": "send_message_to_user",
                                "observation_content": "{\"user_message\": \"有沒有推薦的烤肉地點呢？\"}",
                                "action_name": "send_message_to_user",
                                "action_content": "{\"agent_message\": \"抱歉，我無法處理這個問題\"}",
                                "state_name": "異議處理"
                            }
                        ]
                    }
                },
                "deepinfra_example": {
                    "summary": "Learn from feedback with Deepinfra API",
                    "description": "Learn from feedback with Deepinfra API.",
                    "value": {
                        "settings": {
                            "vector_db_url": "http://weaviate:8080",
                            "agent_name": "TestAgent",
                        },
                        "feedbacks": [
                            {
                                "observation_name": "send_message_to_user",
                                "observation_content": json.dumps({"user_message": "有沒有推薦的烤肉地點呢？"}, ensure_ascii=False),
                                "action_name": "send_message_to_user",
                                "action_content": json.dumps({"agent_message": "抱歉，我無法處理這個問題"}, ensure_ascii=False),
                                "state_name": "異議處理"
                            }
                        ]
                    }
                }
            }
        )
    ]
) -> LearnResponse:
    """
    Learn from feedbacks and update the model.
    """
    try:
        response = await chat_service.learn_from_feedback(request)
        return response
    except Exception as e:
        logger.exception("Error learning from feedback", exc_info=e)
        raise HTTPException(500, detail="Failed to learn from feedback") from e


@router.get("/feedbacks", response_model=List[Feedback], status_code=status.HTTP_200_OK)
async def get_all_feedbacks_endpoint(
    agent_name: str = Query(..., description="Agent名称"),
    vector_db_url: str = Query(..., description="向量数据库URL"),
    offset: int = Query(0, description="偏移量"),
    limit: int = Query(-1, description="限制数量")
) -> List[Feedback]:
    """
    Get all feedbacks.
    """
    try:
        param = GetFeedbackParam(
            agent_name=agent_name,
            vector_db_url=vector_db_url,
            offset=offset,
            limit=limit
        )
        return await chat_service.get_all_feedbacks(param)
    except Exception as e:
        logger.exception("Error getting feedbacks", exc_info=e)
        raise HTTPException(500, detail="Failed to get feedbacks") from e


@router.delete("/feedbacks", status_code=status.HTTP_204_NO_CONTENT)
async def delete_all_feedbacks_endpoint(
    agent_name: str = Query(..., description="Agent名称"),
    vector_db_url: str = Query(..., description="向量数据库URL")
) -> None:
    """
    Delete all feedbacks.
    """
    try:
        param = DeleteFeedbackParam(
            agent_name=agent_name,
            vector_db_url=vector_db_url
        )
        await chat_service.delete_all_feedbacks(param)
    except Exception as e:
        logger.exception("Error deleting feedbacks", exc_info=e)
        raise HTTPException(500, detail="Failed to delete feedbacks") from e