"""
算法拆解子图模块

本模块实现算法拆解子图的完整功能，包括：
- 算法步骤模拟
- 可视化讲解生成
- 子图构建和管理

主要组件：
- agents/: Agent类实现和提示词
- nodes.py: 节点函数实现
- builder.py: 子图构建器和管理器
"""

from .agents import (
    StepSimulatorAgent,
    VisualGeneratorAgent,
    StepType,
    ComplexityType,
    SimulationResult,
    VisualizationOutput
)

from .nodes import (
    step_simulator_node,
    visual_generator_node,
    check_simulation_result,
    handle_error
)

from .builder import (
    DissectionSubgraphBuilder,
    DissectionSubgraphManager,
)

__all__ = [
    # 智能体类
    "StepSimulatorAgent",
    "VisualGeneratorAgent",

    # 枚举和数据类
    "StepType",
    "ComplexityType",
    "SimulationResult",
    "VisualizationOutput",

    # 节点函数
    "step_simulator_node",
    "visual_generator_node",
    "check_simulation_result",
    "handle_error",

    # 构建器和管理器
    "DissectionSubgraphBuilder",
    "DissectionSubgraphManager",
]