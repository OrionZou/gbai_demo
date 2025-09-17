"""
Feedback API endpoints based on FeedbackService

提供学习、获取和删除反馈的API接口
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from agent_runtime.services.feedback_service import FeedbackService
from agent_runtime.clients.weaviate_client import WeaviateClient
from agent_runtime.clients.openai_embedding_client import OpenAIEmbeddingClient
from agent_runtime.data_format.feedback import Feedback, FeedbackSetting
from agent_runtime.logging.logger import logger


# API Models
class LearnRequest(BaseModel):
    """学习请求模型"""
    agent_name: str
    feedbacks: List[Feedback]
    vector_db_url: str = "http://localhost:8080"
    top_k: int = 5


class LearnResponse(BaseModel):
    """学习响应模型"""
    success: bool
    message: str
    feedback_ids: List[str]
    count: int


class FeedbackGetRequest(BaseModel):
    """获取反馈请求模型"""
    agent_name: str
    vector_db_url: str = "http://localhost:8080"
    offset: int = 0
    limit: int = -1
    query: Optional[str] = None
    tags: Optional[List[str]] = None
    top_k: int = 5


class FeedbackGetResponse(BaseModel):
    """获取反馈响应模型"""
    success: bool
    message: str
    feedbacks: List[Feedback]
    total_count: int
    query_count: int


class FeedbackDeleteRequest(BaseModel):
    """删除反馈请求模型"""
    agent_name: str
    vector_db_url: str = "http://localhost:8080"
    delete_type: str = "all"  # "all" or "collection"


class FeedbackDeleteResponse(BaseModel):
    """删除反馈响应模型"""
    success: bool
    message: str
    deleted_count: Optional[int] = None


# Dependency injection
def get_feedback_service() -> FeedbackService:
    """获取FeedbackService实例"""
    # 这里可以配置不同的客户端
    weaviate_client = WeaviateClient(base_url="http://localhost:8080")

    # 可选：配置OpenAI嵌入客户端
    embedding_client = None
    try:
        import os
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            embedding_client = OpenAIEmbeddingClient(
                api_key=api_key,
                model_name="text-embedding-3-small",
                dimensions=384
            )
            logger.info("OpenAI embedding client initialized for API")
    except Exception as e:
        logger.warning(f"Failed to initialize OpenAI client: {e}")

    return FeedbackService(weaviate_client, embedding_client)


# Router
router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("/learn", response_model=LearnResponse)
async def learn_feedbacks(
    request: LearnRequest,
    service: FeedbackService = Depends(get_feedback_service)
):
    """
    学习反馈API

    将提供的反馈添加到向量数据库中进行学习
    """
    try:
        logger.info(f"Learning {len(request.feedbacks)} feedbacks for agent: {request.agent_name}")

        # 创建设置
        settings = FeedbackSetting(
            vector_db_url=request.vector_db_url,
            top_k=request.top_k,
            agent_name=request.agent_name
        )

        # 添加反馈
        feedback_ids = await service.add_feedbacks(settings, request.feedbacks)

        # 获取总数
        total_count = await service.get_feedback_count(request.agent_name)

        logger.info(f"Successfully learned {len(feedback_ids)} feedbacks")

        return LearnResponse(
            success=True,
            message=f"Successfully learned {len(feedback_ids)} feedbacks",
            feedback_ids=feedback_ids,
            count=total_count
        )

    except Exception as e:
        logger.error(f"Failed to learn feedbacks: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to learn feedbacks: {str(e)}"
        )


@router.post("/get", response_model=FeedbackGetResponse)
async def get_feedbacks(
    request: FeedbackGetRequest,
    service: FeedbackService = Depends(get_feedback_service)
):
    """
    获取反馈API

    支持普通获取和基于查询的语义搜索
    """
    try:
        logger.info(f"Getting feedbacks for agent: {request.agent_name}")

        if request.query:
            # 语义搜索
            logger.info(f"Performing semantic search with query: {request.query}")
            settings = FeedbackSetting(
                vector_db_url=request.vector_db_url,
                top_k=request.top_k,
                agent_name=request.agent_name
            )

            feedbacks = await service.query_feedbacks(
                settings=settings,
                query=request.query,
                tags=request.tags
            )
            query_count = len(feedbacks)

        else:
            # 普通获取
            logger.info(f"Getting feedbacks with offset={request.offset}, limit={request.limit}")
            feedbacks = await service.get_feedbacks(
                agent_name=request.agent_name,
                offset=request.offset,
                limit=request.limit
            )
            query_count = len(feedbacks)

        # 获取总数
        total_count = await service.get_feedback_count(request.agent_name)

        logger.info(f"Retrieved {query_count} feedbacks (total: {total_count})")

        return FeedbackGetResponse(
            success=True,
            message=f"Retrieved {query_count} feedbacks",
            feedbacks=feedbacks,
            total_count=total_count,
            query_count=query_count
        )

    except Exception as e:
        logger.error(f"Failed to get feedbacks: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get feedbacks: {str(e)}"
        )


@router.post("/delete", response_model=FeedbackDeleteResponse)
async def delete_feedbacks(
    request: FeedbackDeleteRequest,
    service: FeedbackService = Depends(get_feedback_service)
):
    """
    删除反馈API

    支持删除所有反馈或删除整个集合
    """
    try:
        logger.info(f"Deleting feedbacks for agent: {request.agent_name}, type: {request.delete_type}")

        if request.delete_type == "collection":
            # 删除整个集合
            await service.delete_collection(request.agent_name)
            message = f"Collection for agent '{request.agent_name}' deleted successfully"
            deleted_count = None

        elif request.delete_type == "all":
            # 删除所有反馈但保留集合
            # 先获取数量
            deleted_count = await service.get_feedback_count(request.agent_name)
            await service.delete_all_feedbacks(request.agent_name)
            message = f"All {deleted_count} feedbacks deleted for agent '{request.agent_name}'"

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid delete_type: {request.delete_type}. Must be 'all' or 'collection'"
            )

        logger.info(f"Successfully deleted feedbacks: {message}")

        return FeedbackDeleteResponse(
            success=True,
            message=message,
            deleted_count=deleted_count
        )

    except Exception as e:
        logger.error(f"Failed to delete feedbacks: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete feedbacks: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """健康检查API"""
    return {"status": "healthy", "service": "feedback_api"}


@router.get("/stats/{agent_name}")
async def get_agent_stats(
    agent_name: str,
    service: FeedbackService = Depends(get_feedback_service)
):
    """获取代理统计信息"""
    try:
        count = await service.get_feedback_count(agent_name)
        return {
            "agent_name": agent_name,
            "feedback_count": count,
            "has_embeddings": service.embedding_client is not None
        }
    except Exception as e:
        logger.error(f"Failed to get stats for agent {agent_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get stats: {str(e)}"
        )