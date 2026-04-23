"""
主图构建器 (Main Graph Builder)

本模块负责构建 AlgoWeaver AI 系统的主图，整合 Supervisor Agent 和各个子图，
实现全局任务调度、动态路由和 Human-in-the-loop 机制。

主图架构：
1. 任务分析节点 (supervisor_analyze_task) - 分析用户任务，制定执行计划
2. 路由决策节点 (supervisor_routing) - 根据当前状态决定下一步执行路径
3. 算法拆解子图 (dissection_subgraph) - 执行算法分析和讲解生成
4. 代码评审子图 (review_subgraph) - 执行代码质量检测和优化建议
5. Human-in-the-loop 节点 (human_intervention) - 处理人工干预请求
6. 总结生成节点 (generate_summary) - 生成最终任务执行总结

主图支持：
- 动态路由：根据 Supervisor 决策动态选择执行路径
- 状态持久化：通过 Checkpointer 支持任务暂停和恢复
- Human-in-the-loop：强制人工确认关键决策
- 错误恢复：自动重试和降级处理


Checkpointer 传递链路：

应用运行时（单例模式）：
  FastAPI → get_graph_manager()
    → MainGraphManager(checkpointer=get_checkpointer())  # 全局单例
      → MainGraphBuilder(checkpointer=单例)
        → dissection_subgraph.compile(checkpointer=单例)  # 传递给子图
        → review_subgraph.compile(checkpointer=单例)      # 传递给子图
  结果：主图和所有子图共享同一个 checkpointer 实例

LangGraph Studio（独立实例）：
  langgraph.json → create_main_graph_for_studio(checkpointer=None)
    → MainGraphBuilder(checkpointer=create_checkpointer())  # 新实例
      → dissection_subgraph.compile(checkpointer=新实例)  # 传递给子图
      → review_subgraph.compile(checkpointer=新实例)      # 传递给子图
  结果：每次调试使用独立的 checkpointer 实例
"""

from typing import Dict, Any
from datetime import datetime, timezone
from dataclasses import asdict
import time
import uuid
from langgraph.graph import StateGraph, END
from langgraph.types import interrupt

from app.graph.state import (
    GlobalState,
    StateTaskStatus,
    Phase,
    StateConverter,
    HumanDecision
)
from app.graph.supervisor.agent import (
    NextStep,
    supervisor_analyze_task_node,
    supervisor_routing_node
)
from app.graph.subgraphs.dissection.builder import DissectionSubgraphBuilder
from app.graph.subgraphs.review.builder import ReviewSubgraphBuilder
from app.core.logger import get_logger, log_graph_execution, log_agent_execution
from app.core.checkpointer import create_checkpointer

logger = get_logger(__name__)


class MainGraphBuilder:
    """
    主图构建器

    负责构建和配置主图，整合 Supervisor Agent 和各个子图，
    实现全局任务调度和动态路由。
    """

    def __init__(self, checkpointer=None):
        """
        初始化主图构建器

        Args:
            checkpointer: 状态持久化器，如果为 None 则创建新实例

        Note:
            - LLM 实例由各个节点通过 get_llm_instance() 获取
            - Checkpointer 通过 create_checkpointer() 创建（使用统一配置）
        """
        self.checkpointer = checkpointer or create_checkpointer()
        self.graph = None
        self.compiled_graph = None

        # 构建子图
        self.dissection_subgraph = self._build_dissection_subgraph()
        self.review_subgraph = self._build_review_subgraph()

    def _build_dissection_subgraph(self):
        """构建算法拆解子图"""
        logger.info("构建算法拆解子图")
        builder = DissectionSubgraphBuilder()
        subgraph = builder.build_dissection_subgraph()
        # 使用主图的 checkpointer 编译子图
        return subgraph.compile(checkpointer=self.checkpointer)

    def _build_review_subgraph(self):
        """构建代码评审子图"""
        logger.info("构建代码评审子图")
        builder = ReviewSubgraphBuilder()
        subgraph = builder.build_review_subgraph()
        # 使用主图的 checkpointer 编译子图
        return subgraph.compile(checkpointer=self.checkpointer)

    def build_main_graph(self) -> StateGraph:
        """
        构建主图

        Returns:
            配置完成的主图
        """
        logger.info("开始构建主图")

        # 创建状态图
        self.graph = StateGraph(GlobalState)

        # 添加节点
        self._add_nodes()

        # 定义边和流程
        self._define_edges()

        # 设置入口
        self._set_entry()

        logger.info("主图构建完成")
        return self.graph

    def _add_nodes(self):
        """添加主图节点"""
        logger.debug("添加主图节点")

        # 添加 Supervisor 节点
        self.graph.add_node("supervisor_analyze_task", supervisor_analyze_task_node)
        self.graph.add_node("supervisor_routing", supervisor_routing_node)

        # 添加子图节点
        self.graph.add_node("dissection_subgraph", self._call_dissection_subgraph)
        self.graph.add_node("review_subgraph", self._call_review_subgraph)

        # 添加 Human-in-the-loop 节点
        self.graph.add_node("human_intervention", self._human_intervention_node)

        # 添加总结生成节点
        self.graph.add_node("generate_summary", self._generate_summary_node)

        # 添加错误处理节点
        self.graph.add_node("handle_error", self._handle_error_node)

    def _define_edges(self):
        """定义节点间的边和执行流程"""
        logger.debug("定义主图执行流程")

        # 任务分析 -> 路由决策
        self.graph.add_edge("supervisor_analyze_task", "supervisor_routing")

        # 路由决策 -> 条件路由
        self.graph.add_conditional_edges(
            "supervisor_routing",
            self._route_next_step,
            {
                "dissection_subgraph": "dissection_subgraph",
                "review_subgraph": "review_subgraph",
                "human_intervention": "human_intervention",
                "generate_summary": "generate_summary",
                "handle_error": "handle_error",
                "end": END
            }
        )

        # 算法拆解子图 -> 路由决策
        self.graph.add_edge("dissection_subgraph", "supervisor_routing")

        # 代码评审子图 -> 路由决策
        self.graph.add_edge("review_subgraph", "supervisor_routing")

        # Human-in-the-loop -> 路由决策
        self.graph.add_edge("human_intervention", "supervisor_routing")

        # 总结生成 -> 结束
        self.graph.add_edge("generate_summary", END)

        # 错误处理 -> 路由决策（支持重试）
        self.graph.add_edge("handle_error", "supervisor_routing")

    def _set_entry(self):
        """设置主图入口"""
        logger.debug("设置主图入口")
        self.graph.set_entry_point("supervisor_analyze_task")

    def _route_next_step(self, state: GlobalState) -> str:
        """
        路由决策函数

        根据 Supervisor 的路由决策，决定下一步执行的节点。

        Args:
            state: 全局状态

        Returns:
            下一步节点名称
        """
        # 检查是否有错误
        if state.get("last_error"):
            logger.warning(f"检测到错误: {state['last_error']}")
            return "handle_error"

        # 检查是否需要人工干预
        if state.get("human_intervention_required"):
            logger.info("需要人工干预")
            return "human_intervention"

        # 获取 Supervisor 的路由决策
        routing_decision = state.get("shared_context", {}).get("routing_decision")

        if not routing_decision:
            logger.warning("未找到路由决策，默认进入总结生成")
            return "generate_summary"

        next_step = routing_decision.get("next_step")

        # 映射 NextStep 枚举到节点名称
        step_mapping = {
            NextStep.DISSECTION_SUBGRAPH: "dissection_subgraph",
            NextStep.REVIEW_SUBGRAPH: "review_subgraph",
            NextStep.HUMAN_INTERVENTION: "human_intervention",
            NextStep.COMPLETE: "generate_summary"
        }

        # 如果 next_step 是字符串，尝试转换为枚举
        if isinstance(next_step, str):
            try:
                next_step = NextStep(next_step)
            except ValueError:
                logger.warning(f"无效的 next_step 值: {next_step}")
                return "generate_summary"

        node_name = step_mapping.get(next_step, "generate_summary")
        logger.info(f"路由到节点: {node_name}")
        return node_name

    # ========================================================================
    # 节点实现函数
    # ========================================================================

    async def _call_dissection_subgraph(self, state: GlobalState) -> GlobalState:
        """
        调用算法拆解子图

        Args:
            state: 全局状态

        Returns:
            更新后的全局状态
        """
        logger.info("调用算法拆解子图")

        if 'task_id' not in state:
            logger.error(f"状态中缺少 task_id！完整状态: {state}")
            raise KeyError("状态中缺少必需字段 task_id")

        # 生成追踪ID
        trace_id = state["task_id"]
        span_id = str(uuid.uuid4())
        start_time = time.time()

        try:
            # 更新状态
            state["current_phase"] = Phase.DISSECTION
            state["status"] = StateTaskStatus.ANALYZING
            state["updated_at"] = datetime.now(timezone.utc)

            # 记录子图调用开始
            log_graph_execution(
                graph_name="main_graph",
                node_name="dissection_subgraph",
                task_id=trace_id,
                state_snapshot={
                    "phase": state["current_phase"].value,
                    "status": state["status"].value,
                    "progress": state.get("progress", 0.0)
                },
                trace_id=trace_id,
                span_id=span_id
            )

            # 使用 StateConverter 转换状态
            dissection_state = StateConverter.global_to_dissection(state)

            # 调用子图
            result = await self.dissection_subgraph.ainvoke(dissection_state)

            # 使用 StateConverter 合并结果
            state = StateConverter.dissection_to_global(state, result)

            # 计算执行时间
            duration_ms = (time.time() - start_time) * 1000

            # 记录子图调用完成
            log_graph_execution(
                graph_name="main_graph",
                node_name="dissection_subgraph",
                task_id=trace_id,
                state_snapshot={
                    "phase": state["current_phase"].value,
                    "status": state["status"].value,
                    "progress": state.get("progress", 0.0),
                    "has_explanation": bool(state.get("algorithm_explanation"))
                },
                duration_ms=duration_ms,
                trace_id=trace_id,
                span_id=span_id
            )

            logger.info("算法拆解子图执行完成")

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"算法拆解失败: {str(e)}"

            logger.error(error_msg)
            state["last_error"] = error_msg
            state["retry_count"] = state.get("retry_count", 0) + 1

            # 记录错误
            log_graph_execution(
                graph_name="main_graph",
                node_name="dissection_subgraph",
                task_id=trace_id,
                duration_ms=duration_ms,
                error=error_msg,
                trace_id=trace_id,
                span_id=span_id
            )

        return state

    async def _call_review_subgraph(self, state: GlobalState) -> GlobalState:
        """
        调用代码评审子图

        Args:
            state: 全局状态

        Returns:
            更新后的全局状态
        """
        logger.info("调用代码评审子图")

        # 生成追踪ID
        trace_id = state.get("task_id", str(uuid.uuid4()))
        span_id = str(uuid.uuid4())
        start_time = time.time()

        try:
            # 更新状态
            state["current_phase"] = Phase.REVIEW
            state["status"] = StateTaskStatus.OPTIMIZING
            state["updated_at"] = datetime.now(timezone.utc)

            # 记录子图调用开始
            log_graph_execution(
                graph_name="main_graph",
                node_name="review_subgraph",
                task_id=trace_id,
                state_snapshot={
                    "phase": state["current_phase"].value,
                    "status": state["status"].value,
                    "progress": state.get("progress", 0.0)
                },
                trace_id=trace_id,
                span_id=span_id
            )

            # 使用 StateConverter 转换状态
            review_state = StateConverter.global_to_review(state)

            # 调用子图
            result = await self.review_subgraph.ainvoke(review_state)

            # 使用 StateConverter 合并结果
            state = StateConverter.review_to_global(state, result)

            # 计算执行时间
            duration_ms = (time.time() - start_time) * 1000

            # 记录子图调用完成
            log_graph_execution(
                graph_name="main_graph",
                node_name="review_subgraph",
                task_id=trace_id,
                state_snapshot={
                    "phase": state["current_phase"].value,
                    "status": state["status"].value,
                    "progress": state.get("progress", 0.0),
                    "has_issues": bool(state.get("detected_issues")),
                    "has_suggestions": bool(state.get("optimization_suggestions"))
                },
                duration_ms=duration_ms,
                trace_id=trace_id,
                span_id=span_id
            )

            logger.info("代码评审子图执行完成")

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"代码评审失败: {str(e)}"

            logger.error(error_msg)
            state["last_error"] = error_msg
            state["retry_count"] = state.get("retry_count", 0) + 1

            # 记录错误
            log_graph_execution(
                graph_name="main_graph",
                node_name="review_subgraph",
                task_id=trace_id,
                duration_ms=duration_ms,
                error=error_msg,
                trace_id=trace_id,
                span_id=span_id
            )

        return state

    async def _human_intervention_node(self, state: GlobalState) -> GlobalState:
        """
        Human-in-the-loop 节点

        处理人工干预请求，暂停执行等待用户决策。

        Args:
            state: 全局状态

        Returns:
            更新后的全局状态
        """
        logger.info("进入 Human-in-the-loop 节点")

        try:
            # 更新状态
            state["status"] = StateTaskStatus.WAITING_HUMAN
            state["updated_at"] = datetime.now(timezone.utc)

            # 获取待决策的内容
            pending_decision = state.get("pending_human_decision", {})

            if not pending_decision:
                logger.warning("未找到待决策内容，生成默认干预请求")
                pending_decision = {
                    "intervention_type": "confirmation",
                    "title": "确认继续执行",
                    "description": "是否继续执行任务？",
                    "options": [
                        {"id": "continue", "label": "继续", "description": "继续执行任务"},
                        {"id": "cancel", "label": "取消", "description": "取消任务"}
                    ],
                    "default_option": "continue"
                }
                state["pending_human_decision"] = pending_decision

            # 使用 LangGraph 的 interrupt 机制暂停执行
            # 用户决策将通过 resume 传入
            logger.info(f"暂停执行，等待用户决策: {pending_decision.get('title')}")
            user_decision = interrupt(pending_decision)

            # 处理用户决策
            if user_decision:
                logger.info(f"收到用户决策: {user_decision}")

                # 记录决策历史
                decision_record = HumanDecision(
                    decision_id=f"decision_{len(state.get('decision_history', []))}",
                    decision_type=pending_decision.get("intervention_type", "unknown"),
                    accepted_suggestions=user_decision.get("accepted_suggestions", []),
                    rejected_suggestions=user_decision.get("rejected_suggestions", []),
                    custom_input=user_decision.get("custom_input")
                )
                state["decision_history"].append(decision_record)

                # 清除待决策标记
                state["human_intervention_required"] = False
                state["pending_human_decision"] = {}

                # 根据用户决策更新状态
                if user_decision.get("action") == "cancel":
                    state["status"] = StateTaskStatus.CANCELED
                    logger.info("用户取消任务")
                else:
                    state["status"] = StateTaskStatus.ANALYZING
                    logger.info("用户确认继续执行")

        except Exception as e:
            logger.error(f"Human-in-the-loop 节点执行失败: {str(e)}")
            state["last_error"] = f"人工干预处理失败: {str(e)}"

        return state

    async def _generate_summary_node(self, state: GlobalState) -> GlobalState:
        """
        生成任务执行总结

        Args:
            state: 全局状态

        Returns:
            更新后的全局状态
        """
        logger.info("生成任务执行总结")

        # 生成追踪ID
        trace_id = state.get("task_id", str(uuid.uuid4()))
        span_id = str(uuid.uuid4())
        start_time = time.time()

        try:
            from app.core.llm import get_llm_instance
            from app.graph.supervisor.agent import SupervisorAgent

            # 更新状态
            state["current_phase"] = Phase.REPORT_GENERATION
            state["status"] = StateTaskStatus.COMPLETED
            state["progress"] = 1.0
            state["updated_at"] = datetime.now(timezone.utc)

            # 记录节点执行开始
            log_agent_execution(
                agent_name="supervisor",
                agent_type="supervisor",
                phase="summary_generation",
                task_id=trace_id,
                inputs={"state_keys": list(state.keys())},
                trace_id=trace_id,
                span_id=span_id
            )

            # 创建 Supervisor 实例生成总结
            llm = get_llm_instance()
            supervisor = SupervisorAgent(llm)
            summary = await supervisor.generate_summary(state)

            # 保存总结到共享上下文
            state["shared_context"]["final_summary"] = summary

            # 计算执行时间
            duration_ms = (time.time() - start_time) * 1000

            # 记录节点执行完成
            log_agent_execution(
                agent_name="supervisor",
                agent_type="supervisor",
                phase="summary_generation",
                task_id=trace_id,
                outputs={"summary_length": len(summary) if summary else 0},
                duration_ms=duration_ms,
                trace_id=trace_id,
                span_id=span_id
            )

            logger.info("任务执行总结生成完成")

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"总结生成失败: {str(e)}"

            logger.error(error_msg)
            state["last_error"] = error_msg
            state["status"] = StateTaskStatus.FAILED

            # 记录错误
            log_agent_execution(
                agent_name="supervisor",
                agent_type="supervisor",
                phase="summary_generation",
                task_id=trace_id,
                duration_ms=duration_ms,
                error=error_msg,
                trace_id=trace_id,
                span_id=span_id
            )

        return state

    async def _handle_error_node(self, state: GlobalState) -> GlobalState:
        """
        错误处理节点

        分析错误并制定恢复策略。

        Args:
            state: 全局状态

        Returns:
            更新后的全局状态
        """
        logger.info("进入错误处理节点")

        try:
            from app.core.llm import get_llm_instance
            from app.graph.supervisor.agent import SupervisorAgent

            last_error = state.get("last_error", "未知错误")
            retry_count = state.get("retry_count", 0)

            # 构造错误上下文
            error_context = {
                "error_message": last_error,
                "current_phase": state.get("current_phase"),
                "retry_count": retry_count,
                "task_id": state.get("task_id")
            }

            # 创建 Supervisor 实例处理错误
            llm = get_llm_instance()
            supervisor = SupervisorAgent(llm)
            error = Exception(last_error)
            error_plan = await supervisor.handle_error(error, error_context, retry_count)

            logger.info(f"错误处理方案: {error_plan.recovery_strategy}")

            # 根据恢复策略更新状态
            from app.graph.supervisor.agent import RecoveryStrategy

            if error_plan.recovery_strategy == RecoveryStrategy.RETRY:
                # 重试：清除错误标记，允许重新执行
                if retry_count < error_plan.max_retries:
                    logger.info(f"重试执行 (第 {retry_count + 1} 次)")
                    state["last_error"] = None
                    state["retry_count"] = retry_count + 1
                else:
                    logger.warning("已达到最大重试次数，中止任务")
                    state["status"] = StateTaskStatus.FAILED
                    state["shared_context"]["error_plan"] = asdict(error_plan)

            elif error_plan.recovery_strategy == RecoveryStrategy.DEGRADE:
                # 降级：标记降级模式，继续执行
                logger.info("启用降级模式")
                state["last_error"] = None
                state["shared_context"]["degraded_mode"] = True
                state["shared_context"]["error_plan"] = asdict(error_plan)

            elif error_plan.recovery_strategy == RecoveryStrategy.SKIP:
                # 跳过：清除错误，跳过当前步骤
                logger.info("跳过当前步骤")
                state["last_error"] = None
                state["shared_context"]["skipped_steps"] = state["shared_context"].get("skipped_steps", [])
                state["shared_context"]["skipped_steps"].append(state.get("current_phase"))

            elif error_plan.recovery_strategy == RecoveryStrategy.HUMAN:
                # 人工介入：设置人工干预标记
                logger.info("请求人工介入")
                state["human_intervention_required"] = True
                state["pending_human_decision"] = {
                    "intervention_type": "error_resolution",
                    "title": "错误处理",
                    "description": error_plan.user_message,
                    "options": [
                        {"id": "retry", "label": "重试", "description": "重新执行失败的步骤"},
                        {"id": "skip", "label": "跳过", "description": "跳过当前步骤继续执行"},
                        {"id": "abort", "label": "中止", "description": "中止任务执行"}
                    ],
                    "default_option": "retry"
                }

            else:  # ABORT
                # 中止：标记任务失败
                logger.warning("中止任务执行")
                state["status"] = StateTaskStatus.FAILED
                state["shared_context"]["error_plan"] = asdict(error_plan)

        except Exception as e:
            logger.error(f"错误处理节点执行失败: {str(e)}")
            state["status"] = StateTaskStatus.FAILED
            state["last_error"] = f"错误处理失败: {str(e)}"

        return state

    def compile(self) -> Any:
        """
        编译主图

        Returns:
            编译后的可执行图
        """
        if not self.graph:
            self.build_main_graph()

        logger.info("编译主图")
        self.compiled_graph = self.graph.compile(checkpointer=self.checkpointer)
        logger.info("主图编译完成")

        return self.compiled_graph


# ============================================================================
# LangGraph Studio 工厂函数
# ============================================================================

def _normalize_studio_input(raw_input: Dict[str, Any]) -> GlobalState:
    """
    将 LangGraph Studio 的输入标准化为完整的 GlobalState

    Studio 输入通常是简化的 API 请求体格式（如 {code, language, optimization_level}），
    需要转换为完整的 GlobalState 以避免节点访问缺失字段时出现 KeyError。

    Args:
        raw_input: Studio UI 输入（可能是简化格式或完整 GlobalState）

    Returns:
        完整的 GlobalState

    处理三种输入场景：
    1. 完整 GlobalState（已包含所有必需字段）→ 直接返回
    2. API 请求体格式（{code, language, optimization_level}）→ 转换为 GlobalState
    3. 部分 GlobalState（缺少某些必需字段）→ 补全缺失字段
    """
    from app.graph.state import StateFactory

    # 场景 1：检查是否已经是完整的 GlobalState
    # 通过检查关键必需字段来判断
    required_global_fields = {
        'task_id', 'user_id', 'original_code', 'language', 'status',
        'current_phase', 'progress', 'shared_context', 'code_versions',
        'decision_history', 'created_at', 'updated_at'
    }

    if required_global_fields.issubset(raw_input.keys()):
        logger.info("Studio 输入已是完整 GlobalState，直接使用")
        return raw_input

    # 场景 2 & 3：需要转换或补全
    logger.info("Studio 输入为简化格式，转换为完整 GlobalState")

    # 提取输入字段（兼容不同命名）
    code = raw_input.get('code') or raw_input.get('original_code', '')
    language = raw_input.get('language', 'python')
    optimization_level = raw_input.get('optimization_level', 'balanced')
    task_id = raw_input.get('task_id', f"studio_task_{uuid.uuid4().hex[:8]}")
    user_id = raw_input.get('user_id', 'studio_user')

    # 使用 StateFactory 创建完整状态
    global_state = StateFactory.create_global_state(
        task_id=task_id,
        user_id=user_id,
        code=code,
        language=language,
        optimization_level=optimization_level
    )

    # 保留原始输入中的其他字段（如果有）
    for key, value in raw_input.items():
        if key not in global_state and key not in ['code']:  # 'code' 已映射到 'original_code'
            global_state[key] = value

    logger.info(f"状态转换完成: task_id={task_id}, language={language}")
    return global_state


def _create_studio_wrapper_graph(main_graph, checkpointer=None):
    """
    创建 Studio 包装图，在入口处进行状态标准化

    包装图结构：
    normalize_input (入口) → main_graph_execution → END

    Args:
        main_graph: 编译后的主图
        checkpointer: 状态持久化器

    Returns:
        包装后的图
    """
    from langgraph.graph import StateGraph, END

    async def normalize_input_node(state: Dict[str, Any]) -> GlobalState:
        """标准化输入节点"""
        logger.info("Studio 包装图：标准化输入状态")
        normalized_state = _normalize_studio_input(state)
        return normalized_state

    async def main_graph_execution_node(state: GlobalState) -> GlobalState:
        """执行主图节点"""
        logger.info("Studio 包装图：执行主图")
        # 直接调用主图（已编译）
        result = await main_graph.ainvoke(state)
        return result

    # 创建包装图
    wrapper_graph = StateGraph(GlobalState)
    wrapper_graph.add_node("normalize_input", normalize_input_node)
    wrapper_graph.add_node("main_graph_execution", main_graph_execution_node)

    wrapper_graph.set_entry_point("normalize_input")
    wrapper_graph.add_edge("normalize_input", "main_graph_execution")
    wrapper_graph.add_edge("main_graph_execution", END)

    return wrapper_graph.compile(checkpointer=checkpointer)


def create_main_graph_for_studio(checkpointer=None):
    """
    创建主图的工厂函数（用于 LangGraph Studio）

    LangGraph Studio 在独立进程中运行，会调用此函数创建图实例。
    此函数使用与应用相同的配置逻辑（通过 create_checkpointer），
    确保行为一致。

    **状态初始化适配**：
    为了解决 Studio 输入格式与 GlobalState Schema 不匹配的问题，
    此函数返回一个包装图，在入口处自动将 Studio 输入（简化的 API 请求体格式）
    转换为完整的 GlobalState，避免节点访问缺失字段时出现 KeyError。

    Args:
        checkpointer: 状态持久化器
            - 如果为 None：使用 create_checkpointer() 创建
            - 如果为 dict：LangGraph Studio 传入的配置，忽略并使用 create_checkpointer()
            - 如果为 BaseCheckpointSaver：直接使用

    Returns:
        编译后的包装图（包含状态标准化逻辑）

    Note:
        - 环境变量从 .env.dev 读取（与应用相同）
        - LLM 实例通过 get_llm_instance() 获取（使用相同配置）
        - Checkpointer 通过 create_checkpointer() 创建（使用相同配置）
        - LangGraph Studio 传入的 checkpointer 是 dict 配置对象，需要忽略

    Studio 输入格式支持：
        1. 简化格式（API 请求体）：
           {code: "...", language: "python", optimization_level: "balanced"}
        2. 完整 GlobalState：
           {task_id: "...", user_id: "...", original_code: "...", ...}
        3. 部分 GlobalState（自动补全缺失字段）
    """
    # LangGraph Studio 传入的是 dict 配置，我们需要忽略它
    # 使用我们自己的 checkpointer 创建逻辑
    if checkpointer is None or isinstance(checkpointer, dict):
        checkpointer = None  # 让 MainGraphBuilder 使用默认的 create_checkpointer()

    # 构建主图
    builder = MainGraphBuilder(checkpointer=checkpointer)
    main_graph = builder.compile()

    # 创建包装图（添加状态标准化层）
    logger.info("为 LangGraph Studio 创建包装图（包含状态标准化）")
    wrapper_graph = _create_studio_wrapper_graph(main_graph, checkpointer=checkpointer)

    return wrapper_graph


# ============================================================================
# 主图管理器
# ============================================================================

class MainGraphManager:
    """
    主图管理器

    提供主图的高级管理功能，包括任务执行、状态查询和恢复。
    """

    def __init__(self, checkpointer=None):
        """
        初始化主图管理器

        Args:
            checkpointer: 状态持久化器

        Note:
            LLM 实例由各个节点通过 get_llm_instance() 获取，无需在构建时传入
        """
        self.builder = MainGraphBuilder(checkpointer=checkpointer)
        self.graph = self.builder.compile()

    async def execute_task(self, initial_state: GlobalState, config: Dict[str, Any] = None) -> GlobalState:
        """
        执行任务

        Args:
            initial_state: 初始状态
            config: 执行配置（包含 thread_id 等）

        Returns:
            最终状态
        """
        logger.info(f"开始执行任务: {initial_state.get('task_id')}")

        try:
            # 执行图
            result = await self.graph.ainvoke(initial_state, config=config)
            logger.info(f"任务执行完成: {initial_state.get('task_id')}")
            return result

        except Exception as e:
            logger.error(f"任务执行失败: {str(e)}")
            raise

    async def stream_task(self, initial_state: GlobalState, config: Dict[str, Any] = None):
        """
        流式执行任务

        Args:
            initial_state: 初始状态
            config: 执行配置

        Yields:
            状态更新事件
        """
        logger.info(f"开始流式执行任务: {initial_state.get('task_id')}")

        try:
            async for event in self.graph.astream(initial_state, config=config):
                yield event

        except Exception as e:
            logger.error(f"流式执行失败: {str(e)}")
            raise

    async def get_state(self, config: Dict[str, Any]) -> GlobalState | None:
        """
        获取任务状态

        Args:
            config: 配置（包含 thread_id）

        Returns:
            当前状态
        """
        state = await self.graph.aget_state(config)
        return state.values if state else None

    async def resume_task(self, config: Dict[str, Any], user_input: Any = None) -> GlobalState:
        """
        恢复暂停的任务

        Args:
            config: 配置（包含 thread_id）
            user_input: 用户输入（用于 Human-in-the-loop）

        Returns:
            最终状态
        """
        logger.info("恢复任务执行")

        try:
            # 恢复执行
            result = await self.graph.ainvoke(user_input, config=config)
            logger.info("任务恢复执行完成")
            return result

        except Exception as e:
            logger.error(f"任务恢复失败: {str(e)}")
            raise
