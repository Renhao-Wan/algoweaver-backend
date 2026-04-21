"""
算法拆解子图节点实现

本模块实现算法拆解子图中的核心节点逻辑，包括：
- Step Simulator Agent: 算法步骤模拟节点
- Visual Generator Agent: 可视化生成节点

这些节点协作完成算法的逐步分析和可视化讲解生成。
"""

from app.api.deps import get_llm
from app.graph.state import DissectionState
from app.graph.tools.python_repl import PythonSandbox
from app.graph.subgraphs.dissection.agents import (
    StepSimulatorAgent,
    VisualGeneratorAgent
)
from app.core.logger import get_logger

logger = get_logger(__name__)


# 节点函数定义（用于 LangGraph）

async def step_simulator_node(state: DissectionState) -> DissectionState:
    """
    步骤模拟节点函数

    调用 StepSimulatorAgent 进行算法执行步骤模拟。

    Args:
        state: 当前拆解状态

    Returns:
        更新后的拆解状态，包含模拟结果
    """
    # 使用全局单例 LLM 实例
    llm = get_llm()

    sandbox = PythonSandbox()
    agent = StepSimulatorAgent(llm, sandbox)

    return await agent.simulate_algorithm_execution(state)


async def visual_generator_node(state: DissectionState) -> DissectionState:
    """
    可视化生成节点函数

    调用 VisualGeneratorAgent 生成算法可视化讲解。

    Args:
        state: 当前拆解状态

    Returns:
        更新后的拆解状态，包含可视化讲解
    """
    # 使用全局单例 LLM 实例
    llm = get_llm()

    agent = VisualGeneratorAgent(llm)

    return await agent.generate_algorithm_explanation(state)


# 辅助节点函数

async def check_simulation_result(state: DissectionState) -> DissectionState:
    """
    检查模拟结果节点

    验证算法模拟是否成功，决定是否需要重试。

    Args:
        state: 当前拆解状态

    Returns:
        更新后的拆解状态
    """
    try:
        # 检查是否有错误
        if state.get('error_info'):
            logger.warning(f"模拟结果包含错误: {state['error_info']}")

            # 检查重试次数
            retry_count = state.get('retry_count', 0)
            max_retries = 3

            if retry_count < max_retries:
                state['needs_retry'] = True
                state['retry_count'] = retry_count + 1
                logger.info(f"准备重试，当前重试次数: {retry_count + 1}/{max_retries}")
            else:
                state['needs_retry'] = False
                logger.error(f"已达到最大重试次数 ({max_retries})，停止重试")
        else:
            # 检查执行步骤是否生成
            if not state.get('execution_steps'):
                logger.warning("未生成执行步骤")
                state['needs_retry'] = True
                state['retry_count'] = state.get('retry_count', 0) + 1
            else:
                state['needs_retry'] = False
                logger.info(f"模拟结果验证通过，生成了 {len(state['execution_steps'])} 个步骤")

        return state

    except Exception as e:
        logger.error(f"检查模拟结果失败: {str(e)}")
        state['error_info'] = f"检查模拟结果失败: {str(e)}"
        state['needs_retry'] = False
        return state


async def handle_error(state: DissectionState) -> DissectionState:
    """
    错误处理节点

    处理算法拆解过程中的错误。

    Args:
        state: 当前拆解状态

    Returns:
        更新后的拆解状态
    """
    try:
        error_info = state.get('error_info', '未知错误')
        logger.error(f"算法拆解子图错误: {error_info}")

        # 记录错误到状态
        state['analysis_phase'] = "error"

        # 可以在这里添加更多的错误处理逻辑
        # 例如：发送通知、记录日志、生成错误报告等

        return state

    except Exception as e:
        logger.error(f"错误处理节点失败: {str(e)}")
        state['error_info'] = f"错误处理失败: {str(e)}"
        return state
