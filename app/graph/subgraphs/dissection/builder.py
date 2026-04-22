"""
算法拆解子图构建器

本模块负责构建算法拆解子图，定义节点间的顺序协作流程。
算法拆解子图采用顺序协作模式，按照以下流程执行：
1. Step Simulator Agent - 模拟算法执行步骤
2. Visual Generator Agent - 生成可视化讲解

子图支持状态隔离，使用 DissectionState 作为局部状态。
"""

from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, END

from app.graph.state import (
    DissectionState,
    StateFactory
)
from app.graph.subgraphs.dissection.nodes import (
    step_simulator_node,
    visual_generator_node
)
from app.core.logger import get_logger
from app.core.checkpointer import create_checkpointer

logger = get_logger(__name__)


class DissectionSubgraphBuilder:
    """
    算法拆解子图构建器
    
    负责构建和配置算法拆解子图，定义节点间的执行流程和状态传递。
    """
    
    def __init__(self):
        self.graph = None
        self.compiled_graph = None
    
    def build_dissection_subgraph(self) -> StateGraph:
        """
        构建算法拆解子图
        
        Returns:
            配置完成的算法拆解子图
        """
        logger.info("开始构建算法拆解子图")
        
        # 创建状态图
        self.graph = StateGraph(DissectionState)
        
        # 添加节点
        self._add_nodes()
        
        # 定义边和流程
        self._define_edges()
        
        # 设置入口和出口
        self._set_entry_and_exit()
        
        logger.info("算法拆解子图构建完成")
        return self.graph
    
    def _add_nodes(self):
        """添加子图节点"""
        logger.debug("添加算法拆解子图节点")
        
        # 添加步骤模拟节点
        self.graph.add_node("step_simulator", step_simulator_node)
        
        # 添加可视化生成节点
        self.graph.add_node("visual_generator", visual_generator_node)
        
        # 添加条件检查节点
        self.graph.add_node("check_simulation_result", self._check_simulation_result)
        
        # 添加错误处理节点
        self.graph.add_node("handle_error", self._handle_error)
    
    def _define_edges(self):
        """定义节点间的边和执行流程"""
        logger.debug("定义算法拆解子图执行流程")
        
        # 主要执行流程：步骤模拟 -> 结果检查 -> 可视化生成
        self.graph.add_edge("step_simulator", "check_simulation_result")
        
        # 条件边：根据模拟结果决定下一步
        self.graph.add_conditional_edges(
            "check_simulation_result",
            self._route_after_simulation,
            {
                "continue": "visual_generator",
                "error": "handle_error",
                "retry": "step_simulator"
            }
        )
        
        # 可视化生成完成后结束
        self.graph.add_edge("visual_generator", END)
        
        # 错误处理后结束
        self.graph.add_edge("handle_error", END)
    
    def _set_entry_and_exit(self):
        """设置子图的入口和出口"""
        logger.debug("设置算法拆解子图入口和出口")
        
        # 设置入口点
        self.graph.set_entry_point("step_simulator")
        
        # 设置完成条件（通过 END 节点自动处理）
    
    def compile_subgraph(self, checkpointer=None) -> Any:
        """
        编译子图
        
        Args:
            checkpointer: 检查点保存器，用于状态持久化
            
        Returns:
            编译后的可执行子图
        """
        if not self.graph:
            raise ValueError("子图尚未构建，请先调用 build_dissection_subgraph()")

        logger.info("编译算法拆解子图")

        # 使用统一的 checkpointer 创建逻辑
        if checkpointer is None:
            checkpointer = create_checkpointer()

        # 编译子图
        self.compiled_graph = self.graph.compile(checkpointer=checkpointer)

        logger.info("算法拆解子图编译完成")
        return self.compiled_graph
    
    async def _check_simulation_result(self, state: DissectionState) -> DissectionState:
        """
        检查算法模拟结果

        Args:
            state: 当前拆解状态

        Returns:
            更新后的拆解状态
        """
        logger.debug("检查算法模拟结果")

        try:
            # 检查是否有错误
            if state.get('error_info'):
                logger.warning(f"算法模拟出现错误: {state['error_info']}")

                # 更新重试计数
                retry_count = state.get('retry_count', 0)
                if retry_count < 3:  # 最多重试3次
                    state['retry_count'] = retry_count + 1
                    state['needs_retry'] = True
                    logger.info(f"算法模拟失败，准备进行第 {state['retry_count']} 次重试")
                else:
                    state['needs_retry'] = False
                    logger.error("算法模拟重试次数超限")

                return state

            # 检查执行步骤是否生成
            if not state.get('execution_steps'):
                logger.warning("未生成执行步骤")
                state['error_info'] = "未能生成算法执行步骤"

                # 更新重试计数
                retry_count = state.get('retry_count', 0)
                if retry_count < 3:  # 最多重试3次
                    state['retry_count'] = retry_count + 1
                    state['needs_retry'] = True
                    logger.info(f"算法模拟失败，准备进行第 {state['retry_count']} 次重试")
                else:
                    state['needs_retry'] = False
                    logger.error("算法模拟重试次数超限")

                return state

            # 检查变量追踪是否有效
            if not state.get('variables_trace'):
                logger.info("变量追踪为空，可能是简单算法")

            # 标记检查通过，重置重试计数
            state['simulation_validated'] = True
            state['retry_count'] = 0
            logger.debug("算法模拟结果检查通过")

            return state

        except Exception as e:
            logger.error(f"检查模拟结果时发生错误: {str(e)}")
            state['error_info'] = f"检查模拟结果失败: {str(e)}"
            state['needs_retry'] = False
            return state
    
    def _route_after_simulation(self, state: DissectionState) -> str:
        """
        根据模拟结果决定路由

        Args:
            state: 当前拆解状态

        Returns:
            下一个节点的名称
        """
        logger.debug("根据模拟结果进行路由决策")

        # 如果有错误且需要重试
        if state.get('error_info') and state.get('needs_retry'):
            retry_count = state.get('retry_count', 0)
            logger.info(f"路由决策: 重试 (当前重试次数: {retry_count})")
            return "retry"

        # 如果有错误但不需要重试（超过重试次数）
        if state.get('error_info'):
            logger.warning("路由决策: 转入错误处理")
            return "error"

        # 如果模拟结果验证通过
        if state.get('simulation_validated', False):
            logger.debug("路由决策: 继续可视化生成")
            return "continue"

        # 默认情况下继续执行
        logger.debug("路由决策: 使用默认路由，继续可视化生成")
        return "continue"
    
    async def _handle_error(self, state: DissectionState) -> DissectionState:
        """
        处理子图执行错误
        
        Args:
            state: 当前拆解状态
            
        Returns:
            更新后的拆解状态
        """
        logger.error("处理算法拆解子图错误")
        
        try:
            # 记录错误信息
            error_msg = state.get('error_info') or "未知错误"
            logger.error(f"算法拆解失败: {error_msg}")

            # 生成错误报告
            state['algorithm_explanation'] = self._create_error_explanation(error_msg)

            return state
            
        except Exception as e:
            logger.error(f"错误处理过程中发生异常: {str(e)}")
            state['error_info'] = f"错误处理失败: {str(e)}"
            return state
    
    def _create_error_explanation(self, error_msg: str) -> Any:
        """
        创建错误说明
        
        Args:
            error_msg: 错误信息
            
        Returns:
            错误说明对象
        """
        from app.graph.state import AlgorithmExplanation
        
        return AlgorithmExplanation(
            steps=[],
            pseudocode="# 算法分析失败",
            time_complexity="未知",
            space_complexity="未知",
            visualization=None,
            step_explanations=[f"算法分析过程中出现错误: {error_msg}"],
            teaching_notes=["建议检查代码语法和逻辑", "确保输入数据格式正确"]
        )


class DissectionSubgraphManager:
    """
    算法拆解子图管理器
    
    提供子图的创建、配置和执行管理功能。
    """
    
    def __init__(self):
        self.builder = DissectionSubgraphBuilder()
        self.subgraph = None
        self.compiled_subgraph = None
    
    def initialize_subgraph(self, checkpointer=None) -> Any:
        """
        初始化算法拆解子图
        
        Args:
            checkpointer: 检查点保存器
            
        Returns:
            编译后的子图实例
        """
        logger.info("初始化算法拆解子图")
        
        try:
            # 构建子图
            self.subgraph = self.builder.build_dissection_subgraph()
            
            # 编译子图
            self.compiled_subgraph = self.builder.compile_subgraph(checkpointer)
            
            logger.info("算法拆解子图初始化完成")
            return self.compiled_subgraph
            
        except Exception as e:
            logger.error(f"初始化算法拆解子图失败: {str(e)}")
            raise
    
    async def execute_dissection(
        self,
        code: str,
        language: str,
        task_id: str,
        input_data: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> DissectionState:
        """
        执行算法拆解

        Args:
            code: 要分析的代码
            language: 编程语言
            task_id: 任务ID
            input_data: 输入数据
            config: 执行配置

        Returns:
            拆解结果状态
        """
        if not self.compiled_subgraph:
            raise ValueError("子图尚未初始化，请先调用 initialize_subgraph()")

        logger.info(f"开始执行算法拆解，代码长度: {len(code)} 字符")

        try:
            # 使用 StateFactory 创建初始状态
            initial_state = StateFactory.create_dissection_state(
                task_id=task_id,
                code=code,
                language=language,
                input_data=input_data
            )

            # 执行子图
            result = await self.compiled_subgraph.ainvoke(
                initial_state,
                config=config or {}
            )

            logger.info("算法拆解执行完成")
            return result

        except Exception as e:
            logger.error(f"执行算法拆解失败: {str(e)}")
            raise
    
    def get_subgraph_info(self) -> Dict[str, Any]:
        """
        获取子图信息
        
        Returns:
            子图的配置和状态信息
        """
        return {
            "name": "algorithm_dissection_subgraph",
            "description": "算法拆解子图，负责分析算法执行过程并生成可视化讲解",
            "nodes": [
                "step_simulator",
                "visual_generator", 
                "check_simulation_result",
                "handle_error"
            ],
            "entry_point": "step_simulator",
            "state_type": "DissectionState",
            "collaboration_mode": "sequential",
            "initialized": self.compiled_subgraph is not None
        }


# ============================================================================
# LangGraph Studio 工厂函数
# ============================================================================

def create_dissection_subgraph_for_studio(checkpointer=None) -> Any:
    """
    创建算法拆解子图的工厂函数（用于 LangGraph Studio）

    Args:
        checkpointer: 检查点保存器
            - 如果为 None：使用 create_checkpointer() 创建
            - 如果为 dict：LangGraph Studio 传入的配置，忽略并使用 create_checkpointer()
            - 如果为 BaseCheckpointSaver：直接使用

    Returns:
        编译后的算法拆解子图
    """
    # LangGraph Studio 传入的是 dict 配置，我们需要忽略它
    if checkpointer is None or isinstance(checkpointer, dict):
        checkpointer = None  # 让 Manager 使用默认的 create_checkpointer()

    manager = DissectionSubgraphManager()
    return manager.initialize_subgraph(checkpointer)


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    "DissectionState",
    "DissectionSubgraphBuilder",
    "DissectionSubgraphManager",
]
