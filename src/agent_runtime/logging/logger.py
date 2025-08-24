from loguru import logger
import sys
from pathlib import Path
from threading import Lock


class SingletonMeta(type):
    """线程安全的单例元类"""
    _instances = {}
    _lock: Lock = Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class Logger(metaclass=SingletonMeta):

    def __init__(self,
                 log_dir: str = "logs/ai_knowledge_base",
                 log_file: str = "app.log",
                 level: str = "DEBUG",
                 rotation: str = "10 MB",
                 retention: str = "7 days",
                 compression: str = "zip"):
        """
        基于 loguru 的单例 Logger 类
        :param log_dir: 日志目录
        :param log_file: 日志文件名
        :param level: 日志级别
        :param rotation: 日志轮转策略（大小/时间）
        :param retention: 日志保留时间
        :param compression: 日志压缩格式
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.log_dir / log_file

        # 移除默认 handler
        logger.remove()

        # 控制台输出
        logger.add(
            sys.stdout,
            level=level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>")

        # 文件输出
        logger.add(
            self.log_path,
            level=level,
            rotation=rotation,
            retention=retention,
            compression=compression,
            enqueue=True,  # 多进程安全
            encoding="utf-8",
            format=
            "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
        )

        self._logger = logger

    @property
    def instance(self):
        """返回 loguru.logger 单例"""
        return self._logger


logger = Logger().instance
