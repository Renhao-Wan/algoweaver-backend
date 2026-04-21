"""
LangGraph 状态定义模块（重构版）

本模块定义了多智能体系统中的状态类型，遵循6大状态设计原则：
1. Single Source of Truth: 每个数据只有一个权威来源
2. Strong Typing: 使用强类型约束确保类型安全
3. Minimal but Sufficient: 状态字段最小化但足够完成任务
4. Clear Ownership: 明确每个字段的所有权和生命周期
5. Consistency & Validation: 状态一致性和验证机制
6. Evolvability: 易于扩展和演进

状态层次结构：
- GlobalState: 主图全局状态（任务级别）
- DissectionState: 算法拆解子图局部状态（算法分析级别）
- ReviewState: 代码评审子图局部状态（代码质量级别）
"""

from typing import Dict, List, Optional, Any, Union
from typing_extensions import TypedDict, NotRequired
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from enum import Enum


# ============================================================================
# 枚举类型定义
# ============================================================================

class StateTaskStatus(str, Enum):
    """任务执行状态"""
    PENDING = "pending"
    ANALYZING = "analyzing"
    WAITING_HUMAN = "waiting_human"
    OPTIMIZING = "optimizing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class Phase(str, Enum):
    """执行阶段"""
    ANALYSIS = "analysis"
    DISSECTION = "dissection"
    REVIEW = "review"
    REPORT_GENERATION = "report_generation"


class CollaborationMode(str, Enum):
    """智能体协作模式"""
    MASTER_EXPERT = "master_expert"
    NEGOTIATION = "negotiation"
    ADVERSARIAL = "adversarial"


class IssueType(str, Enum):
    """代码问题类型"""
    LOGIC_ERROR = "logic_error"
    BOUNDARY_CONDITION = "boundary_condition"
    PERFORMANCE = "performance"
    SECURITY = "security"
    READABILITY = "readability"
    MAINTAINABILITY = "maintainability"


class Severity(str, Enum):
    """问题严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ============================================================================
# 基础数据模型（Pydantic）
# ============================================================================

class ExecutionStep(BaseModel):
    """算法执行步骤"""
    step_number: int = Field(..., ge=1, description="步骤编号（从1开始）")
    description: str = Field(..., min_length=1, description="步骤描述")
    code_snippet: Optional[str] = Field(None, description="相关代码片段")
    variables_state: Dict[str, Any] = Field(default_factory=dict, description="变量状态快照")
    time_complexity: Optional[str] = Field(None, description="该步骤的时间复杂度")
    space_complexity: Optional[str] = Field(None, description="该步骤的空间复杂度")


class CodeIssue(BaseModel):
    """代码问题"""
    issue_id: str = Field(..., description="问题唯一标识")
    type: IssueType = Field(..., description="问题类型")
    severity: Severity = Field(..., description="严重程度")
    line_number: int = Field(..., ge=1, description="问题所在行号")
    description: str = Field(..., min_length=1, description="问题描述")
    suggestion: str = Field(..., min_length=1, description="修复建议")
    example_fix: Optional[str] = Field(None, description="修复示例代码")


class Suggestion(BaseModel):
    """优化建议"""
    suggestion_id: str = Field(..., description="建议唯一标识")
    issue_id: str = Field(..., description="关联的问题ID")
    improvement_type: str = Field(..., description="改进类型")
    original_code: str = Field(..., description="原始代码")
    improved_code: str = Field(..., description="改进后代码")
    explanation: str = Field(..., min_length=1, description="改进说明")
    impact_score: float = Field(..., ge=0, le=10, description="影响评分(0-10)")


class HumanDecision(BaseModel):
    """人工决策记录"""
    decision_id: str = Field(..., description="决策唯一标识")
    decision_type: str = Field(..., description="决策类型")
    accepted_suggestions: List[str] = Field(default_factory=list, description="接受的建议ID列表")
    rejected_suggestions: List[str] = Field(default_factory=list, description="拒绝的建议ID列表")
    custom_input: Optional[str] = Field(None, description="用户自定义输入")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="决策时间")


class AlgorithmExplanation(BaseModel):
    """算法讲解"""
    steps: List[ExecutionStep] = Field(default_factory=list, description="执行步骤列表")
    pseudocode: str = Field(..., min_length=1, description="伪代码")
    time_complexity: str = Field(..., description="时间复杂度")
    space_complexity: str = Field(..., description="空间复杂度")
    visualization: Optional[str] = Field(None, description="可视化描述（Mermaid/ASCII）")
    key_insights: List[str] = Field(default_factory=list, description="关键洞察")


# ============================================================================
# LangGraph 状态定义（TypedDict）
# ============================================================================

class GlobalState(TypedDict):
    """
    主图全局状态

    原则：
    - Single Source of Truth: 任务级别的唯一真实来源
    - Clear Ownership: 主图拥有任务生命周期和跨子图的共享数据
    - Minimal: 只包含任务级别必需的字段
    """
    # === 任务标识（必需） ===
    task_id: str
    user_id: str

    # === 输入数据（必需） ===
    original_code: str
    language: str
    optimization_level: str  # "fast", "balanced", "thorough"

    # === 执行状态（必需） ===
    status: StateTaskStatus
    current_phase: Phase
    progress: float  # 0.0 - 1.0

    # === 智能体协作（必需） ===
    collaboration_mode: CollaborationMode
    active_agents: List[str]

    # === 结果数据（可选，由子图填充） ===
    algorithm_explanation: NotRequired[AlgorithmExplanation]
    detected_issues: NotRequired[List[CodeIssue]]
    optimization_suggestions: NotRequired[List[Suggestion]]

    # === 代码版本历史（必需） ===
    code_versions: List[str]  # 代码演进历史

    # === Human-in-the-loop（必需） ===
    decision_history: List[HumanDecision]
    human_intervention_required: bool
    pending_human_decision: NotRequired[Dict[str, Any]]

    # === 共享上下文（必需） ===
    shared_context: Dict[str, Any]  # 智能体间共享的临时数据

    # === 时间戳（必需） ===
    created_at: datetime
    updated_at: datetime

    # === 错误处理（可选） ===
    last_error: NotRequired[str] | None
    retry_count: int


class DissectionState(TypedDict):
    """
    算法拆解子图局部状态

    原则：
    - Clear Ownership: 子图拥有算法分析过程的所有数据
    - Minimal: 只包含算法拆解必需的字段
    - State Isolation: 与全局状态隔离，通过转换函数交互
    """
    # === 任务标识（继承自全局） ===
    task_id: str

    # === 输入数据（继承自全局） ===
    code: str
    language: str

    # === 分析阶段（子图内部） ===
    analysis_phase: str  # "parsing", "simulation", "visualization", "completed"

    # === 执行步骤模拟（子图核心数据） ===
    execution_steps: List[ExecutionStep]
    current_step: int

    # === 算法特征（子图分析结果） ===
    algorithm_type: NotRequired[str]  # "sorting", "searching", "graph", etc.
    data_structures_used: List[str]

    # === 复杂度分析（子图分析结果） ===
    time_complexity_analysis: NotRequired[Dict[str, str]]  # {"best": "O(n)", "average": "O(n log n)", "worst": "O(n²)"}
    space_complexity_analysis: NotRequired[str]

    # === 可视化数据（子图生成） ===
    visualization_data: NotRequired[Dict[str, Any]]
    pseudocode_generated: NotRequired[str]

    # === 算法讲解结果（子图最终输出） ===
    algorithm_explanation: NotRequired[AlgorithmExplanation]

    # === 变量追踪（子图内部） ===
    variables_trace: NotRequired[Dict[str, List[Any]]]
    execution_flow: NotRequired[List[str]]

    # === 输入数据（可选） ===
    input_data: NotRequired[Dict[str, Any]]

    # === 错误处理（子图内部） ===
    error_info: NotRequired[str]
    needs_retry: NotRequired[bool]
    retry_count: NotRequired[int]
    simulation_validated: NotRequired[bool]


class ReviewState(TypedDict):
    """
    代码评审子图局部状态

    原则：
    - Clear Ownership: 子图拥有代码评审过程的所有数据
    - Minimal: 只包含代码评审必需的字段
    - State Isolation: 与全局状态隔离，通过转换函数交互
    """
    # === 任务标识（继承自全局） ===
    task_id: str

    # === 输入数据（继承自全局） ===
    code: str
    language: str
    optimization_level: str

    # === 评审阶段（子图内部） ===
    review_phase: str  # "detection", "suggestion", "validation", "negotiation", "completed"
    review_round: int  # 当前评审轮次（从1开始）

    # === 问题检测结果（子图核心数据） ===
    detected_issues: List[CodeIssue]
    issue_categories: Dict[str, int]  # 按类型统计问题数量

    # === 优化建议（子图核心数据） ===
    generated_suggestions: List[Suggestion]
    validated_suggestions: List[str]  # 已验证通过的建议ID
    rejected_suggestions: List[str]  # 已拒绝的建议ID

    # === 协商/对抗模式状态（子图内部） ===
    iteration_count: int  # 迭代次数
    consensus_reached: bool
    confidence_score: NotRequired[float]  # 建议的置信度

    # === 代码改进（子图生成） ===
    improved_code_versions: List[str]
    current_code_version: int

    # === 质量评估（子图分析结果） ===
    quality_metrics: NotRequired[Dict[str, float]]  # {"readability": 8.5, "maintainability": 7.2, "performance": 9.1}
    quality_threshold: float  # 质量阈值

    # === 验证结果（子图内部） ===
    validation_results: List[Dict[str, Any]]
    test_cases_passed: int
    test_cases_failed: int

    # === 错误处理（子图内部） ===
    error_info: NotRequired[str]


# ============================================================================
# 状态工厂（创建和初始化）
# ============================================================================

class StateFactory:
    """状态工厂：创建和初始化各种状态对象"""

    @staticmethod
    def create_global_state(
        task_id: str,
        user_id: str,
        code: str,
        language: str,
        optimization_level: str = "balanced"
    ) -> GlobalState:
        """创建初始的全局状态"""
        now = datetime.now(timezone.utc)
        return GlobalState(
            task_id=task_id,
            user_id=user_id,
            original_code=code,
            language=language,
            optimization_level=optimization_level,
            status=StateTaskStatus.PENDING,
            current_phase=Phase.ANALYSIS,
            progress=0.0,
            collaboration_mode=CollaborationMode.MASTER_EXPERT,
            active_agents=[],
            code_versions=[code],
            decision_history=[],
            human_intervention_required=False,
            shared_context={},
            created_at=now,
            updated_at=now,
            retry_count=0
        )

    @staticmethod
    def create_dissection_state(
        task_id: str,
        code: str,
        language: str,
        input_data: Optional[Dict[str, Any]] = None
    ) -> DissectionState:
        """创建算法拆解子图状态"""
        state = DissectionState(
            task_id=task_id,
            code=code,
            language=language,
            analysis_phase="parsing",
            execution_steps=[],
            current_step=0,
            data_structures_used=[]
        )
        if input_data:
            state['input_data'] = input_data
        return state

    @staticmethod
    def create_review_state(
        task_id: str,
        code: str,
        language: str,
        optimization_level: str,
        quality_threshold: float = 7.0
    ) -> ReviewState:
        """创建代码评审子图状态"""
        return ReviewState(
            task_id=task_id,
            code=code,
            language=language,
            optimization_level=optimization_level,
            review_phase="detection",
            review_round=1,
            detected_issues=[],
            issue_categories={},
            generated_suggestions=[],
            validated_suggestions=[],
            rejected_suggestions=[],
            iteration_count=0,
            consensus_reached=False,
            improved_code_versions=[],
            current_code_version=0,
            quality_threshold=quality_threshold,
            validation_results=[],
            test_cases_passed=0,
            test_cases_failed=0
        )


# ============================================================================
# 状态转换器（全局状态 ↔ 子图状态）
# ============================================================================

class StateConverter:
    """状态转换器：在全局状态和子图状态之间转换"""

    @staticmethod
    def global_to_dissection(global_state: GlobalState) -> DissectionState:
        """将全局状态转换为算法拆解子图状态"""
        return StateFactory.create_dissection_state(
            task_id=global_state['task_id'],
            code=global_state['original_code'],
            language=global_state['language'],
            input_data=global_state.get('shared_context', {}).get('input_data')
        )

    @staticmethod
    def dissection_to_global(
        global_state: GlobalState,
        dissection_state: DissectionState
    ) -> GlobalState:
        """将算法拆解子图结果合并到全局状态"""
        # 更新算法讲解
        if 'algorithm_explanation' in dissection_state:
            global_state['algorithm_explanation'] = dissection_state['algorithm_explanation']

        # 更新共享上下文
        global_state['shared_context']['dissection_result'] = {
            'execution_steps': dissection_state.get('execution_steps', []),
            'variables_trace': dissection_state.get('variables_trace', {}),
            'execution_flow': dissection_state.get('execution_flow', []),
            'algorithm_type': dissection_state.get('algorithm_type'),
            'data_structures_used': dissection_state.get('data_structures_used', [])
        }

        # 更新错误信息
        if dissection_state.get('error_info'):
            global_state['last_error'] = f"算法拆解错误: {dissection_state['error_info']}"

        global_state['updated_at'] = datetime.utcnow()
        return global_state

    @staticmethod
    def global_to_review(global_state: GlobalState) -> ReviewState:
        """将全局状态转换为代码评审子图状态"""
        # 使用最新版本的代码
        latest_code = global_state['code_versions'][-1]

        return StateFactory.create_review_state(
            task_id=global_state['task_id'],
            code=latest_code,
            language=global_state['language'],
            optimization_level=global_state['optimization_level'],
            quality_threshold=global_state.get('shared_context', {}).get('quality_threshold', 7.0)
        )

    @staticmethod
    def review_to_global(
        global_state: GlobalState,
        review_state: ReviewState
    ) -> GlobalState:
        """将代码评审子图结果合并到全局状态"""
        # 更新检测到的问题
        if review_state.get('detected_issues'):
            global_state['detected_issues'] = review_state['detected_issues']

        # 更新优化建议
        if review_state.get('generated_suggestions'):
            global_state['optimization_suggestions'] = review_state['generated_suggestions']

        # 更新代码版本
        if review_state.get('improved_code_versions'):
            for improved_code in review_state['improved_code_versions']:
                if improved_code not in global_state['code_versions']:
                    global_state['code_versions'].append(improved_code)

        # 更新共享上下文
        global_state['shared_context']['review_result'] = {
            'iteration_count': review_state.get('iteration_count', 0),
            'consensus_reached': review_state.get('consensus_reached', False),
            'quality_metrics': review_state.get('quality_metrics', {}),
            'test_cases_passed': review_state.get('test_cases_passed', 0),
            'test_cases_failed': review_state.get('test_cases_failed', 0)
        }

        # 更新错误信息
        if review_state.get('error_info'):
            global_state['last_error'] = f"代码评审错误: {review_state['error_info']}"

        global_state['updated_at'] = datetime.utcnow()
        return global_state


# ============================================================================
# 状态工具（操作辅助）
# ============================================================================

class StateUtils:
    """状态工具：提供状态操作的辅助方法"""

    @staticmethod
    def update_progress(state: GlobalState, progress: float) -> None:
        """更新全局状态的进度"""
        state['progress'] = max(0.0, min(1.0, progress))
        state['updated_at'] = datetime.utcnow()

    @staticmethod
    def add_code_version(state: GlobalState, new_code: str) -> None:
        """添加新的代码版本"""
        if new_code not in state['code_versions']:
            state['code_versions'].append(new_code)
        state['updated_at'] = datetime.utcnow()

    @staticmethod
    def add_human_decision(state: GlobalState, decision: HumanDecision) -> None:
        """添加人工决策记录"""
        state['decision_history'].append(decision)
        state['updated_at'] = datetime.utcnow()

    @staticmethod
    def set_human_intervention(
        state: GlobalState,
        required: bool,
        decision_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """设置人工干预状态"""
        state['human_intervention_required'] = required
        if required and decision_data:
            state['pending_human_decision'] = decision_data
        elif not required and 'pending_human_decision' in state:
            del state['pending_human_decision']
        state['updated_at'] = datetime.utcnow()

    @staticmethod
    def set_error(state: Union[GlobalState, DissectionState, ReviewState], error_message: str) -> None:
        """设置错误信息"""
        state['error_info'] = error_message
        if isinstance(state, GlobalState):
            state['last_error'] = error_message
            state['status'] = StateTaskStatus.FAILED
        state['updated_at'] = datetime.utcnow() if 'updated_at' in state else None

    @staticmethod
    def clear_error(state: Union[GlobalState, DissectionState, ReviewState]) -> None:
        """清除错误信息"""
        if 'error_info' in state:
            del state['error_info']
        if isinstance(state, GlobalState) and 'last_error' in state:
            del state['last_error']
        if 'updated_at' in state:
            state['updated_at'] = datetime.utcnow()


# ============================================================================
# 状态验证器
# ============================================================================

class StateValidator:
    """状态验证器：确保状态数据的完整性和一致性"""

    @staticmethod
    def validate_global_state(state: GlobalState) -> List[str]:
        """验证全局状态"""
        errors = []

        # 必填字段检查
        required_fields = ["task_id", "user_id", "original_code", "language"]
        for field in required_fields:
            if not state.get(field):
                errors.append(f"缺少必填字段: {field}")

        # 进度值检查
        progress = state.get("progress", 0)
        if not (0.0 <= progress <= 1.0):
            errors.append(f"进度值必须在 0.0 到 1.0 之间，当前值: {progress}")

        # 代码版本历史检查
        if not state.get("code_versions"):
            errors.append("代码版本历史不能为空")

        # 重试次数检查
        if state.get("retry_count", 0) < 0:
            errors.append("重试次数不能为负数")

        return errors

    @staticmethod
    def validate_dissection_state(state: DissectionState) -> List[str]:
        """验证算法拆解状态"""
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
            errors.append(f"当前步骤索引超出范围: {current_step}, 总步骤数: {len(execution_steps)}")

        # 重试次数检查
        if state.get("retry_count", 0) < 0:
            errors.append("重试次数不能为负数")

        return errors

    @staticmethod
    def validate_review_state(state: ReviewState) -> List[str]:
        """验证代码评审状态"""
        errors = []

        # 必填字段检查
        required_fields = ["task_id", "code", "language", "review_phase"]
        for field in required_fields:
            if not state.get(field):
                errors.append(f"缺少必填字段: {field}")

        # 评审轮次检查
        review_round = state.get("review_round", 0)
        if review_round < 1:
            errors.append(f"评审轮次必须大于等于1，当前值: {review_round}")

        # 迭代次数检查
        iteration_count = state.get("iteration_count", 0)
        if iteration_count < 0:
            errors.append(f"迭代次数不能为负数，当前值: {iteration_count}")

        # 质量阈值检查
        quality_threshold = state.get("quality_threshold", 0)
        if not (0.0 <= quality_threshold <= 10.0):
            errors.append(f"质量阈值必须在 0.0 到 10.0 之间，当前值: {quality_threshold}")

        # 测试用例数量检查
        passed = state.get("test_cases_passed", 0)
        failed = state.get("test_cases_failed", 0)
        if passed < 0 or failed < 0:
            errors.append("测试用例数量不能为负数")

        return errors
