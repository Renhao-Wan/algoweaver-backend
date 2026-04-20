"""
API 依赖注入模块

提供 FastAPI 路由所需的依赖项，包括配置、LLM 实例、Graph 实例等。
"""

from typing import Generator, Optional
from functools import lru_cache

from fastapi import Depends, HTTPException, status
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver

from app.core.config import Settings, get_settings
from app.core.logger import get_logger
from app.graph.main_graph import MainGraphManager

logger = get_logger(__name__)


# ============================================================================
# 配置依赖
# ============================================================================

def get_config() -> Settings:
    """
    获取应用配置

    Returns:
        Settings: 配置实例
    """
    return get_settings()


# ============================================================================
# LLM 依赖
# ============================================================================

@lru_cache()
def get_llm(settings: Settings = Depends(get_config)) -> ChatOpenAI:
    """
    获取 LLM 实例

    使用缓存确保单例，避免重复创建 LLM 实例。

    Args:
        settings: 应用配置

    Returns:
        ChatOpenAI: LLM 实例
    """
    try:
        llm = ChatOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_api_base,
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )
        logger.debug(f"创建 LLM 实例: {settings.llm_model}")
        return llm
    except Exception as e:
        logger.error(f"创建 LLM 实例失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM 初始化失败: {str(e)}"
        )


# ============================================================================
# Graph 依赖
# ============================================================================

@lru_cache()
def get_graph_manager(
    llm: ChatOpenAI = Depends(get_llm)
) -> MainGraphManager:
    """
    获取主图管理器实例

    使用缓存确保单例，避免重复构建图。

    Args:
        llm: LLM 实例

    Returns:
        MainGraphManager: 主图管理器实例
    """
    try:
        # 创建 Checkpointer（使用内存存储）
        checkpointer = MemorySaver()

        # 创建主图管理器
        manager = MainGraphManager(llm=llm, checkpointer=checkpointer)
        logger.info("主图管理器创建成功")
        return manager
    except Exception as e:
        logger.error(f"创建主图管理器失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Graph 初始化失败: {str(e)}"
        )


# ============================================================================
# 任务管理依赖
# ============================================================================

def get_task_config(task_id: str) -> dict:
    """
    获取任务配置

    Args:
        task_id: 任务ID

    Returns:
        dict: 任务配置（包含 thread_id）
    """
    return {
        "configurable": {
            "thread_id": task_id
        }
    }


# ============================================================================
# 验证依赖
# ============================================================================

async def validate_task_request(
    code: str,
    settings: Settings = Depends(get_config)
) -> None:
    """
    验证任务请求

    Args:
        code: 代码内容
        settings: 应用配置

    Raises:
        HTTPException: 验证失败时抛出
    """
    # 检查代码长度
    if len(code) > 50000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="代码长度超过限制（最大 50000 字符）"
        )

    # 检查代码是否为空
    if not code.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="代码内容不能为空"
        )


# ============================================================================
# 清理函数
# ============================================================================

def clear_dependency_cache():
    """
    清除依赖缓存

    用于测试或配置更新后重新初始化依赖。
    """
    get_llm.cache_clear()
    get_graph_manager.cache_clear()
    logger.info("依赖缓存已清除")
