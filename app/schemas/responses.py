"""
API 响应模型定义

定义所有 API 响应的统一格式，确保前端能够正确解析和处理响应数据。

架构原则：
- 从 app.graph.state 导入核心业务模型（Single Source of Truth）
- API 响应模型通过继承扩展核心模型，添加 API 特定字段
- 保持依赖方向：API 层 → 业务层
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field

# 从 state.py 导入核心业务模型（Single Source of Truth）
from app.graph.state import (
    Severity,
    ExecutionStep as CoreExecutionStep,
    CodeIssue as CoreCodeIssue,
    AlgorithmExplanation as CoreAlgorithmExplanation,
    Suggestion as CoreSuggestion,
)


class ResponseTaskStatus(str, Enum):
    """任务状态枚举"""
    CREATED = "created"
    PENDING = "pending"
    ANALYZING = "analyzing"
    WAITING_HUMAN = "waiting_human"
    OPTIMIZING = "optimizing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class ImprovementType(str, Enum):
    """改进类型枚举（API 特定）"""
    ALGORITHM_OPTIMIZATION = "algorithm_optimization"
    CODE_REFACTORING = "code_refactoring"
    PERFORMANCE_TUNING = "performance_tuning"
    SECURITY_ENHANCEMENT = "security_enhancement"
    READABILITY_IMPROVEMENT = "readability_improvement"


# ============================================================================
# 基础响应模型
# ============================================================================
class BaseResponse(BaseModel):
    """基础响应模型"""
    
    success: bool = Field(
        ...,
        description="请求是否成功"
    )
    
    message: str = Field(
        default="",
        description="响应消息"
    )
    
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="响应时间戳"
    )
    
    request_id: Optional[str] = Field(
        default=None,
        description="请求追踪ID"
    )


class ErrorResponse(BaseResponse):
    """错误响应模型"""
    
    success: bool = Field(default=False)
    
    error_code: str = Field(
        ...,
        description="错误代码"
    )
    
    error_details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="错误详细信息"
    )


# ============================================================================
# API 特定模型（不在 state.py 中）
# ============================================================================

class ImpactAssessment(BaseModel):
    """影响评估模型（API 特定）"""

    performance_impact: str = Field(
        ...,
        description="性能影响评估"
    )

    readability_impact: str = Field(
        ...,
        description="可读性影响评估"
    )

    maintainability_impact: str = Field(
        ...,
        description="可维护性影响评估"
    )

    risk_level: Severity = Field(
        ...,
        description="风险等级"
    )


# ============================================================================
# 核心业务模型的 API 扩展（继承自 state.py）
# ============================================================================

class ExecutionStep(CoreExecutionStep):
    """
    算法执行步骤模型（API 响应版本）

    继承自 state.py 的 CoreExecutionStep，保持字段一致。
    如需添加 API 特定字段，在此扩展。
    """
    pass


class CodeIssue(CoreCodeIssue):
    """
    代码问题模型（API 响应版本）

    继承自 state.py 的 CoreCodeIssue，添加 API 特定字段。
    """
    column_number: Optional[int] = Field(
        default=None,
        description="问题所在列号（API 额外字段）"
    )

    impact_assessment: Optional[str] = Field(
        default=None,
        description="影响评估（API 额外字段）"
    )


class AlgorithmExplanation(CoreAlgorithmExplanation):
    """
    算法讲解模型（API 响应版本）

    继承自 state.py 的 CoreAlgorithmExplanation，添加 API 特定字段。
    """
    algorithm_name: str = Field(
        default="",
        description="算法名称（API 额外字段）"
    )


class Suggestion(CoreSuggestion):
    """
    优化建议模型（API 响应版本）

    继承自 state.py 的 CoreSuggestion，添加 API 特定字段。
    注意：improvement_type 在核心模型中是 str，这里扩展为 ImprovementType 枚举
    """
    # 重写 improvement_type 为更具体的枚举类型
    improvement_type: ImprovementType = Field(
        ...,
        description="改进类型（API 使用枚举）"
    )

    title: str = Field(
        default="",
        description="建议标题（API 额外字段）"
    )

    description: str = Field(
        default="",
        description="建议描述（API 额外字段）"
    )

    impact_assessment: ImpactAssessment = Field(
        ...,
        description="影响评估（API 额外字段）"
    )

    confidence_score: float = Field(
        default=0.0,
        description="置信度分数（API 额外字段）",
        ge=0.0,
        le=1.0
    )


# ============================================================================
# 其他 API 特定模型
# ============================================================================


class PerformanceMetrics(BaseModel):
    """性能指标模型"""
    
    execution_time_ms: float = Field(
        ...,
        description="执行时间（毫秒）"
    )
    
    memory_usage_mb: float = Field(
        ...,
        description="内存使用量（MB）"
    )
    
    cpu_usage_percent: Optional[float] = Field(
        default=None,
        description="CPU使用率（百分比）"
    )
    
    iterations_count: int = Field(
        ...,
        description="测试迭代次数"
    )
    
    average_time_ms: float = Field(
        ...,
        description="平均执行时间（毫秒）"
    )
    
    min_time_ms: float = Field(
        ...,
        description="最小执行时间（毫秒）"
    )
    
    max_time_ms: float = Field(
        ...,
        description="最大执行时间（毫秒）"
    )
    
    std_deviation_ms: float = Field(
        ...,
        description="标准差（毫秒）"
    )


class ValidationResult(BaseModel):
    """验证结果模型"""
    
    is_valid: bool = Field(
        ...,
        description="验证是否通过"
    )
    
    test_results: List[Dict[str, Any]] = Field(
        ...,
        description="测试结果列表"
    )
    
    performance_comparison: Optional[Dict[str, PerformanceMetrics]] = Field(
        default=None,
        description="性能对比结果"
    )
    
    error_messages: List[str] = Field(
        default_factory=list,
        description="错误消息列表"
    )
    
    warnings: List[str] = Field(
        default_factory=list,
        description="警告消息列表"
    )


# API 响应模型
class TaskCreationResponse(BaseResponse):
    """任务创建响应模型"""
    
    task_id: str = Field(
        ...,
        description="任务唯一标识"
    )
    
    status: ResponseTaskStatus = Field(
        default=ResponseTaskStatus.CREATED,
        description="任务状态"
    )
    
    estimated_duration_seconds: int = Field(
        ...,
        description="预估执行时间（秒）"
    )
    
    websocket_url: str = Field(
        ...,
        description="WebSocket连接URL"
    )


class TaskStatusResponse(BaseResponse):
    """任务状态响应模型"""
    
    task_id: str = Field(
        ...,
        description="任务ID"
    )
    
    status: ResponseTaskStatus = Field(
        ...,
        description="任务状态"
    )
    
    progress_percent: int = Field(
        ...,
        description="进度百分比",
        ge=0,
        le=100
    )
    
    current_phase: str = Field(
        ...,
        description="当前阶段"
    )
    
    created_at: datetime = Field(
        ...,
        description="创建时间"
    )
    
    updated_at: datetime = Field(
        ...,
        description="更新时间"
    )
    
    result: Optional[Dict[str, Any]] = Field(
        default=None,
        description="执行结果"
    )
    
    logs: Optional[List[str]] = Field(
        default=None,
        description="执行日志"
    )


class AnalysisResultResponse(BaseResponse):
    """分析结果响应模型"""
    
    task_id: str = Field(
        ...,
        description="任务ID"
    )
    
    original_code: str = Field(
        ...,
        description="原始代码"
    )
    
    optimized_code: Optional[str] = Field(
        default=None,
        description="优化后代码"
    )
    
    explanation: AlgorithmExplanation = Field(
        ...,
        description="算法讲解"
    )
    
    issues: List[CodeIssue] = Field(
        ...,
        description="发现的问题列表"
    )
    
    suggestions: List[Suggestion] = Field(
        ...,
        description="优化建议列表"
    )
    
    validation_result: Optional[ValidationResult] = Field(
        default=None,
        description="验证结果"
    )
    
    performance_metrics: Optional[PerformanceMetrics] = Field(
        default=None,
        description="性能指标"
    )
    
    optimization_history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="优化历史记录"
    )


class ReportResponse(BaseResponse):
    """报告响应模型"""
    
    report_id: str = Field(
        ...,
        description="报告ID"
    )
    
    report_url: str = Field(
        ...,
        description="报告下载URL"
    )
    
    format: str = Field(
        ...,
        description="报告格式"
    )
    
    size_bytes: int = Field(
        ...,
        description="文件大小（字节）"
    )
    
    expires_at: datetime = Field(
        ...,
        description="过期时间"
    )


class HumanInterventionResponse(BaseResponse):
    """人工干预响应模型"""
    
    intervention_id: str = Field(
        ...,
        description="干预ID"
    )
    
    prompt: str = Field(
        ...,
        description="干预提示信息"
    )
    
    options: List[Dict[str, Any]] = Field(
        ...,
        description="可选项列表"
    )
    
    timeout_seconds: int = Field(
        ...,
        description="超时时间（秒）"
    )
    
    default_action: Optional[str] = Field(
        default=None,
        description="默认操作"
    )


class WebSocketStatusMessage(BaseModel):
    """WebSocket 状态消息模型"""
    
    type: str = Field(
        default="status_update",
        description="消息类型"
    )
    
    data: Dict[str, Any] = Field(
        ...,
        description="状态数据"
    )


class WebSocketInterventionMessage(BaseModel):
    """WebSocket 干预消息模型"""
    
    type: str = Field(
        default="human_intervention_required",
        description="消息类型"
    )
    
    data: HumanInterventionResponse = Field(
        ...,
        description="干预数据"
    )


class WebSocketResultMessage(BaseModel):
    """WebSocket 结果消息模型"""
    
    type: str = Field(
        default="analysis_complete",
        description="消息类型"
    )
    
    data: AnalysisResultResponse = Field(
        ...,
        description="分析结果数据"
    )