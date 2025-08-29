import asyncio
from pydantic import BaseModel, Field

from agent_runtime.clients.llm.openai_client import LLM  # 你的类所在路径
from agent_runtime.data_format.context_ai import AIContext
from agent_runtime.config.loader import LLMSetting

llm = LLM(config_name=LLMSetting.model)


async def demo_ask() -> None:
    ctx = AIContext()
    ctx.add_system_prompt("You are a concise assistant.")
    ctx.add_user_prompt("用一句话解释什么是向量数据库。")

    # 非流式
    text = await llm.ask(ctx.to_openai_format(), stream=False)
    print("\n[非流式结果]\n", text)

    # 流式（控制台会边生成边打印；函数最终返回完整文本）
    text_streamed = await llm.ask(ctx.to_openai_format(), stream=True)
    print("\n[流式最终拼接结果]\n", text_streamed)


async def demo_ask_tool() -> None:

    # 定义一个“加法器”工具
    tools = [{
        "type": "function",
        "function": {
            "name": "add",
            "description": "Add two numbers and return the sum.",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {
                        "type": "number"
                    },
                    "b": {
                        "type": "number"
                    }
                },
                "required": ["a", "b"],
                "additionalProperties": False
            }
        }
    }]

    ctx = AIContext()
    ctx.add_system_prompt("You can decide to call tools when helpful.")
    ctx.add_user_prompt("请用工具把 3 和 4 相加，然后告诉我结果。")

    # 让模型决定是否调用工具（tool_choice="auto"）
    message = await llm.ask_tool(messages=ctx.to_openai_format(),
                                 tools=tools,
                                 tool_choice="auto",
                                 temperature=0.0)

    # 返回的是 OpenAI SDK 的 message 对象（或等价字典）
    print("[模型返回的消息对象]", message)

    # 如果模型决定调用工具，一般会在 message.tool_calls 里
    tool_calls = getattr(message, "tool_calls", None)
    if tool_calls:
        for call in tool_calls:
            print(
                "Tool call -> name:",
                call.function.name,
                "args:",
                call.function.arguments,
            )
    else:
        print("模型没有调用工具，直接给出答案：", message.content)


# 定义期望的结构化返回模型（类，而非实例）


class PlaceInfo(BaseModel):
    name: str = Field(..., description="地名")
    country: str = Field(..., description="国家")
    population_millions: float = Field(..., ge=0, description="人口（百万）")
    fun_fact: str = Field(..., description="一个简短有趣的事实")


async def demo_structured_output() -> None:

    ctx = AIContext()
    ctx.add_system_prompt(
        "Return ONLY data that fits the schema. No extra fields.")
    ctx.add_user_prompt("请以结构化方式给我介绍一下东京（Tokyo）。")

    # 这里把“类”传给 response_format
    result: PlaceInfo = await llm.structured_output(
        messages=ctx.to_openai_format(),
        response_format=PlaceInfo,
        temperature=0.0,
    )

    # result 已是 PlaceInfo 的实例，可直接访问字段
    print("name:", result.name)
    print("country:", result.country)
    print("population_millions:", result.population_millions)
    print("fun_fact:", result.fun_fact)


if __name__ == "__main__":
    asyncio.run(demo_ask())
    asyncio.run(demo_ask_tool())
    asyncio.run(demo_structured_output())
