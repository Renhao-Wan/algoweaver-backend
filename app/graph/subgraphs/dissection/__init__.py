"""
算法拆解子图模块

本模块实现算法拆解子图的完整功能，包括：
- 算法步骤模拟
- 可视化讲解生成
- 子图构建和管理

主要组件：
- nodes.py: 节点实现（StepSimulatorAgent, VisualGeneratorAgent）
- builder.py: 子图构建器和管理器
"""

from .nodes import (
    StepSimulatorAgent,
    VisualGeneratorAgent,
    step_simulator_node,
    visual_generator_node
)

from .builder import (
    DissectionSubgraphBuilder,
    DissectionSubgraphManager,
    create_dissection_subgraph,
    create_dissection_manager,
    convert_global_to_dissection_state,
    merge_dissection_to_global_state
)

__all__ = [
    # 智能体类
    "StepSimulatorAgent",
    "VisualGeneratorAgent",
    
    # 节点函数
    "step_simulator_node", 
    "visual_generator_node",
    
    # 构建器和管理器
    "DissectionSubgraphBuilder",
    "DissectionSubgraphManager",
    
    # 工厂函数
    "create_dissection_subgraph",
    "create_dissection_manager",
    
    # 状态转换函数
    "convert_global_to_dissection_state",
    "merge_dissection_to_global_state"
]