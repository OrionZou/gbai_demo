import sys
from pathlib import Path
from threading import Lock
from typing import Dict
from loguru import logger as _logger


class SingletonMeta(type):
    _instances = {}
    _lock: Lock = Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class Logger(metaclass=SingletonMeta):
    """
    日志路由策略：
      1) 控制台：统一输出
      2) 汇总文件：logs/all.log 记录所有日志
      3) 分模块文件：agent/base.py -> logs/agent/base.log
    """

    def __init__(
        self,
        root_dir: str = "logs",
        level: str = "DEBUG",
        rotation: str = "10 MB",
        retention: str = "7 days",
        compression: str = "zip",
        aggregate_filename: str = "all.log",  # 汇总日志文件名
        enable_console: bool = True,
        enable_aggregate: bool = True,
        enable_per_module: bool = True,
    ):
        self.root_dir = Path(root_dir).resolve()
        self.root_dir.mkdir(parents=True, exist_ok=True)

        self.level = level
        self.rotation = rotation
        self.retention = retention
        self.compression = compression
        self.enable_console = enable_console
        self.enable_aggregate = enable_aggregate
        self.enable_per_module = enable_per_module

        self._module_sinks: Dict[str, int] = {}
        self._lock = Lock()

        self._fmt_console = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>")
        self._fmt_file = ("{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
                          "{name}:{function}:{line} - {message}")

        # 移除默认 sink
        _logger.remove()

        # 1) 控制台
        if self.enable_console:
            _logger.add(sys.stdout, level=self.level, format=self._fmt_console)

        # 2) 汇总文件（所有日志都会写入）
        if self.enable_aggregate:
            aggregate_path = self.root_dir / aggregate_filename
            aggregate_path.parent.mkdir(parents=True, exist_ok=True)
            _logger.add(
                aggregate_path,
                level=self.level,
                rotation=self.rotation,
                retention=self.retention,
                compression=self.compression,
                enqueue=True,
                encoding="utf-8",
                format=self._fmt_file,
            )

        # 3) 路由 sink：用于按模块名动态创建专属文件 sink
        if self.enable_per_module:
            _logger.add(self._route_by_module,
                        level=self.level,
                        format=self._fmt_file,
                        enqueue=True)

        self._logger = _logger

    # 动态路由：把日志按模块名写到 logs/<package>/<module>.log
    def _route_by_module(self, message):
        record = message.record
        module_name: str = record.get("name") or record.get(
            "module") or "__main__"

        parts = module_name.split(".")
        subdir = self.root_dir.joinpath(
            *parts[:-1]) if len(parts) > 1 else self.root_dir
        subdir.mkdir(parents=True, exist_ok=True)
        file_path = subdir / f"{parts[-1]}.log"

        # 若该模块还没有专属 sink，则创建（并把当前这条日志手动补写一行，避免“首条丢失”）
        if module_name not in self._module_sinks:
            with self._lock:
                if module_name not in self._module_sinks:
                    sink_id = _logger.add(
                        file_path,
                        level=self.level,
                        rotation=self.rotation,
                        retention=self.retention,
                        compression=self.compression,
                        enqueue=True,
                        encoding="utf-8",
                        format=self._fmt_file,
                        filter=lambda r, mn=module_name: r["name"] == mn,
                    )
                    self._module_sinks[module_name] = sink_id
                    # 当前这条 message 不会被刚创建的 sink 捕获，手动补写
                    with file_path.open("a", encoding="utf-8") as f:
                        f.write(str(message))

    @property
    def instance(self):
        return self._logger


# 项目里这样用即可（无需改调用点）
logger = Logger().instance
