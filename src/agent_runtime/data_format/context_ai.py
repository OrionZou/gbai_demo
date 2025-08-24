import hashlib
import json
import difflib
import tiktoken
from typing import Any, Dict, List, Optional, Tuple

from agent_runtime.data_format.message import Message


class AIContext:
    """
    - 管理对话消息
    - 导出为 OpenAI 接口消息格式
    - 估算 token 消耗（优先 tiktoken，失败则近似估算）
    - 生成/比较快照，得到缓存差异与 token 差异
    """

    def __init__(self) -> None:
        self._messages: List[Message] = []
        self._snapshots: Dict[str,
                              Tuple[str,
                                    int]] = {}  # snap_id -> (hash, tokens)

    # ------------- 添加消息的便捷接口 -------------
    def add_system_prompt(self,
                          content: str,
                          *,
                          name: Optional[str] = None) -> None:
        self._messages.append(
            Message(role="system", content=content, name=name))

    def add_user_prompt(self,
                        content: str,
                        *,
                        name: Optional[str] = None) -> None:
        self._messages.append(Message(role="user", content=content, name=name))

    def add_assistant(self,
                      content: str,
                      *,
                      name: Optional[str] = None,
                      extras: Optional[Dict[str, Any]] = None) -> None:
        self._messages.append(
            Message(role="assistant",
                    content=content,
                    name=name,
                    extras=extras))

    def add_tool(self,
                 content: str,
                 *,
                 tool_call_id: Optional[str] = None,
                 name: Optional[str] = None) -> None:
        extras = {}
        if tool_call_id:
            extras["tool_call_id"] = tool_call_id
        self._messages.append(
            Message(role="tool", content=content, name=name, extras=extras))

    # ------------- 导出为 OpenAI 接口格式 -------------
    def to_openai_format(self) -> List[Dict[str, Any]]:
        return [m.to_openai_format() for m in self._messages]

    # ------------- Token 估算 -------------
    def count_tokens(
        self,
        model: str = "gpt-4o-mini",
        *,
        fallback_chars_per_token: int = 4,
        include_roles: bool = True,
    ) -> int:
        """
        返回当前 context 的“估算” token 数。
        - 优先使用 tiktoken；如果不可用，则采用字符长度近似：len(text) // fallback_chars_per_token
        - include_roles: 将 role 名一并计入（更保守）
        """
        # 1) tiktoken
        if tiktoken is not None:
            try:
                enc = tiktoken.encoding_for_model(model)
            except Exception:
                enc = tiktoken.get_encoding("cl100k_base")

            total = 0
            for m in self._messages:
                text = (m.role + ": " if include_roles else "") + (m.content
                                                                   or "")
                total += len(enc.encode(text))
            return total

        # 2) 近似估算
        total_chars = 0
        for m in self._messages:
            text = (m.role + ": " if include_roles else "") + (m.content or "")
            total_chars += len(text)
        return max(1, total_chars // max(1, fallback_chars_per_token))

    # ------------- 快照与差异 -------------
    def _hash_messages(self) -> str:
        payload = [m.to_openai_format() for m in self._messages]
        blob = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def snapshot(self, snap_id: str, *, model: str = "gpt-4o-mini") -> None:
        """
        记录当前 context 的哈希与 token 数到 _snapshots[snap_id]
        """
        h = self._hash_messages()
        tks = self.count_tokens(model=model)
        self._snapshots[snap_id] = (h, tks)

    def diff_since(
        self,
        snap_id: str,
        *,
        model: str = "gpt-4o-mini",
        return_text_diff: bool = True,
    ) -> Dict[str, Any]:
        """
        与快照 snap_id 对比，返回：
        - changed: bool
        - token_delta: int（当前 - 快照时）
        - added / removed / modified（逐条消息级别）
        - optional: text_diff（基于全文拼接的统一 diff）
        """
        if snap_id not in self._snapshots:
            raise KeyError(f"Snapshot '{snap_id}' not found")

        prev_hash, prev_tokens = self._snapshots[snap_id]
        cur_hash = self._hash_messages()
        cur_tokens = self.count_tokens(model=model)

        changed = prev_hash != cur_hash

        # 消息级别的增删改：以 index 对齐
        prev_msgs = []  # 需要从快照还原；这里通过 hash 无法直接取历史内容
        # ——为了避免保存全部历史副本，下面提供一种“现用现比”的简洁方式：对比文本拼接。
        # 如果你希望消息级 diff 更精确，可在 snapshot 时同时保存消息列表副本（占用更多内存）。
        # 这里给出“同时保存副本”的版本（推荐）：
        # 将 _snapshots 的 value 从 (hash, tokens) 扩展为 (hash, tokens, messages_dump)

        # 升级：保存消息副本
        # 注：为兼容已有快照，这里做一次“旧结构兼容”
        snap_val = self._snapshots[snap_id]
        if len(snap_val) == 2:
            # 旧结构：只保存 hash/tokens，则无法做结构化的逐条 diff，用文本 diff 代替
            added = removed = modified = []
            text_diff = self._text_diff_from_strings(
                self._concat_text([]),
                self._concat_text([m.to_openai() for m in self._messages]),
            ) if return_text_diff else None
        else:
            # 新结构：包含消息副本
            _, _, prev_dump = snap_val  # type: ignore
            added, removed, modified = self._struct_diff(
                prev_dump, [m.to_openai() for m in self._messages])
            text_diff = self._text_diff_from_strings(
                self._concat_text(prev_dump),
                self._concat_text([m.to_openai() for m in self._messages]),
            ) if return_text_diff else None

        return {
            "changed": changed,
            "token_delta": cur_tokens - prev_tokens,
            "current_tokens": cur_tokens,
            "snapshot_tokens": prev_tokens,
            "added": added,
            "removed": removed,
            "modified": modified,
            "text_diff": text_diff,
        }

    # --- 为了更强的结构化 diff，提供一个支持“保存副本”的快照方法 ---
    def snapshot_with_copy(self,
                           snap_id: str,
                           *,
                           model: str = "gpt-4o-mini") -> None:
        msgs_dump = [m.to_openai_format() for m in self._messages]
        blob = json.dumps(msgs_dump, ensure_ascii=False, sort_keys=True)
        h = hashlib.sha256(blob.encode("utf-8")).hexdigest()
        tks = self.count_tokens(model=model)
        # 保存三元组（hash, tokens, messages_dump）
        self._snapshots[snap_id] = (h, tks, msgs_dump)

    # ------------- 内部：结构化 diff 与文本 diff -------------
    @staticmethod
    def _struct_diff(
            prev: List[Dict[str, Any]],
            cur: List[Dict[str,
                           Any]]) -> Tuple[List[Any], List[Any], List[Any]]:
        """
        基于 index 的简洁 diff：长度对齐后比较 role/content 是否一致。
        返回 (added, removed, modified)，元素为 {index, prev, cur}
        """
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
                # 都存在：检查关键字段
                if (p.get("role") != c.get("role")) or (p.get("content")
                                                        != c.get("content")):
                    modified.append({"index": i, "prev": p, "cur": c})
        return added, removed, modified

    @staticmethod
    def _concat_text(msgs: List[Dict[str, Any]]) -> str:
        lines = []
        for i, m in enumerate(msgs):
            role = m.get("role", "")
            content = m.get("content", "")
            lines.append(f"[{i}] {role}: {content}")
        return "\n".join(lines)

    @staticmethod
    def _text_diff_from_strings(a: str, b: str) -> str:
        diff = difflib.unified_diff(
            a.splitlines(keepends=False),
            b.splitlines(keepends=False),
            fromfile="snapshot",
            tofile="current",
            lineterm="",
            n=2,
        )
        return "\n".join(diff)
