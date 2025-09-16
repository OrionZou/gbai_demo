import json
from typing import List
from pydantic import BaseModel

TAG_PREFIX_STATE_NAME = "state_name_"
TAG_PREFIX_OBSERVATION_NAME = "observation_name_"


class FeedbackSetting(BaseModel):
    """Runtime configuration for the feedback subsystem."""
    vector_db_url: str  # e.g. "http://weaviate.my-cluster.com:8080"
    top_k: int = 5
    agent_name: str


class Feedback(BaseModel):
    observation_name: str
    observation_content: str
    action_name: str
    action_content: str
    state_name: str

    def tags(self) -> List[str]:
        return [
            TAG_PREFIX_STATE_NAME + self.state_name,
            TAG_PREFIX_OBSERVATION_NAME + self.observation_name,
        ]


# Simplified implementations for testing - would need real Weaviate integration in production
async def create_collection(agent_name: str, vector_db_url: str) -> str:
    """Mock implementation - would create actual Weaviate collection"""
    return f"Collection_{agent_name}"


async def delete_collection(agent_name: str, vector_db_url: str) -> None:
    """Mock implementation - would delete actual Weaviate collection"""
    pass


async def add_feedbacks(settings: FeedbackSetting, feedbacks: List[Feedback]) -> List[str]:
    """Mock implementation - would store feedbacks in Weaviate"""
    return [f"uuid_{i}" for i in range(len(feedbacks))]


async def get_feedbacks(
    agent_name: str,
    vector_db_url: str,
    offset: int = 0,
    limit: int = -1,
) -> List[Feedback]:
    """Mock implementation - would retrieve feedbacks from Weaviate"""
    return []


async def delete_all_feedbacks(agent_name: str, vector_db_url: str) -> None:
    """Mock implementation - would delete all feedbacks"""
    pass


async def get_feedback_count(agent_name: str, vector_db_url: str) -> int:
    """Mock implementation - would count feedbacks"""
    return 0


async def query_feedbacks(
    settings: FeedbackSetting,
    query: str,
    tags: List[str] | None = None,
) -> List[Feedback]:
    """Mock implementation - would search feedbacks in Weaviate"""
    return []