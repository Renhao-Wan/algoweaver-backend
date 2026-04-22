"""
日志系统配置模块

提供结构化日志配置和 LangSmith 追踪集成
支持多种日志输出格式和目标
"""

import logging
import logging.handlers
import sys
import json
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from contextvars import ContextVar

from .config import settings


class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器"""
    
    def format(self, record: logging.LogRecord) -> str:
        """
        格式化日志记录为结构化JSON格式
        
        Args:
            record: 日志记录对象
            
        Returns:
            str: 格式化后的JSON字符串
        """
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # 添加额外字段
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)
        
        # 添加追踪信息
        if hasattr(record, "trace_id"):
            log_data["trace_id"] = record.trace_id
        
        if hasattr(record, "span_id"):
            log_data["span_id"] = record.span_id
        
        return json.dumps(log_data, ensure_ascii=False)


class LangSmithHandler(logging.Handler):
    """LangSmith 追踪日志处理器"""

    def __init__(self):
        super().__init__()
        self.langsmith_client = None
        self._init_langsmith_client()

    def _init_langsmith_client(self):
        """初始化 LangSmith 客户端"""
        if not settings.langsmith_tracing or not settings.langsmith_api_key:
            return

        try:
            from langsmith import Client
            self.langsmith_client = Client(
                api_url=settings.langsmith_endpoint,
                api_key=settings.langsmith_api_key,
            )
        except ImportError:
            logging.getLogger(__name__).warning("LangSmith 客户端未安装，跳过追踪日志")
        except Exception as e:
            logging.getLogger(__name__).error(f"初始化 LangSmith 客户端失败: {e}")

    def emit(self, record: logging.LogRecord):
        """
        发送日志到 LangSmith

        Args:
            record: 日志记录对象
        """
        if not self.langsmith_client:
            return

        try:
            # 构建追踪数据
            trace_data = {
                "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                "level": record.levelname,
                "message": record.getMessage(),
                "logger": record.name,
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
            }

            # 添加请求上下文
            if hasattr(record, "request_id"):
                trace_data["request_id"] = record.request_id
            if hasattr(record, "user_id"):
                trace_data["user_id"] = record.user_id

            # 添加追踪上下文
            if hasattr(record, "trace_id"):
                trace_data["trace_id"] = record.trace_id
            if hasattr(record, "span_id"):
                trace_data["span_id"] = record.span_id
            if hasattr(record, "parent_span_id"):
                trace_data["parent_span_id"] = record.parent_span_id

            # 添加智能体执行上下文
            if hasattr(record, "agent_name"):
                trace_data["agent_name"] = record.agent_name
            if hasattr(record, "agent_type"):
                trace_data["agent_type"] = record.agent_type
            if hasattr(record, "task_id"):
                trace_data["task_id"] = record.task_id
            if hasattr(record, "phase"):
                trace_data["phase"] = record.phase

            # 添加异常信息
            if record.exc_info:
                trace_data["exception"] = self.format(record)

            # 发送到 LangSmith
            self.langsmith_client.create_run(
                name=f"log_{record.levelname.lower()}",
                run_type="tool",
                inputs={"log_data": trace_data},
                project_name=settings.langsmith_project,
            )
        except Exception as e:
            # 避免日志处理器本身的错误影响应用
            print(f"LangSmith 日志发送失败: {e}", file=sys.stderr)


request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)


class ContextFilter(logging.Filter):
    """上下文过滤器，添加请求上下文信息"""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        为日志记录添加上下文信息
        
        Args:
            record: 日志记录对象
            
        Returns:
            bool: 是否通过过滤器
        """
        # 添加应用信息
        record.app_name = settings.app_name
        record.app_version = settings.app_version
        record.environment = settings.environment
        
        # 尝试获取请求上下文（如果在 FastAPI 请求中）
        try:
            # 获取请求ID（如果存在）
            request_id = request_id_var.get()
            if request_id:
                record.request_id = request_id

            # 获取用户ID（如果存在）
            user_id = user_id_var.get()
            if user_id:
                record.user_id = user_id
                
        except Exception:
            # 如果获取上下文失败，继续处理
            pass
        
        return True


def setup_logging() -> None:
    """
    设置应用日志配置
    
    配置根日志器、处理器和格式化器
    """
    # 获取根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level))
    
    # 清除现有处理器
    root_logger.handlers.clear()
    
    # 创建上下文过滤器
    context_filter = ContextFilter()
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.log_level))
    
    if settings.is_development:
        # 开发环境使用简单格式
        console_formatter = logging.Formatter(
            fmt=settings.log_format,
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    else:
        # 生产环境使用结构化格式
        console_formatter = StructuredFormatter()
    
    console_handler.setFormatter(console_formatter)
    console_handler.addFilter(context_filter)
    root_logger.addHandler(console_handler)
    
    # 文件处理器（如果配置了日志文件）
    if settings.log_file:
        log_file_path = Path(settings.log_file)
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            filename=settings.log_file,
            maxBytes=settings.log_max_size,
            backupCount=settings.log_backup_count,
            encoding="utf-8"
        )
        file_handler.setLevel(getattr(logging, settings.log_level))
        
        # 文件日志始终使用结构化格式
        file_formatter = StructuredFormatter()
        file_handler.setFormatter(file_formatter)
        file_handler.addFilter(context_filter)
        root_logger.addHandler(file_handler)
    
    # LangSmith 处理器（如果启用追踪）
    if settings.langsmith_tracing and settings.langsmith_api_key:
        langsmith_handler = LangSmithHandler()
        langsmith_handler.setLevel(logging.INFO)  # 只追踪 INFO 及以上级别
        langsmith_handler.addFilter(context_filter)
        root_logger.addHandler(langsmith_handler)
    
    # 设置第三方库日志级别
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志器
    
    Args:
        name: 日志器名称，通常使用 __name__
        
    Returns:
        logging.Logger: 日志器实例
    """
    return logging.getLogger(name)


def log_with_context(logger: logging.Logger, level: int, message: str,
                    extra_fields: Optional[Dict[str, Any]] = None,
                    trace_id: Optional[str] = None,
                    span_id: Optional[str] = None,
                    parent_span_id: Optional[str] = None,
                    agent_name: Optional[str] = None,
                    agent_type: Optional[str] = None,
                    task_id: Optional[str] = None,
                    phase: Optional[str] = None) -> None:
    """
    带上下文信息的日志记录

    Args:
        logger: 日志器实例
        level: 日志级别
        message: 日志消息
        extra_fields: 额外字段
        trace_id: 追踪ID
        span_id: 跨度ID
        parent_span_id: 父跨度ID
        agent_name: 智能体名称
        agent_type: 智能体类型
        task_id: 任务ID
        phase: 执行阶段
    """
    extra = {}

    if extra_fields:
        extra["extra_fields"] = extra_fields

    if trace_id:
        extra["trace_id"] = trace_id

    if span_id:
        extra["span_id"] = span_id

    if parent_span_id:
        extra["parent_span_id"] = parent_span_id

    if agent_name:
        extra["agent_name"] = agent_name

    if agent_type:
        extra["agent_type"] = agent_type

    if task_id:
        extra["task_id"] = task_id

    if phase:
        extra["phase"] = phase

    logger.log(level, message, extra=extra)


class LoggerMixin:
    """日志器混入类，为其他类提供日志功能"""
    
    @property
    def logger(self) -> logging.Logger:
        """获取当前类的日志器"""
        return get_logger(self.__class__.__module__ + "." + self.__class__.__name__)
    
    def log_info(self, message: str, **kwargs):
        """记录信息日志"""
        log_with_context(self.logger, logging.INFO, message, kwargs)
    
    def log_warning(self, message: str, **kwargs):
        """记录警告日志"""
        log_with_context(self.logger, logging.WARNING, message, kwargs)
    
    def log_error(self, message: str, **kwargs):
        """记录错误日志"""
        log_with_context(self.logger, logging.ERROR, message, kwargs)
    
    def log_debug(self, message: str, **kwargs):
        """记录调试日志"""
        log_with_context(self.logger, logging.DEBUG, message, kwargs)


# 应用启动时的日志配置
def configure_logging():
    """
    配置应用日志系统
    
    在应用启动时调用此函数进行日志初始化
    """
    setup_logging()
    
    # 记录启动日志
    logger = get_logger(__name__)
    logger.info(
        "日志系统初始化完成",
        extra={
            "extra_fields": {
                "log_level": settings.log_level,
                "log_file": settings.log_file,
                "langsmith_tracing": settings.langsmith_tracing,
                "environment": settings.environment,
            }
        }
    )


# 导出常用的日志器
app_logger = get_logger("algoweaver.app")
api_logger = get_logger("algoweaver.api")
agent_logger = get_logger("algoweaver.agent")
sandbox_logger = get_logger("algoweaver.sandbox")


def log_agent_execution(
    agent_name: str,
    agent_type: str,
    phase: str,
    task_id: Optional[str] = None,
    inputs: Optional[Dict[str, Any]] = None,
    outputs: Optional[Dict[str, Any]] = None,
    duration_ms: Optional[float] = None,
    error: Optional[str] = None,
    trace_id: Optional[str] = None,
    span_id: Optional[str] = None,
    parent_span_id: Optional[str] = None
) -> None:
    """
    记录智能体执行日志

    专门用于追踪智能体的执行过程，包括输入、输出、耗时等信息。

    Args:
        agent_name: 智能体名称
        agent_type: 智能体类型 (supervisor/dissection/review)
        phase: 执行阶段
        task_id: 任务ID
        inputs: 输入数据
        outputs: 输出数据
        duration_ms: 执行耗时（毫秒）
        error: 错误信息
        trace_id: 追踪ID
        span_id: 跨度ID
        parent_span_id: 父跨度ID
    """
    message = f"智能体执行: {agent_name} ({agent_type}) - {phase}"

    extra_fields = {
        "agent_name": agent_name,
        "agent_type": agent_type,
        "phase": phase,
    }

    if task_id:
        extra_fields["task_id"] = task_id

    if inputs:
        extra_fields["inputs"] = inputs

    if outputs:
        extra_fields["outputs"] = outputs

    if duration_ms is not None:
        extra_fields["duration_ms"] = duration_ms

    if error:
        extra_fields["error"] = error
        level = logging.ERROR
    else:
        level = logging.INFO

    log_with_context(
        agent_logger,
        level,
        message,
        extra_fields=extra_fields,
        trace_id=trace_id,
        span_id=span_id,
        parent_span_id=parent_span_id,
        agent_name=agent_name,
        agent_type=agent_type,
        task_id=task_id,
        phase=phase
    )


def log_graph_execution(
    graph_name: str,
    node_name: str,
    task_id: Optional[str] = None,
    state_snapshot: Optional[Dict[str, Any]] = None,
    duration_ms: Optional[float] = None,
    error: Optional[str] = None,
    trace_id: Optional[str] = None,
    span_id: Optional[str] = None,
    parent_span_id: Optional[str] = None
) -> None:
    """
    记录图执行日志

    专门用于追踪 LangGraph 图的执行过程，包括节点执行、状态变化等信息。

    Args:
        graph_name: 图名称 (main_graph/dissection_subgraph/review_subgraph)
        node_name: 节点名称
        task_id: 任务ID
        state_snapshot: 状态快照
        duration_ms: 执行耗时（毫秒）
        error: 错误信息
        trace_id: 追踪ID
        span_id: 跨度ID
        parent_span_id: 父跨度ID
    """
    message = f"图节点执行: {graph_name}.{node_name}"

    extra_fields = {
        "graph_name": graph_name,
        "node_name": node_name,
    }

    if task_id:
        extra_fields["task_id"] = task_id

    if state_snapshot:
        extra_fields["state_snapshot"] = state_snapshot

    if duration_ms is not None:
        extra_fields["duration_ms"] = duration_ms

    if error:
        extra_fields["error"] = error
        level = logging.ERROR
    else:
        level = logging.INFO

    log_with_context(
        agent_logger,
        level,
        message,
        extra_fields=extra_fields,
        trace_id=trace_id,
        span_id=span_id,
        parent_span_id=parent_span_id,
        task_id=task_id
    )