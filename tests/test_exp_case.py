@/exps/entity/exp_case.py 在一个测试方法，使用到 Observation 中 message 的结果

import pytest

from workbook_ai.domain.entity.case import (
    Observation,
    MemoryState,
    MultiRoundCase,
)
from workbook_ai.domain.entity.content import ContentPart


def test_multi_round_case_observation_message():
    case = MultiRoundCase(description="电商客服对话")

    # 第 1 轮
    r1 = case.add_round(
        o=Observation(message="用户：你好，我的订单没到"),
        s=MemoryState(state_name="接入"),
        p=[ContentPart(type="text", text="初始化记忆")],
        a="您好，我来帮您查看订单状态。",
    )

    # 第 2 轮
    r2 = case.add_round(
        o=Observation(message="订单号是 123456"),
        s=MemoryState(state_name="获取订单号"),
        p=[ContentPart(type="text", text="记录到 memory：order_id=123456")],
        a="收到，我正在查询，请稍等片刻。",
    )

    # 第 3 轮
    r3 = case.add_round(
        o=Observation(message="请问今天能到吗？"),
        s=MemoryState(state_name="物流催问"),
        p=[ContentPart(type="markdown", markdown="**加急** 处理物流查询")],
        a="预计今晚 20:00 前送达。",
    )

    # 断言 Observation.message
    assert r1.observation.message == "用户：你好，我的订单没到"
    assert r2.observation.message == "订单号是 123456"
    assert r3.observation.message == "请问今天能到吗？"

    # 断言 ContentPart 在 props 中
    assert isinstance(r1.props[0], ContentPart)
    assert r1.props[0].text == "初始化记忆"
    assert r2.props[0].text.startswith("记录到 memory")
    assert r3.props[0].type == "markdown"