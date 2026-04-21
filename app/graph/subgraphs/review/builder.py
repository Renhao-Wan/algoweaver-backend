"""
代码评审子图构建器

本模块负责构建代码评审子图，定义节点间的协商/对抗模式流程。
代码评审子图采用协商/对抗模式，支持多轮迭代优化：
1. Mistake Detector Agent - 检测代码问题
2. Suggestion Generator Agent - 生成优化建议
3. Validation Tester Agent - 验证改进效果
4. 根据验证结果决定是否继续迭代或完成评审

子图支持状态隔离，使用 ReviewState 作为局部状态。
"""

from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.graph.state import (
    ReviewState,
    StateFactory
)
from app.graph.subgraphs.review.agents import (
    ReviewPhase
)
from app.graph.subgraphs.review.nodes import (
    mistake_detector_node,
    suggestion_generator_node,
    validation_tester_node
)
from app.core.logger import get_logger

logger = get_logger(__name__)


class ReviewSubgraphBuilder:
    """
    代码评审子图构建器

    负责构建和配置代码评审子图，定义节点间的执行流程和状态传递。
    支持协商/对抗模式的多轮迭代评审。
    """

    def __init__(self, max_review_rounds: int = 3):
        self.graph = None
        self.compiled_graph = None
        self.max_review_rounds = max_review_rounds

    def build_review_subgraph(self) -> StateGraph:
        """
        构建代码评审子图

        Returns:
            配置完成的代码评审子图
        """
        logger.info("开始构建代码评审子图")

        # 创建状态图
        self.graph = StateGraph(ReviewState)

        # 添加节点
        self._add_nodes()

        # 定义边和流程
        self._define_edges()

        # 设置入口和出口
        self._set_entry_and_exit()

        logger.info("代码评审子图构建完成")
        return self.graph

    def _add_nodes(self):
        """添加子图节点"""
        logger.debug("添加代码评审子图节点")

        # 添加问题检测节点
        self.graph.add_node("mistake_detector", mistake_detector_node)

        # 添加建议生成节点
        self.graph.add_node("suggestion_generator", suggestion_generator_node)

        # 添加验证测试节点
        self.graph.add_node("validation_tester", validation_tester_node)

        # 添加协商决策节点
        self.graph.add_node("negotiation_decision", self._negotiation_decision)

        # 添加错误处理节点
        self.graph.add_node("handle_error", self._handle_error)

    def _define_edges(self):
        """定义节点间的边和执行流程"""
        logger.debug("定义代码评审子图执行流程")

        # 主要执行流程：问题检测 -> 建议生成 -> 验证测试 -> 协商决策
        self.graph.add_edge("mistake_detector", "suggestion_generator")
        self.graph.add_edge("suggestion_generator", "validation_tester")
        self.graph.add_edge("validation_tester", "negotiation_decision")

        # 条件边：根据协商结果决定下一步
        self.graph.add_conditional_edges(
            "negotiation_decision",
            self._route_after_negotiation,
            {
                "continue": "suggestion_generator",  # 继续迭代优化
                "complete": END,  # 评审完成
                "error": "handle_error"  # 错误处理
            }
        )

        # 错误处理后结束
        self.graph.add_edge("handle_error", END)

    def _set_entry_and_exit(self):
        """设置子图的入口和出口"""
        logger.debug("设置代码评审子图入口和出口")

        # 设置入口点
        self.graph.set_entry_point("mistake_detector")

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
            raise ValueError("子图尚未构建，请先调用 build_review_subgraph()")

        logger.info("编译代码评审子图")

        # 使用默认的内存检查点保存器
        if checkpointer is None:
            checkpointer = MemorySaver()

        # 编译子图
        self.compiled_graph = self.graph.compile(checkpointer=checkpointer)

        logger.info("代码评审子图编译完成")
        return self.compiled_graph

    async def _negotiation_decision(self, state: ReviewState) -> ReviewState:
        """
        协商决策节点

        根据验证结果和当前状态，决定是否继续迭代或完成评审。

        Args:
            state: 当前评审状态

        Returns:
            更新后的评审状态
        """
        logger.debug("进行协商决策")

        try:
            # 检查是否达成共识
            if state.get('consensus_reached', False):
                logger.info("评审达成共识，准备完成")
                state['review_phase'] = ReviewPhase.COMPLETED.value
                return state

            # 检查是否超过最大迭代轮次
            if state['review_round'] >= self.max_review_rounds:
                logger.warning(f"达到最大评审轮次 {self.max_review_rounds}，强制完成")
                state['consensus_reached'] = True
                state['review_phase'] = ReviewPhase.COMPLETED.value
                return state

            # 检查质量评分
            quality_metrics = state.get('quality_metrics', {})
            quality_score = quality_metrics.get('overall_score', 0)
            quality_threshold = state.get('quality_threshold', 7.0)

            if quality_score >= quality_threshold:
                logger.info(f"质量评分 {quality_score} 达到阈值 {quality_threshold}")
                state['consensus_reached'] = True
                state['review_phase'] = ReviewPhase.COMPLETED.value
                return state

            # 检查验证结果
            if state.get('validation_results'):
                latest_validation = state['validation_results'][-1]
                failed_tests = latest_validation.get('failed_tests', 0)

                if failed_tests == 0:
                    logger.info("所有验证测试通过")
                    state['consensus_reached'] = True
                    state['review_phase'] = ReviewPhase.COMPLETED.value
                    return state

            # 需要继续迭代
            logger.info(f"质量评分 {quality_score} 未达到阈值，准备第 {state['review_round'] + 1} 轮评审")
            state['review_round'] += 1
            state['review_phase'] = ReviewPhase.SUGGESTION.value

            return state

        except Exception as e:
            logger.error(f"协商决策失败: {str(e)}")
            state['review_phase'] = ReviewPhase.COMPLETED.value
            state['consensus_reached'] = False
            return state

    def _route_after_negotiation(self, state: ReviewState) -> str:
        """
        根据协商结果决定路由

        Args:
            state: 当前评审状态

        Returns:
            下一个节点的名称
        """
        logger.debug("根据协商结果进行路由决策")

        # 检查是否有错误
        if state.get('error_info'):
            logger.warning("评审过程中出现错误")
            return "error"

        # 检查是否达成共识
        if state.get('consensus_reached', False):
            logger.debug("评审达成共识，完成评审")
            return "complete"

        # 检查是否超过最大轮次
        if state['review_round'] >= self.max_review_rounds:
            logger.warning("达到最大评审轮次，强制完成")
            return "complete"

        # 继续迭代
        logger.debug(f"继续第 {state['review_round']} 轮评审")
        return "continue"

    async def _handle_error(self, state: ReviewState) -> ReviewState:
        """
        处理子图执行错误

        Args:
            state: 当前评审状态

        Returns:
            更新后的评审状态
        """
        logger.error("处理代码评审子图错误")

        try:
            # 获取错误信息
            error_msg = state.get('error_info', '未知错误')
            logger.error(f"代码评审失败: {error_msg}")

            # 标记为错误状态
            state['review_phase'] = ReviewPhase.COMPLETED.value
            state['consensus_reached'] = False

            # 如果有部分结果，保留它们
            if not state.get('generated_suggestions'):
                state['generated_suggestions'] = []

            return state

        except Exception as e:
            logger.error(f"错误处理过程中发生异常: {str(e)}")
            state['review_phase'] = ReviewPhase.COMPLETED.value
            state['error_info'] = f"错误处理失败: {str(e)}"
            return state


class ReviewSubgraphManager:
    """
    代码评审子图管理器

    提供子图的创建、配置和执行管理功能。
    """

    def __init__(self, max_review_rounds: int = 3):
        self.builder = ReviewSubgraphBuilder(max_review_rounds)
        self.subgraph = None
        self.compiled_subgraph = None

    def initialize_subgraph(self, checkpointer=None) -> Any:
        """
        初始化代码评审子图

        Args:
            checkpointer: 检查点保存器

        Returns:
            编译后的子图实例
        """
        logger.info("初始化代码评审子图")

        try:
            # 构建子图
            self.subgraph = self.builder.build_review_subgraph()

            # 编译子图
            self.compiled_subgraph = self.builder.compile_subgraph(checkpointer)

            logger.info("代码评审子图初始化完成")
            return self.compiled_subgraph

        except Exception as e:
            logger.error(f"初始化代码评审子图失败: {str(e)}")
            raise

    async def execute_review(
        self,
        code: str,
        language: str,
        task_id: str,
        optimization_level: str = "balanced",
        quality_threshold: float = 7.0,
        config: Optional[Dict[str, Any]] = None
    ) -> ReviewState:
        """
        执行代码评审

        Args:
            code: 要评审的代码
            language: 编程语言
            task_id: 任务ID
            optimization_level: 优化级别
            quality_threshold: 质量阈值
            config: 执行配置

        Returns:
            评审结果状态
        """
        if not self.compiled_subgraph:
            raise ValueError("子图尚未初始化，请先调用 initialize_subgraph()")

        logger.info(f"开始执行代码评审，代码长度: {len(code)} 字符")

        try:
            # 使用 StateFactory 创建初始状态
            initial_state = StateFactory.create_review_state(
                task_id=task_id,
                code=code,
                language=language,
                optimization_level=optimization_level,
                quality_threshold=quality_threshold
            )

            # 执行子图
            result = await self.compiled_subgraph.ainvoke(
                initial_state,
                config=config or {}
            )

            logger.info("代码评审执行完成")
            return result

        except Exception as e:
            logger.error(f"执行代码评审失败: {str(e)}")
            raise

    def get_subgraph_info(self) -> Dict[str, Any]:
        """
        获取子图信息

        Returns:
            子图的配置和状态信息
        """
        return {
            "name": "code_review_subgraph",
            "description": "代码评审子图，负责检测代码问题并生成优化建议",
            "nodes": [
                "mistake_detector",
                "suggestion_generator",
                "validation_tester",
                "negotiation_decision",
                "handle_error"
            ],
            "entry_point": "mistake_detector",
            "state_type": "ReviewState",
            "collaboration_mode": "adversarial",
            "max_review_rounds": self.builder.max_review_rounds,
            "initialized": self.compiled_subgraph is not None
        }


# 工厂函数

def create_review_subgraph(checkpointer=None, max_review_rounds: int = 3) -> Any:
    """
    创建代码评审子图的工厂函数

    Args:
        checkpointer: 检查点保存器
        max_review_rounds: 最大评审轮次

    Returns:
        编译后的代码评审子图
    """
    manager = ReviewSubgraphManager(max_review_rounds)
    return manager.initialize_subgraph(checkpointer)



def create_review_manager(max_review_rounds: int = 3) -> ReviewSubgraphManager:
    """
    创建代码评审子图管理器的工厂函数

    Args:
        max_review_rounds: 最大评审轮次

    Returns:
        代码评审子图管理器实例
    """
    return ReviewSubgraphManager(max_review_rounds)

