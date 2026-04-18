"""
LangGraph 状态定义模块

定义了多智能体系统中的状态类型，包括主图状态和子图局部状态。
使用 TypedDict 和 Pydantic 进行状态类型约束，确保状态传递的类型安全。

"""

from typing import Dict, List, Optional, Any, Union
from typing_extensions import TypedDict, NotRequired
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    """任务执行状态枚举"""
    PENDING = "pending"
    ANALYZING = "analyzing"
    WAITING_HUMAN = "waiting_human"
    OPTIMIZING = "optimizing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class Phase(str, Enum):
    """执行阶段枚举"""
    ANALYSIS = "analysis"
    DISSECTION = "dissection"
    REVIEW = "review"
    OPTIMIZATION = "optimization"
    VALIDATION = "validation"
    REPORT_GENERATION = "report_generation"


class CollaborationMode(str, Enum):
    """智能体协作模式枚举"""
    MASTER_EXPERT = "master_expert"
    NEGOTIATION = "negotiation"
    ADVERSARIAL = "adversarial"


class IssueType(str, Enum):
    """代码问题类型枚举"""
    LOGIC_ERROR = "logic_error"
    BOUNDARY_CONDITION = "boundary_condition"
    PERFORMANCE = "performance"
    SECURITY = "security"
    READABILITY = "readability"
    MAINTAINABILITY = "maintainability"


class Severity(str, Enum):
    """问题严重程度枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ============================================================================
# 基础数据模型
# ============================================================================

class ExecutionStep(BaseModel):
    """算法执行步骤模型"""
    step_number: int = Field(..., description="步骤编号")
    description: str = Field(..., description="步骤描述")
    code_snippet: Optional[str] = Field(None, description="相关代码片段")
    variables_state: Dict[str, Any] = Field(default_factory=dict, description="变量状态")
    time_complexity: Optional[str] = Field(None, description="时间复杂度")
    space_complexity: Optional[str] = Field(None, description="空间复杂度")


class CodeIssue(BaseModel):
    """代码问题模型"""
    issue_id: str = Field(..., description="问题唯一标识")
    type: IssueType = Field(..., description="问题类型")
    severity: Severity = Field(..., description="严重程度")
    line_number: int = Field(..., description="问题所在行号")
    description: str = Field(..., description="问题描述")
    suggestion: str = Field(..., description="修复建议")
    example_fix: Optional[str] = Field(None, description="修复示例代码")


class Suggestion(BaseModel):
    """优化建议模型"""
    suggestion_id: str = Field(..., description="建议唯一标识")
    issue_id: str = Field(..., description="关联的问题ID")
    improvement_type: str = Field(..., description="改进类型")
    original_code: str = Field(..., description="原始代码")
    improved_code: str = Field(..., description="改进后代码")
    explanation: str = Field(..., description="改进说明")
    impact_score: float = Field(..., ge=0, le=10, description="影响评分(0-10)")


class HumanDecision(BaseModel):
    """人工决策模型"""
    decision_id: str = Field(..., description="决策唯一标识")
    decision_type: str = Field(..., description="决策类型")
    accepted_suggestions: List[str] = Field(default_factory=list, description="接受的建议ID列表")
    rejected_suggestions: List[str] = Field(default_factory=list, description="拒绝的建议ID列表")
    custom_input: Optional[str] = Field(None, description="用户自定义输入")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="决策时间")


class AlgorithmExplanation(BaseModel):
    """算法讲解模型"""
    steps: List[ExecutionStep] = Field(default_factory=list, description="执行步骤列表")
    pseudocode: str = Field(..., description="伪代码")
    time_complexity: str = Field(..., description="时间复杂度")
    space_complexity: str = Field(..., description="空间复杂度")
    visualization: Optional[str] = Field(None, description="可视化描述")
    key_insights: List[str] = Field(default_factory=list, description="关键洞察")


# ============================================================================
# LangGraph 状态定义 (TypedDict)
# ============================================================================

class GlobalState(TypedDict):
    """
    主图全局状态
    
    管理整个多智能体系统的全局状态，包括任务信息、执行进度、
    智能体协作状态和用户交互历史。
    """
    # 任务基本信息
    task_id: str
    user_id: str
    original_code: str
    language: str
    optimization_level: str
    
    # 执行状态
    status: TaskStatus
    current_phase: Phase
    progress: float  # 0.0 - 1.0
    
    # 智能体协作状态
    collaboration_mode: CollaborationMode
    active_agents: List[str]
    
    # 分析结果
    algorithm_explanation: NotRequired[AlgorithmExplanation]
    detected_issues: NotRequired[List[CodeIssue]]
    optimization_suggestions: NotRequired[List[Suggestion]]
    
    # 迭代历史
    code_versions: List[str]  # 代码版本历史
    decision_history: List[HumanDecision]  # 人工决策历史
    
    # 人机交互
    pending_human_decision: NotRequired[Dict[str, Any]]
    human_intervention_required: bool
    
    # 执行上下文
    shared_context: Dict[str, Any]  # 智能体间共享的上下文信息
    execution_metadata: Dict[str, Any]  # 执行元数据
    
    # 时间戳
    created_at: datetime
    updated_at: datetime
    
    # 错误处理
    last_error: NotRequired[str]
    retry_count: int


class DissectionState(TypedDict):
    """
    算法拆解子图局部状态
    
    专门用于算法分析和拆解过程的局部状态管理，
    包含算法执行步骤、复杂度分析和可视化信息。
    """
    # 继承自全局状态的关键信息
    task_id: str
    code: str
    language: str
    
    # 算法分析状态
    analysis_phase: str  # "parsing", "simulation", "explanation", "visualization"
    
    # 执行步骤模拟
    execution_steps: List[ExecutionStep]
    current_step: int
    
    # 算法特征分析
    algorithm_type: NotRequired[str]  # "sorting", "searching", "graph", "dynamic_programming", etc.
    data_structures_used: List[str]
    
    # 复杂度分析
    time_complexity_analysis: NotRequired[Dict[str, str]]  # {"best": "O(n)", "average": "O(n log n)", "worst": "O(n²)"}
    space_complexity_analysis: NotRequired[str]
    
    # 可视化信息
    visualization_data: NotRequired[Dict[str, Any]]
    pseudocode_generated: NotRequired[str]
    
    # 子图执行状态
    step_simulator_result: NotRequired[Dict[str, Any]]
    visual_generator_result: NotRequired[Dict[str, Any]]
    
    # 错误处理
    parsing_errors: List[str]
    simulation_errors: List[str]


class ReviewState(TypedDict):
    """
    代码评审子图局部状态
    
    专门用于代码质量检测和优化建议生成的局部状态管理，
    支持协商/对抗模式的多轮评审和验证。
    """
    # 继承自全局状态的关键信息
    task_id: str
    code: str
    language: str
    optimization_level: str
    
    # 评审阶段状态
    review_phase: str  # "detection", "suggestion", "validation", "negotiation"
    review_round: int  # 当前评审轮次
    
    # 问题检测结果
    detected_issues: List[CodeIssue]
    issue_categories: Dict[str, int]  # 按类型统计问题数量
    
    # 优化建议
    generated_suggestions: List[Suggestion]
    validated_suggestions: List[str]  # 已验证通过的建议ID
    rejected_suggestions: List[str]  # 已拒绝的建议ID
    
    # 协商/对抗模式状态
    negotiation_rounds: int
    consensus_reached: bool
    conflicting_suggestions: List[Dict[str, Any]]  # 冲突的建议
    
    # 智能体协作状态
    mistake_detector_result: NotRequired[Dict[str, Any]]
    suggestion_generator_result: NotRequired[Dict[str, Any]]
    validation_tester_result: NotRequired[Dict[str, Any]]
    
    # 代码改进
    improved_code_versions: List[str]
    current_code_version: int
    
    # 质量评估
    quality_metrics: NotRequired[Dict[str, float]]  # {"readability": 8.5, "maintainability": 7.2, "performance": 9.1}
    quality_threshold: float  # 质量阈值
    quality_improvement: NotRequired[float]  # 质量提升幅度
    
    # 验证结果
    validation_results: List[Dict[str, Any]]
    test_cases_passed: int
    test_cases_failed: int
    
    # 错误处理
    detection_errors: List[str]
    suggestion_errors: List[str]
    validation_errors: List[str]


# ============================================================================
# 状态工厂和工具函数
# ============================================================================

class StateFactory:
    """状态工厂类，用于创建和初始化各种状态对象"""
    
    @staticmethod
    def create_global_state(
        task_id: str,
        user_id: str,
        code: str,
        language: str,
        optimization_level: str = "balanced"
    ) -> GlobalState:
        """创建初始的全局状态"""
        now = datetime.utcnow()
        return GlobalState(
            task_id=task_id,
            user_id=user_id,
            original_code=code,
            language=language,
            optimization_level=optimization_level,
            status=TaskStatus.PENDING,
            current_phase=Phase.ANALYSIS,
            progress=0.0,
            collaboration_mode=CollaborationMode.MASTER_EXPERT,
            active_agents=[],
            code_versions=[code],
            decision_history=[],
            human_intervention_required=False,
            shared_context={},
            execution_metadata={},
            created_at=now,
            updated_at=now,
            retry_count=0
        )
    
    @staticmethod
    def create_dissection_state(global_state: GlobalState) -> DissectionState:
        """从全局状态创建算法拆解子图状态"""
        return DissectionState(
            task_id=global_state["task_id"],
            code=global_state["original_code"],
            language=global_state["language"],
            analysis_phase="parsing",
            execution_steps=[],
            current_step=0,
            data_structures_used=[],
            parsing_errors=[],
            simulation_errors=[]
        )
    
    @staticmethod
    def create_review_state(global_state: GlobalState) -> ReviewState:
        """从全局状态创建代码评审子图状态"""
        return ReviewState(
            task_id=global_state["task_id"],
            code=global_state["code_versions"][-1],  # 使用最新版本的代码
            language=global_state["language"],
            optimization_level=global_state["optimization_level"],
            review_phase="detection",
            review_round=1,
            detected_issues=[],
            issue_categories={},
            generated_suggestions=[],
            validated_suggestions=[],
            rejected_suggestions=[],
            negotiation_rounds=0,
            consensus_reached=False,
            conflicting_suggestions=[],
            improved_code_versions=[],
            current_code_version=0,
            quality_threshold=7.0,  # 默认质量阈值
            validation_results=[],
            test_cases_passed=0,
            test_cases_failed=0,
            detection_errors=[],
            suggestion_errors=[],
            validation_errors=[]
        )


class StateUtils:
    """状态工具类，提供状态操作的辅助方法"""
    
    @staticmethod
    def update_progress(state: GlobalState, progress: float) -> None:
        """更新全局状态的进度"""
        state["progress"] = max(0.0, min(1.0, progress))
        state["updated_at"] = datetime.utcnow()
    
    @staticmethod
    def add_code_version(state: GlobalState, new_code: str) -> None:
        """添加新的代码版本到历史记录"""
        state["code_versions"].append(new_code)
        state["updated_at"] = datetime.utcnow()
    
    @staticmethod
    def add_human_decision(state: GlobalState, decision: HumanDecision) -> None:
        """添加人工决策到历史记录"""
        state["decision_history"].append(decision)
        state["updated_at"] = datetime.utcnow()
    
    @staticmethod
    def set_human_intervention_required(
        state: GlobalState, 
        required: bool, 
        decision_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """设置是否需要人工干预"""
        state["human_intervention_required"] = required
        if required and decision_data:
            state["pending_human_decision"] = decision_data
        elif not required and "pending_human_decision" in state:
            del state["pending_human_decision"]
        state["updated_at"] = datetime.utcnow()
    
    @staticmethod
    def increment_retry_count(state: GlobalState) -> None:
        """增加重试计数"""
        state["retry_count"] += 1
        state["updated_at"] = datetime.utcnow()
    
    @staticmethod
    def set_error(state: GlobalState, error_message: str) -> None:
        """设置错误信息"""
        state["last_error"] = error_message
        state["status"] = TaskStatus.FAILED
        state["updated_at"] = datetime.utcnow()
    
    @staticmethod
    def clear_error(state: GlobalState) -> None:
        """清除错误信息"""
        if "last_error" in state:
            del state["last_error"]
        state["updated_at"] = datetime.utcnow()


# ============================================================================
# 状态验证器
# ============================================================================

class StateValidator:
    """状态验证器，确保状态数据的完整性和一致性"""
    
    @staticmethod
    def validate_global_state(state: GlobalState) -> List[str]:
        """验证全局状态的有效性"""
        errors = []
        
        # 必填字段检查
        required_fields = ["task_id", "user_id", "original_code", "language"]
        for field in required_fields:
            if not state.get(field):
                errors.append(f"缺少必填字段: {field}")
        
        # 进度值检查
        if not (0.0 <= state.get("progress", 0) <= 1.0):
            errors.append("进度值必须在 0.0 到 1.0 之间")
        
        # 代码版本历史检查
        if not state.get("code_versions"):
            errors.append("代码版本历史不能为空")
        
        return errors
    
    @staticmethod
    def validate_dissection_state(state: DissectionState) -> List[str]:
        """验证算法拆解状态的有效性"""
        errors = []
        
        # 必填字段检查
        required_fields = ["task_id", "code", "language", "analysis_phase"]
        for field in required_fields:
            if not state.get(field):
                errors.append(f"缺少必填字段: {field}")
        
        # 当前步骤检查
        current_step = state.get("current_step", 0)
        execution_steps = state.get("execution_steps", [])
        if current_step < 0 or current_step > len(execution_steps):
            errors.append("当前步骤索引超出范围")
        
        return errors
    
    @staticmethod
    def validate_review_state(state: ReviewState) -> List[str]:
        """验证代码评审状态的有效性"""
        errors = []
        
        # 必填字段检查
        required_fields = ["task_id", "code", "language", "review_phase"]
        for field in required_fields:
            if not state.get(field):
                errors.append(f"缺少必填字段: {field}")
        
        # 评审轮次检查
        if state.get("review_round", 0) < 1:
            errors.append("评审轮次必须大于等于1")
        
        # 质量阈值检查
        quality_threshold = state.get("quality_threshold", 0)
        if not (0.0 <= quality_threshold <= 10.0):
            errors.append("质量阈值必须在 0.0 到 10.0 之间")
        
        return errors