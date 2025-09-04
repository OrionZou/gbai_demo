from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from agent_runtime.data_format.qa_format import QAList, CQAList
from agent_runtime.data_format.chapter_format import ChapterStructure
from agent_runtime.data_format.ospa import OSPA


class BackwardV2Request(BaseModel):
    """Backward V2 服务请求"""
    
    qa_lists: List[QAList] = Field(..., description="Q&A二维列表，第一维区分多个多轮对话，第二维区分多轮对话中的多个Q&A")
    chapter_structure: Optional[ChapterStructure] = Field(None, description="可选的章节目录")
    max_level: int = Field(3, description="章节目录最大层数")


class BackwardV2Response(BaseModel):
    """Backward V2 服务响应"""
    
    chapter_structure: ChapterStructure = Field(..., description="最终的章节目录结构")
    ospa_list: List[OSPA] = Field(..., description="生成的OSPA列表")
    operation_log: List[str] = Field(default_factory=list, description="操作日志")