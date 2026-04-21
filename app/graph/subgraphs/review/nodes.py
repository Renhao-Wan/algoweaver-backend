"""
代码评审子图节点实现

本模块实现代码评审子图中的核心节点逻辑，包括：
- Mistake Detector Agent: 问题检测节点
- Suggestion Generator Agent: 建议生成节点
- Validation Tester Agent: 验证测试节点

这些节点协作完成代码质量检测和优化建议生成，支持协商/对抗模式的多轮评审。
"""

from app.api.deps import get_llm
from app.graph.state import ReviewState
from app.graph.tools.python_repl import PythonSandbox
from app.graph.subgraphs.review.agents import (
    MistakeDetectorAgent,
    SuggestionGeneratorAgent,
    ValidationTesterAgent
)
from app.core.logger import get_logger

logger = get_logger(__name__)


# 节点函数定义（用于 LangGraph）

async def mistake_detector_node(state: ReviewState) -> ReviewState:
    """
    问题检测节点函数

    调用 MistakeDetectorAgent 进行代码问题检测。

    Args:
        state: 当前评审状态

    Returns:
        更新后的评审状态，包含检测到的问题
    """
    # 使用全局单例 LLM 实例
    llm = get_llm()

    sandbox = PythonSandbox()
    agent = MistakeDetectorAgent(llm, sandbox)

    return await agent.detect_code_issues(state)


async def suggestion_generator_node(state: ReviewState) -> ReviewState:
    """
    建议生成节点函数

    调用 SuggestionGeneratorAgent 生成优化建议。

    Args:
        state: 当前评审状态

    Returns:
        更新后的评审状态，包含优化建议
    """
    # 使用全局单例 LLM 实例
    llm = get_llm()

    agent = SuggestionGeneratorAgent(llm)

    return await agent.generate_suggestions(state)


async def validation_tester_node(state: ReviewState) -> ReviewState:
    """
    验证测试节点函数

    调用 ValidationTesterAgent 验证代码改进。

    Args:
        state: 当前评审状态

    Returns:
        更新后的评审状态，包含验证结果
    """
    # 使用全局单例 LLM 实例
    llm = get_llm()

    sandbox = PythonSandbox()
    agent = ValidationTesterAgent(llm, sandbox)

    return await agent.validate_improvements(state)


# 辅助节点函数

async def check_review_result(state: ReviewState) -> ReviewState:
    """
    检查评审结果节点

    验证评审是否完成，决定是否需要继续迭代。

    Args:
        state: 当前评审状态

    Returns:
        更新后的评审状态
    """
    try:
        # 检查是否达成共识
        if state.get('consensus_reached', False):
            logger.info("评审达成共识，流程完成")
            state['review_phase'] = "completed"
            return state

        # 检查迭代次数
        max_iterations = 5
        current_iteration = state.get('iteration_count', 0)

        if current_iteration >= max_iterations:
            logger.warning(f"已达到最大迭代次数 ({max_iterations})，强制结束评审")
            state['consensus_reached'] = True
            state['review_phase'] = "completed"
            return state

        # 检查质量评分
        quality_score = state.get('quality_metrics', {}).get('overall_score', 0)
        quality_threshold = state.get('quality_threshold', 7.0)

        if quality_score >= quality_threshold:
            logger.info(f"质量评分 {quality_score} 达到阈值 {quality_threshold}")
            state['consensus_reached'] = True
            state['review_phase'] = "completed"
        else:
            logger.info(f"质量评分 {quality_score} 未达到阈值，继续迭代")
            state['review_phase'] = "negotiation"

        return state

    except Exception as e:
        logger.error(f"检查评审结果失败: {str(e)}")
        state['error_info'] = f"检查评审结果失败: {str(e)}"
        return state


async def handle_negotiation(state: ReviewState) -> ReviewState:
    """
    处理协商节点

    在多轮评审中处理协商逻辑。

    Args:
        state: 当前评审状态

    Returns:
        更新后的评审状态
    """
    try:
        logger.info("进入协商阶段")

        # 增加迭代计数
        state['iteration_count'] = state.get('iteration_count', 0) + 1

        # 分析当前问题
        unfixed_issues = []
        for issue in state.get('detected_issues', []):
            # 检查问题是否已修复
            is_fixed = any(
                s.issue_id == issue.issue_id
                for s in state.get('generated_suggestions', [])
            )
            if not is_fixed:
                unfixed_issues.append(issue)

        if unfixed_issues:
            logger.info(f"还有 {len(unfixed_issues)} 个问题未修复，继续生成建议")
            state['review_phase'] = "suggestion"
        else:
            logger.info("所有问题已修复，进入验证阶段")
            state['review_phase'] = "validation"

        return state

    except Exception as e:
        logger.error(f"处理协商失败: {str(e)}")
        state['error_info'] = f"处理协商失败: {str(e)}"
        return state


async def handle_error(state: ReviewState) -> ReviewState:
    """
    错误处理节点

    处理代码评审过程中的错误。

    Args:
        state: 当前评审状态

    Returns:
        更新后的评审状态
    """
    try:
        error_info = state.get('error_info', '未知错误')
        logger.error(f"代码评审子图错误: {error_info}")

        # 记录错误到状态
        state['review_phase'] = "error"

        # 可以在这里添加更多的错误处理逻辑
        # 例如：发送通知、记录日志、生成错误报告等

        return state

    except Exception as e:
        logger.error(f"错误处理节点失败: {str(e)}")
        state['error_info'] = f"错误处理失败: {str(e)}"
        return state
