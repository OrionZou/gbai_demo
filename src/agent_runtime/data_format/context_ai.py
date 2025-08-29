import hashlib
import json
import copy
import difflib
import tiktoken
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union, Callable
from enum import Enum

from agent_runtime.data_format.message import Message


class TrimStrategy(Enum):
    """Context trimming strategies"""

    FIFO = "fifo"
    IMPORTANCE = "importance"
    TOPIC_CLUSTER = "topic_cluster"


class AIContext:
    """
    Enhanced Agent Context Manager

    Key Features:
    1. 会话状态管理 - 对话历史、系统提示、重置功能
    2. 记忆存取 - 短期记忆（当前会话）和长期记忆（持久化）
    3. 变量管理 - 模板变量与验证
    4. 上下文合并与裁剪 - Token 限制控制，多种策略
    5. 外部资源挂载 - 挂载搜索结果、工具输出
    6. 上下文版本/快照 - 快照与回滚功能
    7. 日志与可视化 - 导出上下文用于调试/监控
    """

    def __init__(
        self, max_tokens: int = 8000, trim_strategy: TrimStrategy = TrimStrategy.FIFO
    ) -> None:
        # 核心消息存储
        self._messages: List[Message] = []
        self._system_prompt: Optional[str] = None
        self._role_info: Dict[str, Any] = {}

        # 记忆管理
        self._short_term_memory: Dict[str, Any] = {}
        self._long_term_memory: Dict[str, Any] = {}
        self._persistent_summaries: List[str] = []

        # 变量管理
        self._variables: Dict[str, Any] = {}
        self._required_variables: set = set()

        # 上下文控制
        self._max_tokens = max_tokens
        self._trim_strategy = trim_strategy

        # 外部资源
        self._external_resources: Dict[str, Any] = {}

        # 版本系统
        self._snapshots: Dict[str, Dict[str, Any]] = {}
        self._version_counter = 0

        # 日志
        self._change_log: List[Dict[str, Any]] = []
        self._created_at = datetime.now()

    # ================ 会话状态管理 ================

    def set_system_prompt(
        self, prompt: str, role_info: Optional[Dict[str, Any]] = None
    ) -> None:
        """设置系统提示和角色信息"""
        self._system_prompt = prompt
        if role_info:
            self._role_info.update(role_info)
        self._log_change(
            "system_prompt_updated", {"prompt": prompt, "role_info": role_info}
        )

    def get_system_prompt(self) -> Optional[str]:
        """获取当前系统提示"""
        return self._system_prompt

    def get_role_info(self) -> Dict[str, Any]:
        """获取角色信息"""
        return self._role_info.copy()

    def add_system_prompt(self, content: str, *, name: Optional[str] = None) -> None:
        """添加系统消息到对话"""
        self._messages.append(Message(role="system", content=content, name=name))
        self._log_change("system_message_added", {"content": content, "name": name})

    def add_user_prompt(self, content: str, *, name: Optional[str] = None) -> None:
        """添加用户消息到对话"""
        self._messages.append(Message(role="user", content=content, name=name))
        self._log_change("user_message_added", {"content": content, "name": name})

    def add_assistant(
        self,
        content: str,
        *,
        name: Optional[str] = None,
        extras: Optional[Dict[str, Any]] = None,
    ) -> None:
        """添加助手消息到对话"""
        self._messages.append(
            Message(role="assistant", content=content, name=name, extras=extras)
        )
        self._log_change(
            "assistant_message_added",
            {"content": content, "name": name, "extras": extras},
        )

    def add_tool(
        self,
        content: str,
        *,
        tool_call_id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> None:
        """添加工具消息到对话"""
        extras = {}
        if tool_call_id:
            extras["tool_call_id"] = tool_call_id
        self._messages.append(
            Message(role="tool", content=content, name=name, extras=extras)
        )
        self._log_change(
            "tool_message_added",
            {"content": content, "tool_call_id": tool_call_id, "name": name},
        )

    def reset(self, keep_system: bool = True, keep_variables: bool = False) -> None:
        """重置上下文到初始状态"""
        self._messages.clear()
        self._short_term_memory.clear()
        self._external_resources.clear()

        if not keep_system:
            self._system_prompt = None
            self._role_info.clear()

        if not keep_variables:
            self._variables.clear()
            self._required_variables.clear()

        self._log_change(
            "context_reset",
            {"keep_system": keep_system, "keep_variables": keep_variables},
        )

    # ================ 记忆存取 ================

    def set_short_term_memory(self, key: str, value: Any) -> None:
        """存储当前会话的短期记忆"""
        self._short_term_memory[key] = value
        self._log_change("short_term_memory_set", {"key": key})

    def get_short_term_memory(self, key: str, default: Any = None) -> Any:
        """获取短期记忆"""
        return self._short_term_memory.get(key, default)

    def clear_short_term_memory(self) -> None:
        """清空所有短期记忆"""
        self._short_term_memory.clear()
        self._log_change("short_term_memory_cleared", {})

    def set_long_term_memory(self, key: str, value: Any) -> None:
        """存储长期记忆（跨会话持久化）"""
        self._long_term_memory[key] = value
        self._log_change("long_term_memory_set", {"key": key})

    def get_long_term_memory(self, key: str, default: Any = None) -> Any:
        """获取长期记忆"""
        return self._long_term_memory.get(key, default)

    def add_summary(self, summary: str) -> None:
        """添加对话总结用于持久化"""
        self._persistent_summaries.append(summary)
        self._log_change("summary_added", {"summary": summary})

    def get_summaries(self) -> List[str]:
        """获取所有对话总结"""
        return self._persistent_summaries.copy()

    # ================ 变量管理 ================

    def set_var(self, key: str, value: Any, required: bool = False) -> None:
        """设置模板变量"""
        self._variables[key] = value
        if required:
            self._required_variables.add(key)
        self._log_change("variable_set", {"key": key, "required": required})

    def get_var(self, key: str, default: Any = None) -> Any:
        """获取模板变量"""
        return self._variables.get(key, default)

    def update_vars(self, variables: Dict[str, Any]) -> None:
        """一次更新多个变量"""
        self._variables.update(variables)
        self._log_change("variables_updated", {"keys": list(variables.keys())})

    def require_var(self, key: str) -> None:
        """标记变量为必填"""
        self._required_variables.add(key)

    def validate_required_vars(self) -> List[str]:
        """检查缺失的必填变量"""
        missing = []
        for var in self._required_variables:
            if var not in self._variables:
                missing.append(var)
        return missing

    def get_all_vars(self) -> Dict[str, Any]:
        """获取所有模板变量"""
        return self._variables.copy()

    # ================ 上下文合并与裁剪 ================

    def get_current_tokens(self, model: str = "gpt-4o-mini") -> int:
        """获取当前 token 数量"""
        return self.count_tokens(model=model)

    def needs_trimming(self, model: str = "gpt-4o-mini") -> bool:
        """检查是否需要裁剪上下文"""
        return self.get_current_tokens(model) > self._max_tokens

    def trim_context(
        self, model: str = "gpt-4o-mini", target_ratio: float = 0.8
    ) -> int:
        """使用配置的策略裁剪上下文"""
        current_tokens = self.get_current_tokens(model)
        if current_tokens <= self._max_tokens:
            return 0

        target_tokens = int(self._max_tokens * target_ratio)

        if self._trim_strategy == TrimStrategy.FIFO:
            return self._trim_fifo(target_tokens, model)
        elif self._trim_strategy == TrimStrategy.IMPORTANCE:
            return self._trim_by_importance(target_tokens, model)
        else:  # TOPIC_CLUSTER
            return self._trim_by_topic(target_tokens, model)

    def _trim_fifo(self, target_tokens: int, model: str) -> int:
        """FIFO 策略：优先删除最旧的消息"""
        removed_count = 0
        while (
            len(self._messages) > 1 and self.get_current_tokens(model) > target_tokens
        ):
            # 保留系统消息
            for i, msg in enumerate(self._messages):
                if msg.role != "system":
                    self._messages.pop(i)
                    removed_count += 1
                    break
            else:
                break
        return removed_count

    def _trim_by_importance(self, target_tokens: int, model: str) -> int:
        """重要性策略：优先删除不重要的消息（工具调用等）"""
        removed_count = 0
        importance_order = ["tool", "user", "assistant", "system"]

        for role_to_remove in importance_order:
            while (
                len(self._messages) > 1
                and self.get_current_tokens(model) > target_tokens
            ):
                removed = False
                for i, msg in enumerate(self._messages):
                    if msg.role == role_to_remove and (
                        role_to_remove != "system" or i > 0
                    ):
                        self._messages.pop(i)
                        removed_count += 1
                        removed = True
                        break
                if not removed:
                    break
            if self.get_current_tokens(model) <= target_tokens:
                break

        return removed_count

    def _trim_by_topic(self, target_tokens: int, model: str) -> int:
        """主题聚类策略（简化实现）"""
        # 目前回退到 FIFO - 主题聚类需要 NLP 实现
        return self._trim_fifo(target_tokens, model)

    def merge_conversations(self, other_context: "AIContext") -> None:
        """合并另一个上下文的消息到当前上下文"""
        self._messages.extend(other_context._messages)
        self._variables.update(other_context._variables)
        self._external_resources.update(other_context._external_resources)
        self._log_change(
            "context_merged", {"messages_added": len(other_context._messages)}
        )

    # ================ 外部资源挂载 ================

    def attach(self, resource_name: str, resource_data: Any) -> None:
        """挂载外部资源（搜索结果、工具输出等）"""
        self._external_resources[resource_name] = resource_data
        self._log_change("resource_attached", {"resource_name": resource_name})

    def detach(self, resource_name: str) -> Any:
        """卸载并返回外部资源"""
        resource = self._external_resources.pop(resource_name, None)
        if resource is not None:
            self._log_change("resource_detached", {"resource_name": resource_name})
        return resource

    def get_resource(self, resource_name: str, default: Any = None) -> Any:
        """获取外部资源"""
        return self._external_resources.get(resource_name, default)

    def list_resources(self) -> List[str]:
        """列出所有已挂载的资源名称"""
        return list(self._external_resources.keys())

    # ================ 上下文版本/快照 ================

    def checkpoint(self, checkpoint_name: Optional[str] = None) -> str:
        """创建检查点快照"""
        if checkpoint_name is None:
            checkpoint_name = f"checkpoint_{self._version_counter}"
            self._version_counter += 1

        snapshot = {
            "messages": [m.to_openai_format() for m in self._messages],
            "system_prompt": self._system_prompt,
            "role_info": self._role_info.copy(),
            "variables": self._variables.copy(),
            "short_term_memory": self._short_term_memory.copy(),
            "external_resources": copy.deepcopy(self._external_resources),
            "timestamp": datetime.now().isoformat(),
        }

        self._snapshots[checkpoint_name] = snapshot
        self._log_change("checkpoint_created", {"checkpoint_name": checkpoint_name})
        return checkpoint_name

    def rollback(self, checkpoint_name: str) -> bool:
        """回滚到指定检查点"""
        if checkpoint_name not in self._snapshots:
            return False

        snapshot = self._snapshots[checkpoint_name]

        # 恢复状态
        self._messages = [Message.from_openai_format(m) for m in snapshot["messages"]]
        self._system_prompt = snapshot["system_prompt"]
        self._role_info = snapshot["role_info"]
        self._variables = snapshot["variables"]
        self._short_term_memory = snapshot["short_term_memory"]
        self._external_resources = snapshot["external_resources"]

        self._log_change("rollback_executed", {"checkpoint_name": checkpoint_name})
        return True

    def list_checkpoints(self) -> List[str]:
        """列出所有可用检查点"""
        return list(self._snapshots.keys())

    def delete_checkpoint(self, checkpoint_name: str) -> bool:
        """删除检查点"""
        if checkpoint_name in self._snapshots:
            del self._snapshots[checkpoint_name]
            self._log_change("checkpoint_deleted", {"checkpoint_name": checkpoint_name})
            return True
        return False

    # ================ 遗留快照方法（增强版） ================

    def snapshot(self, snap_id: str, *, model: str = "gpt-4o-mini") -> None:
        """遗留快照方法 - 使用完整状态增强"""
        msgs_dump = [m.to_openai_format() for m in self._messages]
        blob = json.dumps(msgs_dump, ensure_ascii=False, sort_keys=True)
        h = hashlib.sha256(blob.encode("utf-8")).hexdigest()
        tks = self.count_tokens(model=model)

        # 存储增强的快照数据
        snapshot_data = (
            h,
            tks,
            msgs_dump,
            {
                "variables": self._variables.copy(),
                "resources": copy.deepcopy(self._external_resources),
                "timestamp": datetime.now().isoformat(),
            },
        )

        self._snapshots[snap_id] = snapshot_data

    def snapshot_with_copy(self, snap_id: str, *, model: str = "gpt-4o-mini") -> None:
        """支持保存副本的快照方法"""
        self.snapshot(snap_id, model=model)

    def diff_since(
        self, snap_id: str, *, model: str = "gpt-4o-mini", return_text_diff: bool = True
    ) -> Dict[str, Any]:
        """增强的差异比较，包含变量和资源变化"""
        if snap_id not in self._snapshots:
            raise KeyError(f"Snapshot '{snap_id}' not found")

        snapshot_data = self._snapshots[snap_id]

        if len(snapshot_data) >= 4:
            prev_hash, prev_tokens, prev_msgs, prev_extras = snapshot_data
            prev_vars = prev_extras.get("variables", {})
            prev_resources = prev_extras.get("resources", {})
        else:
            # 遗留格式兼容
            prev_hash, prev_tokens = snapshot_data[:2]
            prev_msgs = snapshot_data[2] if len(snapshot_data) > 2 else []
            prev_vars = {}
            prev_resources = {}

        cur_hash = self._hash_messages()
        cur_tokens = self.count_tokens(model=model)
        cur_msgs = [m.to_openai_format() for m in self._messages]

        # 消息差异
        added, removed, modified = self._struct_diff(prev_msgs, cur_msgs)

        # 变量差异
        var_changes = self._diff_dicts(prev_vars, self._variables)

        # 资源差异
        resource_changes = self._diff_dicts(prev_resources, self._external_resources)

        result = {
            "changed": prev_hash != cur_hash,
            "token_delta": cur_tokens - prev_tokens,
            "current_tokens": cur_tokens,
            "snapshot_tokens": prev_tokens,
            "messages": {"added": added, "removed": removed, "modified": modified},
            "variables": var_changes,
            "resources": resource_changes,
        }

        if return_text_diff:
            result["text_diff"] = self._text_diff_from_strings(
                self._concat_text(prev_msgs), self._concat_text(cur_msgs)
            )

        return result

    # ================ Token 计数 ================

    def count_tokens(
        self,
        model: str = "gpt-4o-mini",
        *,
        fallback_chars_per_token: int = 4,
        include_roles: bool = True,
    ) -> int:
        """增强精度的 token 计数"""
        if tiktoken is not None:
            try:
                enc = tiktoken.encoding_for_model(model)
            except Exception:
                enc = tiktoken.get_encoding("cl100k_base")

            total = 0

            # 系统提示
            if self._system_prompt:
                total += len(enc.encode(self._system_prompt))

            # 消息
            for m in self._messages:
                text = (m.role + ": " if include_roles else "") + (str(m.content) or "")
                total += len(enc.encode(text))

            # 变量（如果会被渲染）
            for key, value in self._variables.items():
                if isinstance(value, str):
                    total += len(enc.encode(f"{key}: {value}"))

            return total

        # 回退估算
        total_chars = 0
        if self._system_prompt:
            total_chars += len(self._system_prompt)

        for m in self._messages:
            text = (m.role + ": " if include_roles else "") + (str(m.content) or "")
            total_chars += len(text)

        for key, value in self._variables.items():
            if isinstance(value, str):
                total_chars += len(f"{key}: {value}")

        return max(1, total_chars // max(1, fallback_chars_per_token))

    # ================ 导出与可视化 ================

    def to_openai_format(self) -> List[Dict[str, Any]]:
        """导出为 OpenAI 格式消息"""
        messages = []

        # 添加系统提示（如果存在）
        if self._system_prompt:
            messages.append({"role": "system", "content": self._system_prompt})

        # 添加对话消息
        messages.extend([m.to_openai_format() for m in self._messages])

        return messages

    def export_context(self, include_logs: bool = False) -> Dict[str, Any]:
        """导出完整上下文用于调试/监控"""
        context_data = {
            "messages": self.to_openai_format(),
            "system_prompt": self._system_prompt,
            "role_info": self._role_info,
            "variables": self._variables,
            "required_variables": list(self._required_variables),
            "short_term_memory": self._short_term_memory,
            "long_term_memory": self._long_term_memory,
            "summaries": self._persistent_summaries,
            "external_resources": {
                k: str(type(v)) for k, v in self._external_resources.items()
            },
            "checkpoints": list(self._snapshots.keys()),
            "config": {
                "max_tokens": self._max_tokens,
                "trim_strategy": self._trim_strategy.value,
            },
            "stats": {
                "current_tokens": self.get_current_tokens(),
                "message_count": len(self._messages),
                "created_at": self._created_at.isoformat(),
            },
        }

        if include_logs:
            context_data["change_log"] = self._change_log

        return context_data

    def get_conversation_summary(self) -> str:
        """生成当前对话的摘要"""
        if not self._messages:
            return "Empty conversation"

        user_messages = [m for m in self._messages if m.role == "user"]
        assistant_messages = [m for m in self._messages if m.role == "assistant"]

        summary = f"Conversation with {len(user_messages)} user messages and {len(assistant_messages)} assistant responses."

        if self._variables:
            summary += f" Variables: {list(self._variables.keys())}"

        if self._external_resources:
            summary += f" External resources: {list(self._external_resources.keys())}"

        return summary

    # ================ 内部辅助方法 ================

    def _hash_messages(self) -> str:
        """生成当前消息的哈希"""
        payload = [m.to_openai_format() for m in self._messages]
        blob = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def _log_change(self, action: str, details: Dict[str, Any]) -> None:
        """记录上下文变化"""
        self._change_log.append(
            {
                "timestamp": datetime.now().isoformat(),
                "action": action,
                "details": details,
            }
        )

    @staticmethod
    def _struct_diff(
        prev: List[Dict[str, Any]], cur: List[Dict[str, Any]]
    ) -> Tuple[List[Any], List[Any], List[Any]]:
        """比较消息结构"""
        added, removed, modified = [], [], []
        n_prev, n_cur = len(prev), len(cur)
        n = max(n_prev, n_cur)

        for i in range(n):
            p = prev[i] if i < n_prev else None
            c = cur[i] if i < n_cur else None

            if p is None and c is not None:
                added.append({"index": i, "cur": c})
            elif p is not None and c is None:
                removed.append({"index": i, "prev": p})
            else:
                if (p.get("role") != c.get("role")) or (
                    p.get("content") != c.get("content")
                ):
                    modified.append({"index": i, "prev": p, "cur": c})

        return added, removed, modified

    @staticmethod
    def _diff_dicts(prev: Dict[str, Any], cur: Dict[str, Any]) -> Dict[str, Any]:
        """比较两个字典"""
        added = {k: v for k, v in cur.items() if k not in prev}
        removed = {k: v for k, v in prev.items() if k not in cur}
        modified = {
            k: {"prev": prev[k], "cur": cur[k]}
            for k in prev.keys() & cur.keys()
            if prev[k] != cur[k]
        }

        return {"added": added, "removed": removed, "modified": modified}

    @staticmethod
    def _concat_text(msgs: List[Dict[str, Any]]) -> str:
        """拼接消息用于文本差异"""
        lines = []
        for i, m in enumerate(msgs):
            role = m.get("role", "")
            content = m.get("content", "")
            lines.append(f"[{i}] {role}: {content}")
        return "\n".join(lines)

    @staticmethod
    def _text_diff_from_strings(a: str, b: str) -> str:
        """生成两个字符串的统一差异"""
        diff = difflib.unified_diff(
            a.splitlines(keepends=False),
            b.splitlines(keepends=False),
            fromfile="snapshot",
            tofile="current",
            lineterm="",
            n=2,
        )
        return "\n".join(diff)
