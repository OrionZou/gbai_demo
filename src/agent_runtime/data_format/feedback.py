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


