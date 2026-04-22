"""
Checkpointer 工厂模块

提供统一的 checkpointer 创建逻辑，确保整个应用使用相同的持久化策略。
"""

from typing import Optional
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

from app.core.config import get_settings
from app.core.logger import get_logger

logger = get_logger(__name__)

# 全局 checkpointer 实例缓存（用于应用）
_checkpointer_instance: Optional[BaseCheckpointSaver] = None


def create_checkpointer() -> BaseCheckpointSaver:
    """
    创建 checkpointer 实例

    根据配置创建合适的 checkpointer 实例。
    当前使用 MemorySaver，未来可以扩展支持 Redis 等持久化存储。

    Returns:
        BaseCheckpointSaver: checkpointer 实例

    Note:
        此函数每次调用都会创建新实例，适用于：
        - LangGraph Studio（独立进程）
        - 测试环境
        - 需要隔离状态的场景
    """
    settings = get_settings()

    # TODO: 根据配置选择不同的 checkpointer 类型
    # if settings.checkpointer_type == "redis":
    #     from langgraph.checkpoint.redis import RedisSaver
    #     return RedisSaver(...)

    # 默认使用内存存储
    logger.debug("创建 MemorySaver checkpointer")
    return MemorySaver()


def get_checkpointer() -> BaseCheckpointSaver:
    """
    获取全局 checkpointer 实例（单例模式）

    用于应用运行时，确保所有图共享同一个 checkpointer 实例。

    Returns:
        BaseCheckpointSaver: 全局 checkpointer 实例

    Note:
        此函数返回单例实例，适用于：
        - FastAPI 应用运行时
        - 需要共享状态的场景
    """
    global _checkpointer_instance

    if _checkpointer_instance is None:
        _checkpointer_instance = create_checkpointer()
        logger.info("全局 checkpointer 实例创建成功")

    return _checkpointer_instance


def clear_checkpointer_cache():
    """
    清除 checkpointer 缓存

    用于测试或配置更新后重新初始化 checkpointer。
    """
    global _checkpointer_instance
    _checkpointer_instance = None
    logger.info("checkpointer 缓存已清除")
