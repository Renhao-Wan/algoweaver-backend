"""
数据模型包

包含所有 API 请求和响应的 Pydantic 模型定义。
"""

# 请求模型
from .requests import (
    OptimizationLevel,
    ProgrammingLanguage,
    TaskRequest,
    HumanInterventionRequest,
    ReportGenerationRequest,
    PerformanceTestRequest,
    WebSocketMessage,
    TaskStatusQuery,
)

# 响应模型
from .responses import (
    TaskStatus,
    IssueType,
    Severity,
    ImprovementType,
    BaseResponse,
    ErrorResponse,
    ExecutionStep,
    AlgorithmExplanation,
    CodeIssue,
    ImpactAssessment,
    Suggestion,
    PerformanceMetrics,
    ValidationResult,
    TaskCreationResponse,
    TaskStatusResponse,
    AnalysisResultResponse,
    ReportResponse,
    HumanInterventionResponse,
    WebSocketStatusMessage,
    WebSocketInterventionMessage,
    WebSocketResultMessage,
)

__all__ = [
    # 枚举类型
    "OptimizationLevel",
    "ProgrammingLanguage", 
    "TaskStatus",
    "IssueType",
    "Severity",
    "ImprovementType",
    
    # 请求模型
    "TaskRequest",
    "HumanInterventionRequest",
    "ReportGenerationRequest",
    "PerformanceTestRequest",
    "WebSocketMessage",
    "TaskStatusQuery",
    
    # 响应模型
    "BaseResponse",
    "ErrorResponse",
    "ExecutionStep",
    "AlgorithmExplanation",
    "CodeIssue",
    "ImpactAssessment",
    "Suggestion",
    "PerformanceMetrics",
    "ValidationResult",
    "TaskCreationResponse",
    "TaskStatusResponse",
    "AnalysisResultResponse",
    "ReportResponse",
    "HumanInterventionResponse",
    "WebSocketStatusMessage",
    "WebSocketInterventionMessage",
    "WebSocketResultMessage",
]