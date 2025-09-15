from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

from agent_runtime.clients.openai_llm_client import LLM
from agent_runtime.logging.logger import logger
from agent_runtime.agents.reward_agent import RewardAgent


class PairwiseJudge(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    index: int = Field(..., description="候选答案在输入数组中的下标")
    label: str
    confidence: float = Field(..., ge=0, le=1)
    reason: str


class RewardRusult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    question: str
    target_answer: str
    results: List[PairwiseJudge]


class RewardService:

    def __init__(self, llm_client: LLM):
        self.llm_client = llm_client
        
        # 初始化全局上下文
        from agent_runtime.data_format.context import AIContext
        self.global_context = AIContext()
        self.global_context.add_system_prompt("你是一个专业的答案评审助手，负责评估候选答案与目标答案的语义一致性。")
        
        self.reward_agent = RewardAgent(llm_engine=llm_client)
        
        logger.info("RewardService initialized with global context and RewardAgent")

    def get_global_context(self):
        """获取全局上下文"""
        return self.global_context
    
    def update_global_context(self, context) -> None:
        """更新全局上下文"""
        self.global_context = context
        logger.info("Global context updated for RewardService")

    def update_prompts(
        self,
        system_prompt: Optional[str] = None,
        user_prompt_template: Optional[str] = None,
    ) -> None:
        """
        更新系统提示词和用户提示词模板

        Args:
            system_prompt: 新的系统提示词，如果为None则不更新
            user_prompt_template: 新的用户提示词模板，如果为None则不更新
        """
        if system_prompt is not None:
            self.reward_agent.update_system_prompt(system_prompt)
            logger.info("System prompt updated")

        if user_prompt_template is not None:
            self.reward_agent.update_user_template(user_prompt_template)
            logger.info("User prompt template updated")

    async def compare_answer(
        self, question: str, candidates: List[str], target_answer: str
    ) -> RewardRusult:
        """
        使用 RewardAgent 比较候选答案与目标答案的语义匹配度。
        返回结构包含：原因、分数
        """
        # 使用全局上下文调用agent step方法
        json_list = await self.reward_agent.step(
            context=self.global_context,
            question=question,
            target_answer=target_answer,
            candidates=candidates,
        )

        results = []
        for data in json_list:
            results.append(PairwiseJudge(**data))
        return RewardRusult(
            question=question, target_answer=target_answer, results=results
        )
