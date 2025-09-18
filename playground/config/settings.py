"""
应用配置设置
"""
import os


class AppConfig:
    """应用配置"""
    
    # API配置
    DEFAULT_API_URL = "http://localhost:8011"
    API_TIMEOUT = 600
    
    # 并发配置
    DEFAULT_MAX_CONCURRENT = 10
    MAX_CONCURRENT_OPTIONS = [1, 3, 5, 8, 10, 15]
    
    # 文件上传配置
    MAX_FILE_SIZE_MB = 10
    SUPPORTED_FILE_TYPES = ['csv', 'json']
    
    # UI配置
    PAGE_TITLE = "🤖 Agent Runtime API Playground"
    PAGE_DESCRIPTION = "用于测试和验证 Agent Runtime API 功能"
    
    # 表格配置
    MAX_PREVIEW_ROWS = 15
    MAX_DETAILED_ITEMS = 10
    DEFAULT_MANUAL_ITEMS = 3
    
    # 导出配置
    EXPORT_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"
    
    @classmethod
    def get_api_url(cls) -> str:
        """获取API URL"""
        return os.getenv("AGENT_RUNTIME_API_URL", cls.DEFAULT_API_URL)
    
    @classmethod
    def get_max_concurrent(cls) -> int:
        """获取默认最大并发数"""
        return int(os.getenv("MAX_CONCURRENT", cls.DEFAULT_MAX_CONCURRENT))


class UIConfig:
    """UI配置"""
    
    # 页面标签配置
    TAB_CONFIG = [
        {"name": "⚙️ LLM配置", "key": "config"},
        {"name": "🏆 Reward API", "key": "reward"},
        {"name": "↩️ Backward API", "key": "backward"},
        {"name": "🔧 BQA Extract", "key": "bqa_extract"},
        {"name": "📊 OSPA 表格", "key": "ospa"},
        {"name": "🤖 Agent管理", "key": "agent"}
    ]
    
    # 列配置
    OSPA_COLUMNS = [
        {"key": "no", "name": "序号", "width": "small", "disabled": True},
        {"key": "O", "name": "O", "width": "medium", "help": "观察/用户输入"},
        {"key": "S", "name": "S", "width": "small", "help": "状态/场景"},
        {"key": "p", "name": "p", "width": "large", "help": "提示词"},
        {"key": "A", "name": "A", "width": "medium", "help": "Agent输出/标准答案"},
        {"key": "A_prime", "name": "A'", "width": "medium", "help": "候选答案（用于一致性比较）"},
        {"key": "consistency", "name": "consistency", "width": "small", "help": "一致性得分", "format": "%.3f"},
        {"key": "confidence_score", "name": "confidence_score", "width": "small", "help": "置信度", "format": "%.3f"},
        {"key": "error", "name": "error", "width": "medium", "help": "错误信息"}
    ]
    
    # 颜色配置
    COLORS = {
        "success": "#28a745",
        "error": "#dc3545", 
        "warning": "#ffc107",
        "info": "#17a2b8",
        "primary": "#007bff"
    }
    
    # 图标配置
    ICONS = {
        "success": "✅",
        "error": "❌", 
        "warning": "⚠️",
        "info": "💡",
        "loading": "🔄",
        "download": "📥",
        "upload": "📤",
        "edit": "✏️",
        "delete": "🗑️",
        "add": "➕",
        "save": "💾"
    }