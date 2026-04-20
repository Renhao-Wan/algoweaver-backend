"""
算法拆解子图 Agents 模块

导出 Agent 类和提示词模板，供节点函数使用。
"""

from app.graph.subgraphs.dissection.agents.agent import (
    StepSimulatorAgent,
    VisualGeneratorAgent,
    StepType,
    ComplexityType,
    SimulationResult,
    VisualizationOutput
)

from app.graph.subgraphs.dissection.agents.prompts import (
    DissectionPrompts,
    get_simulation_prompt,
    get_visualization_prompt,
    get_pseudocode_generation_prompt,
    get_complexity_analysis_prompt,
    get_teaching_notes_prompt
)

__all__ = [
    # Agent 类
    "StepSimulatorAgent",
    "VisualGeneratorAgent",
    # 枚举类型
    "StepType",
    "ComplexityType",
    # 数据类
    "SimulationResult",
    "VisualizationOutput",
    # 提示词类
    "DissectionPrompts",
    # 提示词函数
    "get_simulation_prompt",
    "get_visualization_prompt",
    "get_pseudocode_generation_prompt",
    "get_complexity_analysis_prompt",
    "get_teaching_notes_prompt",
]
