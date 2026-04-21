"""
LLM 实例管理模块

提供 LLM 实例的创建和缓存，避免循环依赖。

┌─────────────────────────────────────┐
│     app.core.llm.get_llm_instance() │  ← 全局单例 LLM 管理
│     (_llm_instance 全局变量)        │
└──────────────┬──────────────────────┘
               │
               ├─→ supervisor/agent.py 节点函数
               ├─→ dissection/nodes.py 节点函数
               ├─→ review/nodes.py 节点函数
               └─→ 所有 Agent 类
"""

from typing import Optional

from fastapi import HTTPException, status
from langchain_openai import ChatOpenAI

from app.core.config import Settings, get_settings
from app.core.logger import get_logger

logger = get_logger(__name__)

# 全局 LLM 实例缓存
_llm_instance: Optional[ChatOpenAI] = None


def get_llm_instance(settings: Optional[Settings] = None) -> ChatOpenAI:
    """
    获取 LLM 实例

    使用全局变量缓存确保单例，避免重复创建 LLM 实例。

    Args:
        settings: 应用配置（可选，未提供时使用 get_settings()）

    Returns:
        ChatOpenAI: LLM 实例
    """
    global _llm_instance

    if _llm_instance is None:
        if settings is None:
            settings = get_settings()
            # 类型断言确保 settings 不为 None
            assert settings is not None

        try:
            _llm_instance = ChatOpenAI(
                api_key=lambda : settings.llm_api_key,
                base_url=settings.llm_api_base,
                model=settings.llm_model,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
            )
            logger.debug(f"创建 LLM 实例: {settings.llm_model}")
        except Exception as e:
            logger.error(f"创建 LLM 实例失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"LLM 初始化失败: {str(e)}"
            )

    return _llm_instance


def clear_llm_cache():
    """
    清除 LLM 缓存

    用于测试或配置更新后重新初始化 LLM。
    """
    global _llm_instance
    _llm_instance = None
    logger.info("LLM 缓存已清除")
