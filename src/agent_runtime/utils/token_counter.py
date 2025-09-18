"""
Token统计模块 - 单例模式实现

用于统计LLM API调用的token消耗，支持会话级别的统计和查询。
"""

import threading
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
import uuid
from collections import OrderedDict

from agent_runtime.logging.logger import logger


@dataclass
class TokenUsage:
    """单次API调用的token使用记录"""
    timestamp: datetime
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    request_id: Optional[str] = None


@dataclass
class SessionStats:
    """会话级别的token统计"""
    session_id: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    total_requests: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    last_update: datetime = field(default_factory=datetime.now)
    details: List[TokenUsage] = field(default_factory=list)


class TokenCounter:
    """
    Token计数器 - 单例模式实现

    线程安全的token使用量统计器，支持多会话并发统计。
    会话数量限制为500，使用先进先出(FIFO)策略管理。
    """

    _instance = None
    _lock = threading.Lock()
    MAX_SESSIONS = 500  # 最大会话数量

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # 避免重复初始化
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._sessions: OrderedDict[str, SessionStats] = OrderedDict()
            self._global_stats = SessionStats(session_id="__global__")
            self._lock = threading.RLock()  # 使用可重入锁

    def create_session(self, session_id: Optional[str] = None) -> str:
        """
        创建新的统计会话，支持FIFO限制

        Args:
            session_id: 可选的会话ID，如果不提供则自动生成

        Returns:
            str: 会话ID
        """
        if session_id is None:
            session_id = str(uuid.uuid4())

        with self._lock:
            # 如果会话已存在，更新访问时间（移到末尾）
            if session_id in self._sessions:
                self._sessions.move_to_end(session_id)
                return session_id

            # 检查会话数量限制
            if len(self._sessions) >= self.MAX_SESSIONS:
                # 移除最旧的会话（FIFO）
                oldest_session_id, _ = self._sessions.popitem(last=False)
                logger.info(f"Session limit reached, removed oldest session: {oldest_session_id}")

            # 创建新会话
            self._sessions[session_id] = SessionStats(session_id=session_id)

        return session_id

    def record_usage(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str = "unknown",
        session_id: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> None:
        """
        记录token使用量

        Args:
            input_tokens: 输入token数
            output_tokens: 输出token数
            model: 使用的模型名称
            session_id: 会话ID，如果为None则记录到全局统计
            request_id: 可选的请求ID
        """
        total_tokens = input_tokens + output_tokens
        usage = TokenUsage(
            timestamp=datetime.now(),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            request_id=request_id
        )

        with self._lock:
            # 更新全局统计
            self._update_stats(self._global_stats, usage)

            # 更新会话统计
            if session_id:
                if session_id in self._sessions:
                    # 更新现有会话并移到末尾（标记为最近访问）
                    self._sessions.move_to_end(session_id)
                    self._update_stats(self._sessions[session_id], usage)
                else:
                    # 自动创建会话（会自动处理FIFO限制）
                    self.create_session(session_id)
                    self._update_stats(self._sessions[session_id], usage)

    def _update_stats(self, stats: SessionStats, usage: TokenUsage) -> None:
        """更新统计数据（内部方法）"""
        stats.input_tokens += usage.input_tokens
        stats.output_tokens += usage.output_tokens
        stats.total_tokens += usage.total_tokens
        stats.total_requests += 1
        stats.last_update = datetime.now()
        stats.details.append(usage)

    def get_session_stats(self, session_id: str) -> Optional[SessionStats]:
        """
        获取指定会话的统计数据

        Args:
            session_id: 会话ID

        Returns:
            SessionStats: 会话统计数据，如果会话不存在则返回None
        """
        with self._lock:
            return self._sessions.get(session_id)

    def get_global_stats(self) -> SessionStats:
        """获取全局统计数据"""
        with self._lock:
            return self._global_stats

    def get_all_sessions(self) -> Dict[str, SessionStats]:
        """获取所有会话统计"""
        with self._lock:
            return dict(self._sessions)

    def get_session_count(self) -> int:
        """获取当前会话数量"""
        with self._lock:
            return len(self._sessions)

    def get_oldest_sessions(self, count: int = 10) -> List[str]:
        """获取最旧的N个会话ID"""
        with self._lock:
            return list(self._sessions.keys())[:count]

    def get_newest_sessions(self, count: int = 10) -> List[str]:
        """获取最新的N个会话ID"""
        with self._lock:
            session_keys = list(self._sessions.keys())
            return session_keys[-count:] if len(session_keys) >= count else session_keys

    def reset_session(self, session_id: str) -> None:
        """重置指定会话的统计"""
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id] = SessionStats(session_id=session_id)

    def reset_global(self) -> None:
        """重置全局统计"""
        with self._lock:
            self._global_stats = SessionStats(session_id="__global__")

    def reset_all(self) -> None:
        """重置所有统计"""
        with self._lock:
            self._sessions.clear()
            self._global_stats = SessionStats(session_id="__global__")

    def get_summary(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        获取统计摘要

        Args:
            session_id: 会话ID，如果为None则返回全局摘要

        Returns:
            Dict: 包含统计摘要的字典
        """
        stats = self.get_session_stats(session_id) if session_id else self._global_stats

        if not stats:
            return {}

        return {
            "session_id": stats.session_id,
            "input_tokens": stats.input_tokens,
            "output_tokens": stats.output_tokens,
            "total_tokens": stats.total_tokens,
            "total_requests": stats.total_requests,
            "average_input_tokens": stats.input_tokens / max(1, stats.total_requests),
            "average_output_tokens": stats.output_tokens / max(1, stats.total_requests),
            "start_time": stats.start_time.isoformat(),
            "last_update": stats.last_update.isoformat(),
            "duration_seconds": (stats.last_update - stats.start_time).total_seconds()
        }

    def cleanup_old_sessions(self, hours: int = 24) -> int:
        """
        清理指定时间之前的会话

        Args:
            hours: 保留最近多少小时的会话

        Returns:
            int: 清理的会话数量
        """
        from datetime import timedelta

        cutoff_time = datetime.now() - timedelta(hours=hours)
        sessions_to_remove = []

        with self._lock:
            for session_id, stats in self._sessions.items():
                if stats.last_update < cutoff_time:
                    sessions_to_remove.append(session_id)

            for session_id in sessions_to_remove:
                del self._sessions[session_id]

        return len(sessions_to_remove)


# 全局实例获取函数
def get_token_counter() -> TokenCounter:
    """获取TokenCounter单例实例"""
    return TokenCounter()