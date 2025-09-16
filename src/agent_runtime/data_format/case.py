import uuid

from typing import List, Optional, Union, Dict, Any, Annotated
from pydantic import BaseModel, Field

from agent_runtime.data_format.message import Message
from agent_runtime.data_format.content import ContentPart
from agent_runtime.logging.logger import logger


class Observation(BaseModel):
    """
    表示一次观测信息（Observation）
    """
    message: Union[str, List["Message"]] = Field(
        ..., description="观测内容，可以是字符串或 Message 列表")
    metadata: Optional[Dict[str, Any]] = Field(default=None,
                                               description="附加元数据，例如标签、上下文信息")

    class Config:
        json_schema_extra = {
            "examples": [
                # ✅ 简单字符串观测
                {
                    "message": "用户观察到异常：温度过高",
                    "metadata": {
                        "sensor": "manual",
                        "priority": "high"
                    }
                },
                # ✅ 单条 Message 观测
                {
                    "message": {
                        "role": "user",
                        "role_name": "alice",
                        "content": "你好，今天的天气怎么样？",
                        "created_at": "2025-08-21T15:30:00+08:00"
                    },
                    "metadata": {
                        "context": "chat",
                        "topic": "weather"
                    }
                },
                # ✅ 多条 Message 观测
                {
                    "message": [{
                        "role": "system",
                        "role_name": "system-1",
                        "content": "你是一个有帮助的助手。",
                        "created_at": "2025-08-21T15:25:00+08:00"
                    }, {
                        "role":
                        "user",
                        "role_name":
                        "bob",
                        "content": [{
                            "type": "text",
                            "text": "帮我查一下今天上海的天气"
                        }],
                        "created_at":
                        "2025-08-21T15:26:00+08:00"
                    }],
                    "metadata": {
                        "session_id": "chat-001",
                        "topic": "weather"
                    }
                }
            ]
        }


class MemoryState(BaseModel):
    """
    记忆状态
    - state_name: 状态名称
    - tag_dict: LLM 根据 state_name 生成的标签
    """

    state_name: str = Field(..., description="记忆状态名称")

    # TODO: tag_dict
    # tag_dict: Dict[str, str] = Field(
    #     default_factory=dict,
    #     description="由 LLM 自动生成的标签字典"
    # )

    # @field_validator("tag_dict", mode="before")
    # @classmethod
    # def generate_tags(cls, v, values):
    #     if v and isinstance(v, dict):
    #         return v  # 已提供则直接用
    #     state_name = values.get("state_name")
    #     return generate_tags_from_llm(state_name)

    # class Config:
    #     json_schema_extra = {
    #         "examples": [{
    #             "state_name": "用户请求天气信息",
    #             "tag_dict": {
    #                 "角色": "用户",
    #                 "上下文": "对话"
    #             },
    #         }, {
    #             "state_name": "系统错误日志",
    #             "tag_dict": {
    #                 "角色": "系统",
    #                 "功能": "控制"
    #             },
    #         }]
    #     }


class OSPARound(BaseModel):
    """多轮对话中的一轮"""
    case_id: str = Field(..., description="案例id")
    round_id: str = Field(..., description="回合id")
    last_rounds: List[str] = Field([], description="上轮关联对话")
    next_rounds: List[str] = Field([], description="下轮关联对话")
    o: Observation = Field(..., description="观测信息")
    s: MemoryState = Field(..., description="当前记忆信息")
    p: Union[str, List["ContentPart"]] = Field(..., description="记忆信息管理细节")
    a: str = Field(..., description="回复")

    def to_weaviate_properties(self) -> dict:
        """转换为 Weaviate properties（不含 class 信息）"""

        def dump_content(p: Union[str, List["ContentPart"]]) -> Any:
            if isinstance(p, list):
                return [
                    c.model_dump() if hasattr(c, "model_dump") else str(c)
                    for c in p
                ]
            if hasattr(p, "model_dump"):
                return p.model_dump()
            return p

        return {
            "case_id": self.case_id,
            "round_id": self.round_id,
            "last_rounds": self.last_rounds,
            "next_rounds": self.next_rounds,
            "o": self.o.model_dump(),
            "s": self.s.model_dump(),
            "p": dump_content(self.p),
            "a": self.a,
        }

    def save_to_weaviate(self, client: "WeaviateClient") -> None:
        """使用项目中的 WeaviateClient 保存对象"""
        props = self.to_weaviate_properties()
        client.create_object("OSPARound", props)


class MultiRoundCase(BaseModel):
    """一个多轮对话案例"""
    case_id: str = Field(default_factory=lambda: str(uuid.uuid4().hex),
                         description="案例id，自动生成")
    rounds: Annotated[List[OSPARound], Field(description="多轮对话")] = []

    # ---------- 基本检索 ----------
    def get_round(self, round_id: str) -> OSPARound:
        for r in self.rounds:
            if r.round_id == round_id:
                return r
        raise KeyError(f"round_id 不存在: {round_id}")

    def has_round(self, round_id: str) -> bool:
        return any(r.round_id == round_id for r in self.rounds)

    # ---------- 增量添加 ----------
    def add_round(
        self,
        o: "Observation",
        s: "MemoryState",
        p: Union[str, List["ContentPart"]],
        a: str,
        last_round_ids: Optional[str] = None,
        # round_id: Optional[str] = None,
    ) -> OSPARound:
        """
        追加一轮 OSPA，并自动维护 last/next 链接。
        - last_round_ids 为空表示这是起始回合（无父）
        - round_id 不传则自动生成
        """
        rid = str(uuid.uuid4().hex)
        last_ids = list(last_round_ids or [])

        # 父引用校验
        if last_ids:
            for lr in last_ids:
                if not self.has_round(lr):
                    logger.warning(f"last_round_id 不存在: {lr}")
                    raise ValueError(f"last_round_id 不存在: {lr}")

        if self.rounds:
            self.rounds[-1].next_rounds = [rid]
            last_ids.append(self.rounds[-1].round_id)

        new_round = OSPARound(
            case_id=self.case_id,
            round_id=rid,
            last_rounds=last_ids,
            next_rounds=[],
            o=o,
            s=s,
            p=p,
            a=a,
        )

        # 写入
        self.rounds.append(new_round)

        # 维护父 -> 子 的 next_rounds
        for lr in last_ids:
            parent = self.get_round(lr)
            if new_round.round_id not in parent.next_rounds:
                parent.next_rounds.append(new_round.round_id)

        return new_round

    # ---------- 手动补链 ----------
    def link_rounds(self, src_round_id: str, dst_round_id: str) -> None:
        """手动建立 src -> dst 的有向边"""
        src = self.get_round(src_round_id)
        dst = self.get_round(dst_round_id)
        if dst_round_id not in src.next_rounds:
            src.next_rounds.append(dst_round_id)
        if src_round_id not in dst.last_rounds:
            dst.last_rounds.append(src_round_id)

    # ---------- 校验 ----------
    def validate_graph(self) -> None:
        """
        校验：
        1) 引用的 round_id 必须存在
        2) 回边一致性：A.next 含 B，则 B.last 必含 A；反之亦然
        3) 简单环检测（DFS）
        """
        idset = {r.round_id for r in self.rounds}
        idx: Dict[str, OSPARound] = {r.round_id: r for r in self.rounds}

        # 1) 引用存在
        for r in self.rounds:
            for x in r.last_rounds + r.next_rounds:
                if x not in idset:
                    raise ValueError(f"引用了不存在的 round_id: {x}")

        # 2) 回边一致
        for r in self.rounds:
            for nx in r.next_rounds:
                if r.round_id not in idx[nx].last_rounds:
                    raise ValueError(f"不一致: {r.round_id} -> {nx} 缺少回边")
            for ls in r.last_rounds:
                if r.round_id not in idx[ls].next_rounds:
                    raise ValueError(f"不一致: {ls} -> {r.round_id} 缺少回边")

        # 3) 简单环检测
        visited, stack = set(), set()

        def dfs(u: str) -> None:
            if u in stack:
                raise ValueError(f"检测到环: {u}")
            if u in visited:
                return
            visited.add(u)
            stack.add(u)
            for v in idx[u].next_rounds:
                dfs(v)
            stack.remove(u)

        for r in self.rounds:
            dfs(r.round_id)

    # ---------- 导出 ----------
    def to_mermaid(self) -> str:
        """导出 mermaid flowchart（按 round_id 连边）"""
        lines = ["flowchart TD"]
        # 节点
        for r in self.rounds:
            title = (r.a[:16] + "…") if len(r.a) > 16 else r.a
            lines.append(f'    {r.round_id}["{title}"]')
        # 边
        for r in self.rounds:
            for nx in r.next_rounds:
                lines.append(f"    {r.round_id} --> {nx}")
        return "\n".join(lines)
