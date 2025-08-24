# singleton_base.py
from __future__ import annotations
import threading
import inspect
from typing import Any, Dict, Tuple, Optional


class _PerKeySingletonMeta(type):
    """
    线程安全的“按键分组”单例元类：
    - 通过类属性 SINGLETON_KEY 指定用于分组的参数名（例如 "config_name"）
    - 同一类 + 同一 key 值 -> 只会构造一次实例
    - 提供清理 API: clear_instance / clear_all
    """
    _instances: Dict[Tuple[type, str, Any], Any] = {}
    _lock = threading.RLock()

    def __call__(cls, *args, **kwargs):
        key_name: str | None = getattr(cls, "SINGLETON_KEY", None)
        if not key_name:
            # 无 key 时，退化为“类级单例”
            key = (cls, "__class__", None)
        else:
            # 优先从 kwargs 取 key
            if key_name in kwargs:
                key_val = kwargs[key_name]
            else:
                # 从 __init__ 的签名里解析该参数的实参（支持位置参数）
                # 注意：__init__(self, ...) 的第一个形参是 self，这里用占位
                sig = inspect.signature(cls.__init__)
                ba = sig.bind_partial(None, *args, **kwargs)
                key_val = ba.arguments.get(key_name, None)
            key = (cls, key_name, key_val)

        with cls._lock:
            inst = cls._instances.get(key)
            if inst is None:
                inst = super().__call__(*args, **kwargs)  # 正常构造（只一次）
                cls._instances[key] = inst
            return inst

    # -------- 辅助清理 API --------
    def clear_instance(cls, *, key_value: Any = None) -> bool:
        """清理指定 key 的实例；SINGLETON_KEY 必须已设置。返回是否删除成功。"""
        key_name: str | None = getattr(cls, "SINGLETON_KEY", None)
        if not key_name:
            k = (cls, "__class__", None)
            with cls._lock:
                return cls._instances.pop(k, None) is not None
        k = (cls, key_name, key_value)
        with cls._lock:
            return cls._instances.pop(k, None) is not None

    def clear_all(cls) -> int:
        """清理该类的所有实例；返回删除数量。"""
        with cls._lock:
            to_del = [k for k in list(cls._instances.keys()) if k[0] is cls]
            for k in to_del:
                cls._instances.pop(k, None)
            return len(to_del)


class SingletonBase(metaclass=_PerKeySingletonMeta):
    """
    继承此类即可获得单例能力。
    - 设置类属性 SINGLETON_KEY = "<__init__ 里的参数名>"
      即可实现“按该参数值分组的单例”
    - 若不设置 SINGLETON_KEY，则为整个类一个单例
    """
    SINGLETON_KEY: str | None = None

    # 可选：避免重复初始化开销（若你在 __init__ 做了昂贵操作）
    _initialized_flag_attr = "_$__singleton_initialized"

    def _mark_initialized_once(self) -> bool:
        """
        在 __init__ 最开始调用：
        if self._mark_initialized_once(): return
        用于保证昂贵初始化只执行一次（即使外部误用强行再次调用 __init__）
        """
        if getattr(self, self._initialized_flag_attr, False):
            return True
        setattr(self, self._initialized_flag_attr, True)
        return False


