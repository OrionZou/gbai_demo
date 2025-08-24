from typing import List
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel

from agent_runtime.services.reward_service import RewardService, RewardRusult
from agent_runtime.clients.llm.openai_client import LLM
from agent_runtime.config.loader import SettingLoader, LLMSetting

router = APIRouter()


class RewardRequest(BaseModel):
    question: str
    candidates: List[str]
    target_answer: str


# def get_reward_service(llm_client: LLM = Depends(), ) -> RewardService:
#     return RewardService(llm_client)

llm_client = LLM()
reward_service = RewardService(llm_client)


@router.post("/reward")
async def reward_api(request: RewardRequest = Body(
    ...,
    openapi_examples={
        "simple_example": {
            "summary": "简单示例 - 地理题",
            "description": "一个包含五个候选答案的简单例子",
            "value": {
                "question": "世界上最大的海洋是哪个？",
                "candidates": ["大西洋", "太平洋", "印度洋", "北冰洋", "地中海"],
                "target_answer": "太平洋"
            },
        },
        "complex_example": {
            "summary": "复杂示例 - 阅读理解",
            "description": "一个带有五个候选长文本答案的复杂语义比较例子",
            "value": {
                "question":
                "请总结《西游记》中唐僧西天取经的目的。",
                "candidates": [
                    "唐僧带领孙悟空、猪八戒、沙僧历经九九八十一难前往西天取经，为了取得真经。",
                    "唐僧此行是因为皇帝派遣他寻找宝物。", "取经的最终目的，是为了获取佛经，弘扬佛法，普度众生。",
                    "唐僧和徒弟们一路降妖除魔，实际上是为了打败妖怪获得宝藏。", "这个故事主要讲述了团队合作、修行和坚持不懈的精神。"
                ],
                "target_answer":
                "唐僧此次取经的真正目的，是为了弘扬佛法，普度众生。"
            },
        },
    },
)) -> RewardRusult:
    """
    Reward API: 比较多个答案的语义一致性

    你可以在 FastAPI docs (/docs) 中选择示例请求体，快速测试。
    """
    try:
        result = await reward_service.compare_answer(
            question=request.question,
            candidates=request.candidates,
            target_answer=request.target_answer,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reward API 调用失败: {e}")


@router.get("/config")
async def get_config() -> dict:
    """获取当前的 LLM 配置"""
    try:
        config = SettingLoader.get_llm_setting()
        return config.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取配置失败: {e}")


@router.post("/config")
async def set_config(
    cfg: LLMSetting = Body(
        ...,
        openapi_examples={
            "deepseek_example": {
                "summary": "配置 DeepSeek-Chat 模型",
                "description": "使用 DeepSeek Chat 模型及 API Key 的示例",
                "value": {
                    "api_key": "your_key",
                    "model": "deepseek-chat",
                    "base_url": "https://api.deepseek.com/v1",
                    "timeout": 180.0,
                    "max_completion_tokens": 2048,
                    "temperature": 0
                },
            }
        },
    )
) -> dict:
    """
    设置 LLM 配置，并更新全局 llm_client 和 reward_service
    """
    try:
        new_cfg = SettingLoader.set_llm_setting(
            cfg.model_dump(exclude_none=True))
        global llm_client, reward_service
        # 重新构建 LLM 客户端 (简化为使用默认构造函数，内部读取新的 SettingLoader 配置)
        llm_client = LLM(llm_setting=new_cfg)
        reward_service = RewardService(llm_client)
        return {"message": "配置已更新", "config": new_cfg.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新配置失败: {e}")
