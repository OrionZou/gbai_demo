from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, List, Optional, Literal, Union, Any
import uuid
import json
from pathlib import Path

from .message import Message


class AIContext(BaseModel):
    """
    AI对话上下文管理器，使用UUID作为key存储Message
    支持增删Message，按时间范围、role和name过滤
    
    存储模式：
    - 默认：纯内存模式（高性能，不持久化）
    - 可选：文件存储模式（数据持久化）
    
    使用方式：
    - AIContext() 或 AIContext.create_memory_only() - 纯内存模式
    - AIContext.create_with_storage() - 文件存储模式
    """

    messages: Dict[str, Message] = Field(
        default_factory=dict, description="使用UUID作为key的Message字典"
    )

    context_name: str = Field(default="default", description="上下文名称，用于文件存储")

    storage_path: Optional[Path] = Field(
        default_factory=lambda: Path("context_storage"), 
        description="上下文存储路径，为None时不存储到文件"
    )
    
    enable_storage: bool = Field(
        default=False,
        description="是否启用文件存储，False时为纯内存模式（默认）"
    )
    
    # Token统计字段
    total_input_tokens: int = Field(default=0, description="总输入token数")
    total_output_tokens: int = Field(default=0, description="总输出token数")
    cache_hit_tokens: int = Field(default=0, description="缓存命中的token数")
    cache_miss_tokens: int = Field(default=0, description="缓存未命中的token数")

    def __init__(self, **data):
        super().__init__(**data)
        # 只有启用存储且路径不为None时才创建目录
        if self.enable_storage and self.storage_path is not None:
            self.storage_path.mkdir(parents=True, exist_ok=True)

    def add_message(self, message: Message) -> str:
        """
        添加消息到上下文

        Args:
            message: Message对象

        Returns:
            str: 消息的UUID
        """
        # 生成新的UUID作为消息ID
        message_id = str(uuid.uuid4())

        # 添加到内存
        self.messages[message_id] = message

        # 同步到文件（仅在启用存储时）
        if self.enable_storage and self.storage_path is not None:
            self._sync_to_file(message, message_id)

        return message_id

    def remove_message(self, message_id: str) -> bool:
        """
        从上下文中移除消息

        Args:
            message_id: 消息UUID

        Returns:
            bool: 是否成功移除
        """
        if message_id in self.messages:
            message = self.messages[message_id]
            del self.messages[message_id]

            # 从文件中移除（仅在启用存储时）
            if self.enable_storage and self.storage_path is not None:
                self._remove_from_file(message, message_id)

            return True
        return False

    def filter_messages(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        role: Optional[Literal["system", "user", "assistant", "tool"]] = None,
        name: Optional[str] = None,
    ) -> "AIContext":
        """
        根据条件过滤消息，返回新的AIContext实例

        Args:
            start_time: 开始时间
            end_time: 结束时间
            role: 消息角色
            name: 角色名称

        Returns:
            AIContext: 包含过滤后消息的新上下文
        """
        filtered_messages = {}

        for msg_id, message in self.messages.items():
            # 时间范围过滤
            if start_time and message.created_at < start_time:
                continue
            if end_time and message.created_at > end_time:
                continue

            # 角色过滤
            if role and message.role != role:
                continue

            # 名称过滤
            if name and message.name != name:
                continue

            filtered_messages[msg_id] = message

        # 创建新的上下文实例（继承存储设置）
        filtered_context = AIContext(
            messages=filtered_messages,
            context_name=f"{self.context_name}_filtered",
            storage_path=self.storage_path,
            enable_storage=self.enable_storage,
        )

        return filtered_context

    def get_messages_by_time_order(self, ascending: bool = True) -> List[Message]:
        """
        按时间顺序获取消息列表

        Args:
            ascending: 是否升序排列

        Returns:
            List[Message]: 按时间排序的消息列表
        """
        messages = list(self.messages.values())
        messages.sort(key=lambda x: x.created_at, reverse=not ascending)
        return messages

    def _sync_to_file(self, message: Message, message_id: str):
        """
        将消息同步到对应的存储文件

        Args:
            message: 要同步的消息
            message_id: 消息的唯一标识符
        """
        # 如果存储路径为None，直接返回
        if self.storage_path is None:
            return
            
        # 根据role_name分文件存储
        if message.name:
            role_name = f"{message.role}_{message.name}"
            file_path = self.storage_path / f"{role_name}.json"
        else:
            role_name = message.role
            file_path = self.storage_path / f"{role_name}.json"

        # 全局context文件
        global_file_path = self.storage_path / f"{self.context_name}_global.json"

        # 读取现有文件内容
        role_data = self._load_file_data(file_path)
        global_data = self._load_file_data(global_file_path)

        # 添加或更新消息
        message_dict = message.model_dump()
        role_data[message_id] = message_dict
        global_data[message_id] = message_dict

        # 写入文件
        self._save_file_data(file_path, role_data)
        self._save_file_data(global_file_path, global_data)

    def _remove_from_file(self, message: Message, message_id: str):
        """
        从存储文件中移除消息

        Args:
            message: 要移除的消息
            message_id: 消息的唯一标识符
        """
        # 如果存储路径为None，直接返回
        if self.storage_path is None:
            return
            
        # 确定文件路径
        if message.name:
            role_name = f"{message.role}_{message.name}"
            file_path = self.storage_path / f"{role_name}.json"
        else:
            role_name = message.role
            file_path = self.storage_path / f"{role_name}.json"

        global_file_path = self.storage_path / f"{self.context_name}_global.json"

        # 从文件中移除
        role_data = self._load_file_data(file_path)
        global_data = self._load_file_data(global_file_path)

        role_data.pop(message_id, None)
        global_data.pop(message_id, None)

        # 如果role文件变空，删除文件；否则保存更新后的数据
        if role_data:
            self._save_file_data(file_path, role_data)
        elif file_path.exists():
            try:
                file_path.unlink()
            except OSError as e:
                print(f"删除空文件失败 {file_path}: {e}")

        # 保存全局文件
        self._save_file_data(global_file_path, global_data)

    def _load_file_data(self, file_path: Path) -> Dict:
        """
        从文件加载数据

        Args:
            file_path: 文件路径

        Returns:
            Dict: 文件中的数据
        """
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save_file_data(self, file_path: Path, data: Dict):
        """
        保存数据到文件

        Args:
            file_path: 文件路径
            data: 要保存的数据
        """
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        except IOError as e:
            print(f"保存文件失败 {file_path}: {e}")

    def load_from_storage(self) -> int:
        """
        从存储文件加载上下文

        Returns:
            int: 加载的消息数量
        """
        # 如果未启用存储，返回0
        if not self.enable_storage or self.storage_path is None:
            return 0
            
        global_file_path = self.storage_path / f"{self.context_name}_global.json"

        if not global_file_path.exists():
            return 0

        data = self._load_file_data(global_file_path)
        loaded_count = 0

        for msg_id, msg_data in data.items():
            try:
                # 从字典创建Message对象
                message = Message(**msg_data)
                self.messages[msg_id] = message
                loaded_count += 1
            except Exception as e:
                print(f"加载消息失败 {msg_id}: {e}")

        return loaded_count

    def clear_context(self):
        """
        清空上下文和所有相关文件
        """
        # 清空内存
        self.messages.clear()
        
        # 如果未启用存储，直接返回
        if not self.enable_storage or self.storage_path is None:
            return
            
        # 收集要删除的文件列表
        files_to_delete = set()
        
        # 1. 添加全局文件
        global_file = self.storage_path / f"{self.context_name}_global.json"
        if global_file.exists():
            files_to_delete.add(global_file)
        
        # 2. 从全局文件读取所有消息，以确保找到所有相关文件
        all_messages = []
        if global_file.exists():
            global_data = self._load_file_data(global_file)
            for msg_data in global_data.values():
                try:
                    message = Message(**msg_data)
                    all_messages.append(message)
                except Exception:
                    continue
        
        # 3. 根据全局文件中的所有消息，找到所有相关的role_name文件
        for message in all_messages:
            if message.name:
                role_name_file = self.storage_path / f"{message.role}_{message.name}.json"
            else:
                role_name_file = self.storage_path / f"{message.role}.json"
            
            if role_name_file.exists():
                files_to_delete.add(role_name_file)

        # 删除所有相关文件
        for file_path in files_to_delete:
            try:
                file_path.unlink()
            except OSError as e:
                print(f"删除文件失败 {file_path}: {e}")

    def to_openai_format(self, include_system: bool = True) -> List[Dict]:
        """
        转换为 OpenAI ChatML 格式
        
        Args:
            include_system: 是否包含系统消息
            
        Returns:
            List[Dict]: OpenAI ChatML 格式的消息列表
        """
        messages = self.get_messages_by_time_order(ascending=True)
        openai_messages = []
        
        for message in messages:
            # 可选择跳过系统消息
            if not include_system and message.role == "system":
                continue
                
            openai_message = message.to_openai_format()
            openai_messages.append(openai_message)
        
        return openai_messages
    
    def to_openai_format_filtered(
        self,
        role: Optional[Literal["system", "user", "assistant", "tool"]] = None,
        name: Optional[str] = None,
        include_system: bool = True
    ) -> List[Dict]:
        """
        根据条件过滤后转换为 OpenAI ChatML 格式
        
        Args:
            role: 过滤的角色
            name: 过滤的名称
            include_system: 是否包含系统消息
            
        Returns:
            List[Dict]: 过滤后的 OpenAI ChatML 格式消息列表
        """
        filtered_context = self.filter_messages(role=role, name=name)
        return filtered_context.to_openai_format(include_system=include_system)
    
    @classmethod
    def from_openai_format(
        cls,
        openai_messages: List[Dict],
        context_name: str = "openai_import",
        storage_path: Optional[Path] = None,
        enable_storage: bool = False
    ) -> "AIContext":
        """
        从 OpenAI ChatML 格式创建 AIContext
        
        Args:
            openai_messages: OpenAI ChatML 格式的消息列表
            context_name: 上下文名称
            storage_path: 存储路径
            enable_storage: 是否启用文件存储
            
        Returns:
            AIContext: 新的上下文实例
        """
        if storage_path is None and enable_storage:
            storage_path = Path("context_storage")
            
        context = cls(
            context_name=context_name, 
            storage_path=storage_path,
            enable_storage=enable_storage
        )
        
        for openai_msg in openai_messages:
            try:
                message = Message.from_openai_format(openai_msg)
                context.add_message(message)
            except Exception as e:
                print(f"导入消息失败: {e}")
                continue
        
        return context

    def add_input_tokens(self, tokens: int, cache_hit: bool = False):
        """
        添加输入token统计
        
        Args:
            tokens: token数量
            cache_hit: 是否为缓存命中
        """
        self.total_input_tokens += tokens
        if cache_hit:
            self.cache_hit_tokens += tokens
        else:
            self.cache_miss_tokens += tokens

    def add_output_tokens(self, tokens: int):
        """
        添加输出token统计
        
        Args:
            tokens: token数量
        """
        self.total_output_tokens += tokens

    def get_token_stats(self) -> Dict[str, Union[int, float]]:
        """
        获取token统计信息
        
        Returns:
            Dict[str, int]: token统计数据
        """
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "cache_hit_tokens": self.cache_hit_tokens,
            "cache_miss_tokens": self.cache_miss_tokens,
            "cache_hit_rate": (
                self.cache_hit_tokens / self.total_input_tokens 
                if self.total_input_tokens > 0 else 0.0
            )
        }

    def reset_token_stats(self):
        """
        重置token统计
        """
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.cache_hit_tokens = 0
        self.cache_miss_tokens = 0

    @classmethod
    def create_memory_only(cls, context_name: str = "memory_context") -> "AIContext":
        """
        创建纯内存模式的上下文（不存储到文件）
        
        Args:
            context_name: 上下文名称
            
        Returns:
            AIContext: 纯内存模式的上下文实例
        """
        return cls(
            context_name=context_name,
            storage_path=None,
            enable_storage=False
        )

    @classmethod
    def create_with_storage(
        cls, 
        context_name: str = "stored_context",
        storage_path: Optional[Path] = None
    ) -> "AIContext":
        """
        创建启用文件存储的上下文
        
        Args:
            context_name: 上下文名称
            storage_path: 存储路径，默认为 context_storage
            
        Returns:
            AIContext: 启用存储的上下文实例
        """
        if storage_path is None:
            storage_path = Path("context_storage")
            
        return cls(
            context_name=context_name,
            storage_path=storage_path,
            enable_storage=True
        )

    def get_context_stats(self) -> Dict:
        """
        获取上下文统计信息

        Returns:
            Dict: 统计信息
        """
        if not self.messages:
            return {"total_messages": 0}

        role_counts: Dict[str, int] = {}
        name_counts: Dict[str, int] = {}

        for message in self.messages.values():
            # 统计角色
            role_counts[message.role] = role_counts.get(message.role, 0) + 1

            # 统计名称
            if message.name:
                name_counts[message.name] = name_counts.get(message.name, 0) + 1

        # 时间范围
        messages_by_time = self.get_messages_by_time_order()
        earliest = messages_by_time[0].created_at if messages_by_time else None
        latest = messages_by_time[-1].created_at if messages_by_time else None

        return {
            "total_messages": len(self.messages),
            "role_counts": role_counts,
            "name_counts": name_counts,
            "time_range": {"earliest": earliest, "latest": latest},
            "token_stats": self.get_token_stats(),
        }

    # Compatibility methods for context_ai.py interface
    def add_system_prompt(self, content: str, *, name: Optional[str] = None) -> str:
        """添加系统消息到上下文（兼容方法）"""
        message = Message(role="system", content=content, name=name)
        return self.add_message(message)

    def add_user_prompt(self, content: str, *, name: Optional[str] = None) -> str:
        """添加用户消息到上下文（兼容方法）"""
        message = Message(role="user", content=content, name=name)
        return self.add_message(message)

    def add_assistant(self, content: str, *, name: Optional[str] = None, extras: Optional[Dict[str, Any]] = None) -> str:
        """添加助手消息到上下文（兼容方法）"""
        message = Message(role="assistant", content=content, name=name, extras=extras)
        return self.add_message(message)

    def add_tool(self, content: str, *, tool_call_id: Optional[str] = None, name: Optional[str] = None) -> str:
        """添加工具消息到上下文（兼容方法）"""
        extras = {}
        if tool_call_id:
            extras["tool_call_id"] = tool_call_id
        message = Message(role="tool", content=content, name=name, extras=extras)
        return self.add_message(message)

    def get_current_tokens(self, model: str = "gpt-4o-mini") -> int:
        """获取当前token数量（兼容方法）"""
        try:
            import tiktoken
            try:
                enc = tiktoken.encoding_for_model(model)
            except:
                enc = tiktoken.get_encoding("cl100k_base")
            
            total = 0
            for message in self.messages.values():
                text = f"{message.role}: {message.content}"
                total += len(enc.encode(str(text)))
            return total
        except ImportError:
            # 回退到字符数估算
            total_chars = sum(len(str(msg.content)) + len(msg.role) + 2 for msg in self.messages.values())
            return max(1, total_chars // 4)
