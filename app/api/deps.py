"""
API 依赖注入模块

提供 FastAPI 路由所需的依赖项，包括配置、Graph 实例等。
┌─────────────────────────────────────────────┐
│         app/api/deps.py                     │
│         (依赖注入中心)                       │
│                                             │
│  - get_config() → 全局配置                  │
│  - get_graph_manager() → 主图管理器         │
└──────────────┬──────────────────────────────┘
               │ 被所有层使用
               ↓
┌──────────────────────────────────────────────┐
│  使用者：                                     │
│  ✓ API 路由 (app/api/routes/)                │
│                                              │
│  Note: LLM 实例由 app.core.llm 统一管理     │
│  各节点直接调用 get_llm_instance() 获取      │
└──────────────────────────────────────────────┘

"""

from typing import Optional

from fastapi import Depends, HTTPException, status

from app.core.config import Settings, get_settings
from app.core.logger import get_logger
from app.core.checkpointer import get_checkpointer
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
# Graph 依赖
# ============================================================================

# 全局 Graph Manager 实例缓存
_graph_manager_instance: Optional[MainGraphManager] = None


def get_graph_manager() -> MainGraphManager:
    """
    获取主图管理器实例

    使用全局变量缓存确保单例，避免重复构建图。

    Returns:
        MainGraphManager: 主图管理器实例

    Note:
        - LLM 实例由各个节点通过 get_llm_instance() 获取
        - Checkpointer 通过 get_checkpointer() 获取（单例）
    """
    global _graph_manager_instance

    if _graph_manager_instance is None:
        try:
            # 获取全局 checkpointer 实例
            checkpointer = get_checkpointer()

            # 创建主图管理器
            _graph_manager_instance = MainGraphManager(checkpointer=checkpointer)
            logger.info("主图管理器创建成功")

            if _graph_manager_instance is None :
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Graph 初始化失败"
                )
        except Exception as e:
            logger.error(f"创建主图管理器失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Graph 初始化失败: {str(e)}"
            )

    return _graph_manager_instance


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
    from app.core.llm import clear_llm_cache
    from app.core.checkpointer import clear_checkpointer_cache

    # 清除 LLM 缓存
    clear_llm_cache()

    # 清除 Checkpointer 缓存
    clear_checkpointer_cache()

    # 清除 Graph Manager 缓存
    global _graph_manager_instance
    _graph_manager_instance = None

    logger.info("依赖缓存已清除")
