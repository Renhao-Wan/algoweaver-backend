"""
API 请求模型定义

定义所有 API 请求的入参校验模型，确保数据完整性和类型安全。
"""

from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class OptimizationLevel(str, Enum):
    """优化级别枚举"""
    BASIC = "basic"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"
    PRODUCTION = "production"


class ProgrammingLanguage(str, Enum):
    """支持的编程语言枚举"""
    PYTHON = "python"
    JAVA = "java"
    JAVASCRIPT = "javascript"
    CPP = "cpp"


class TaskRequest(BaseModel):
    """代码分析任务请求模型"""
    
    code: str = Field(
        ...,
        description="待分析的代码内容",
        min_length=1,
        max_length=50000,
        example="def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)"
    )
    
    language: ProgrammingLanguage = Field(
        ...,
        description="编程语言类型"
    )
    
    optimization_level: OptimizationLevel = Field(
        default=OptimizationLevel.BALANCED,
        description="优化级别"
    )
    
    include_explanation: bool = Field(
        default=True,
        description="是否包含算法讲解"
    )
    
    include_performance_test: bool = Field(
        default=False,
        description="是否包含性能测试"
    )
    
    custom_requirements: Optional[str] = Field(
        default=None,
        description="自定义需求说明",
        max_length=1000
    )

    @field_validator("code")
    @classmethod
    def validate_code_content(cls, v):
        """验证代码内容"""
        if not v.strip():
            raise ValueError('代码内容不能为空')
        
        # 检查是否包含危险操作
        dangerous_patterns = [
            'import os', 'import sys', 'import subprocess',
            'import socket', 'import urllib', 'import requests',
            '__import__', 'eval(', 'exec(', 'compile('
        ]
        
        code_lower = v.lower()
        for pattern in dangerous_patterns:
            if pattern in code_lower:
                raise ValueError(f'代码包含潜在危险操作: {pattern}')
        
        return v


class HumanInterventionRequest(BaseModel):
    """人工干预请求模型"""
    
    intervention_id: str = Field(
        ...,
        description="干预请求唯一标识"
    )
    
    decision_type: str = Field(
        ...,
        description="决策类型",
        example="optimization_suggestions"
    )
    
    accepted_suggestions: List[str] = Field(
        default_factory=list,
        description="接受的建议ID列表"
    )
    
    rejected_suggestions: List[str] = Field(
        default_factory=list,
        description="拒绝的建议ID列表"
    )
    
    custom_input: Optional[str] = Field(
        default=None,
        description="用户自定义输入",
        max_length=2000
    )
    
    timeout_seconds: Optional[int] = Field(
        default=300,
        description="超时时间（秒）",
        ge=30,
        le=1800
    )


class ReportGenerationRequest(BaseModel):
    """报告生成请求模型"""
    
    task_id: str = Field(
        ...,
        description="任务ID"
    )
    
    format: str = Field(
        default="markdown",
        description="报告格式",
        pattern="^(markdown|pdf|html)$"
    )
    
    include_history: bool = Field(
        default=True,
        description="是否包含优化历史"
    )
    
    template: str = Field(
        default="default",
        description="报告模板",
        pattern="^(default|detailed|summary)$"
    )
    
    custom_sections: Optional[List[str]] = Field(
        default=None,
        description="自定义章节列表"
    )


class PerformanceTestRequest(BaseModel):
    """性能测试请求模型"""
    
    code: str = Field(
        ...,
        description="待测试的代码"
    )
    
    test_cases: List[Dict[str, Any]] = Field(
        ...,
        description="测试用例列表",
        min_items=1,
        max_items=100
    )
    
    iterations: int = Field(
        default=10,
        description="测试迭代次数",
        ge=1,
        le=1000
    )
    
    timeout_per_test: int = Field(
        default=30,
        description="单个测试超时时间（秒）",
        ge=1,
        le=300
    )


class WebSocketMessage(BaseModel):
    """WebSocket 消息模型"""
    
    type: str = Field(
        ...,
        description="消息类型",
        example="status_update"
    )
    
    data: Dict[str, Any] = Field(
        ...,
        description="消息数据"
    )
    
    timestamp: Optional[str] = Field(
        default=None,
        description="时间戳"
    )
    
    message_id: Optional[str] = Field(
        default=None,
        description="消息ID"
    )


class TaskStatusQuery(BaseModel):
    """任务状态查询模型"""
    
    task_id: str = Field(
        ...,
        description="任务ID"
    )
    
    include_details: bool = Field(
        default=True,
        description="是否包含详细信息"
    )
    
    include_logs: bool = Field(
        default=False,
        description="是否包含执行日志"
    )