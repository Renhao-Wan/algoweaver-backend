"""
Supervisor 主控调度模块

提供全局任务调度和智能体协调功能。
"""

from app.graph.supervisor.agent import (
    SupervisorAgent,
    TaskType,
    NextStep,
    RecoveryStrategy,
    TaskPlan,
    RoutingDecision,
    CoordinationResult,
    ErrorHandlingPlan,
    supervisor_analyze_task_node,
    supervisor_routing_node
)

from app.graph.supervisor.prompts import (
    SupervisorPrompts,
    get_task_analysis_prompt,
    get_routing_decision_prompt,
    get_coordination_prompt,
    get_human_intervention_prompt,
    get_error_handling_prompt,
    get_summary_generation_prompt
)

__all__ = [
    # 核心类
    "SupervisorAgent",

    # 枚举
    "TaskType",
    "NextStep",
    "RecoveryStrategy",

    # 数据类
    "TaskPlan",
    "RoutingDecision",
    "CoordinationResult",
    "ErrorHandlingPlan",

    # 节点函数
    "supervisor_analyze_task_node",
    "supervisor_routing_node",

    # 提示词类和函数
    "SupervisorPrompts",
    "get_task_analysis_prompt",
    "get_routing_decision_prompt",
    "get_coordination_prompt",
    "get_human_intervention_prompt",
    "get_error_handling_prompt",
    "get_summary_generation_prompt"
]
