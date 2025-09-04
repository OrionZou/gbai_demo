from pydantic import BaseModel



class OSPA(BaseModel):
    """OSPA数据模型
    
    OSPA是用于结构化知识表示的四元组模型，包含目标、场景、提示和答案四个维度。
    
    Attributes:
        o (str): Objective - 目标，通常是用户的问题或查询内容
        s (str): Scenario - 场景，描述问题所属的上下文或章节信息
        p (str): Prompt - 提示，指导LLM如何基于特定场景回答问题的提示词
        a (str): Answer - 答案，对应问题的标准答案
    """
    o: str  # Objective - 目标问题
    s: str  # Scenario - 场景上下文
    p: str  # Prompt - 辅助提示词
    a: str  # Answer - 标准答案
