from workbook_ai.domain.entity.case import (
    Observation,
    MemoryState,
    MultiRoundCase,
)

from workbook_ai.domain.entity.content import ContentPart
from workbook_ai.domain.entity.message import Message


def run1():
    # 1) 初始化一个案例
    case = MultiRoundCase(description="电商客服对话")

    # 2) 添加第 1 轮（无父）
    r1 = case.add_round(
        o=Observation(message="用户：你好，我的订单没到"),
        s=MemoryState(state_name="接入"),
        p=[ContentPart(type="text", text="初始化记忆")],
        a="您好，我来帮您查看订单状态。",
    )

    # 3) 添加第 2 轮（父为 r1）
    r2 = case.add_round(
        o=Observation(message="订单号是 123456"),
        s=MemoryState(state_name="获取订单号"),
        p=[ContentPart(type="text", text="记录到 memory：order_id=123456")],
        a="收到，我正在查询，请稍等片刻。",
    )

    # 4) 添加第 3 轮（父为 r2）
    r3 = case.add_round(
        o=Observation(message="请问今天能到吗？"),
        s=MemoryState(state_name="物流催问"),
        p=[ContentPart(type="markdown", markdown="**加急** 处理物流查询")],
        a="预计今晚 20:00 前送达。",
    )

    print(case.to_mermaid())


def run2():
    case = MultiRoundCase(description="电商客服对话（class message）")
    m = Message(content=[ContentPart(type="text", text="用户：你好！")])
    o = Observation(message=[m])
    s = MemoryState(state_name="接入")
    p = [ContentPart(type="text", text="初始化记忆")]
    a = "您好，我来帮您查看订单状态。"
    r1 = case.add_round(
        o=o,
        s=s,
        p=p,
        a=a,
    )

    r2 = case.add_round(
        o=Observation(message=[
            Message(content=[ContentPart(type="text", text="订单号是 123456")])
        ]),
        s=MemoryState(state_name="获取订单号"),
        p=[ContentPart(type="text", text="记录到 memory：order_id=123456")],
        a="收到，我正在查询，请稍等片刻。",
    )

    print(case.to_mermaid())


if __name__ == "__main__":

    run1()
    run2()
