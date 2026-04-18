"""
AlgoWeaver AI 核心基础设施模块

提供配置管理、日志系统等基础功能
"""

from .config import settings, get_settings, reload_settings, validate_required_settings
from .logger import configure_logging, get_logger, LoggerMixin

__all__ = [
    "settings",
    "get_settings", 
    "reload_settings",
    "validate_required_settings",
    "configure_logging",
    "get_logger",
    "LoggerMixin",
]


def initialize_core():
    """
    初始化核心基础设施
    
    在应用启动时调用此函数进行基础设施初始化
    """
    # 验证必需配置
    validate_required_settings()
    
    # 配置日志系统
    configure_logging()
    
    # 记录初始化完成
    logger = get_logger(__name__)
    logger.info("AlgoWeaver AI 核心基础设施初始化完成")