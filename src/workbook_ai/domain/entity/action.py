from typing import Dict, List
from pydantic import BaseModel, Field


class Action(BaseModel):
    """动作定义"""
    name: str = Field(..., description="动作名称")
    description: str = Field(..., description="动作描述")
    params: Dict[str, str] = Field(default_factory=dict, description="动作参数")


class ActionLib(BaseModel):
    """动作库，即动作的集合"""
    actions: List[Action] = Field(default_factory=list)