from pydantic import BaseModel
from typing import Optional


class V2Action(BaseModel):
    name: str
    arguments: Optional[dict] = None
    result: Optional[dict] = None
