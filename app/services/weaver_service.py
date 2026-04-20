"""
Weaver Service 业务逻辑层

负责解析 API 请求，调用 LangGraph 编译后的 graph.invoke/astream 方法，
处理流式输出和状态管理。
"""

from typing import Dict, Any, AsyncGenerator, Optional
from datetime import datetime
import uuid

from app.graph.main_graph import MainGraphManager
from app.graph.state import GlobalState, TaskStatus, Phase
from app.schemas.requests import TaskRequest, OptimizationLevel
from app.schemas.responses import (
    TaskCreationResponse,
    TaskStatusResponse,
    AnalysisResultResponse,
    AlgorithmExplanation,
    ExecutionStep,
    CodeIssue,
    Suggestion,
    ValidationResult,
    PerformanceMetrics,
    ImpactAssessment,
    IssueType,
    Severity,
    ImprovementType
)
from app.core.logger import get_logger
from app.core.config import Settings

logger = get_logger(__name__)


class WeaverService:
    """
    Weaver Service 业务逻辑服务

    提供代码分析、优化和教学报告生成的核心业务逻辑。
    """

    def __init__(self, graph_manager: MainGraphManager, settings: Settings):
        """
        初始化 Weaver Service

        Args:
            graph_manager: 主图管理器实例
            settings: 应用配置
        """
        self.graph_manager = graph_manager
        self.settings = settings

    async def create_task(self, request: TaskRequest) -> TaskCreationResponse:
        """
        创建代码分析任务

        Args:
            request: 任务请求

        Returns:
            TaskCreationResponse: 任务创建响应
        """
        # 生成任务ID
        task_id = str(uuid.uuid4())

        logger.info(f"创建任务: {task_id}")

        # 预估执行时间（基于优化级别）
        estimated_duration = self._estimate_duration(request.optimization_level)

        # 构建 WebSocket URL
        websocket_url = f"ws://{self.settings.host}:{self.settings.port}/ws/chat/{task_id}"

        return TaskCreationResponse(
            success=True,
            message="任务创建成功",
            task_id=task_id,
            status=TaskStatus.CREATED,
            estimated_duration_seconds=estimated_duration,
            websocket_url=websocket_url
        )

    async def execute_task(self, task_id: str, initial_state: GlobalState) -> GlobalState:
        """
        执行代码分析任务

        Args:
            task_id: 任务ID
            initial_state: 初始状态

        Returns:
            GlobalState: 最终状态
        """
        logger.info(f"执行任务: {task_id}")

        # 构建任务配置
        config = {"configurable": {"thread_id": task_id}}

        try:
            # 执行任务
            final_state = await self.graph_manager.execute_task(initial_state, config)
            logger.info(f"任务执行完成: {task_id}")
            return final_state

        except Exception as e:
            logger.error(f"任务执行失败: {task_id}, 错误: {str(e)}")
            raise

    async def stream_task(
        self,
        task_id: str,
        initial_state: GlobalState
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式执行代码分析任务

        Args:
            task_id: 任务ID
            initial_state: 初始状态

        Yields:
            Dict[str, Any]: 状态更新事件
        """
        logger.info(f"流式执行任务: {task_id}")

        # 构建任务配置
        config = {"configurable": {"thread_id": task_id}}

        try:
            async for event in self.graph_manager.stream_task(initial_state, config):
                # 转换事件格式
                formatted_event = self._format_stream_event(event)
                yield formatted_event

            logger.info(f"任务流式执行完成: {task_id}")

        except Exception as e:
            logger.error(f"任务流式执行失败: {task_id}, 错误: {str(e)}")
            # 发送错误事件
            yield {
                "type": "error",
                "data": {
                    "error_message": str(e),
                    "task_id": task_id
                }
            }

    async def get_task_status(self, task_id: str) -> TaskStatusResponse:
        """
        获取任务状态

        Args:
            task_id: 任务ID

        Returns:
            TaskStatusResponse: 任务状态响应
        """
        logger.info(f"查询任务状态: {task_id}")

        # 构建任务配置
        config = {"configurable": {"thread_id": task_id}}

        try:
            # 获取状态
            state = await self.graph_manager.get_state(config)

            if not state:
                logger.warning(f"任务不存在: {task_id}")
                return TaskStatusResponse(
                    success=False,
                    message="任务不存在",
                    task_id=task_id,
                    status=TaskStatus.FAILED,
                    progress_percent=0,
                    current_phase="unknown",
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )

            # 构建响应
            return TaskStatusResponse(
                success=True,
                message="查询成功",
                task_id=task_id,
                status=state.get("status", TaskStatus.PENDING),
                progress_percent=int(state.get("progress", 0) * 100),
                current_phase=state.get("current_phase", Phase.INITIALIZATION).value,
                created_at=state.get("created_at", datetime.utcnow()),
                updated_at=state.get("updated_at", datetime.utcnow()),
                result=state.get("shared_context", {}).get("final_summary"),
                logs=state.get("execution_logs", [])
            )

        except Exception as e:
            logger.error(f"查询任务状态失败: {task_id}, 错误: {str(e)}")
            raise

    async def get_analysis_result(self, task_id: str) -> AnalysisResultResponse:
        """
        获取分析结果

        Args:
            task_id: 任务ID

        Returns:
            AnalysisResultResponse: 分析结果响应
        """
        logger.info(f"获取分析结果: {task_id}")

        # 构建任务配置
        config = {"configurable": {"thread_id": task_id}}

        try:
            # 获取状态
            state = await self.graph_manager.get_state(config)

            if not state:
                raise ValueError(f"任务不存在: {task_id}")

            # 提取结果数据
            original_code = state.get("original_code", "")
            optimized_code = state.get("optimized_code")

            # 构建算法讲解
            explanation = self._build_explanation(state)

            # 构建问题列表
            issues = self._build_issues(state)

            # 构建建议列表
            suggestions = self._build_suggestions(state)

            # 构建验证结果
            validation_result = self._build_validation_result(state)

            # 构建性能指标
            performance_metrics = self._build_performance_metrics(state)

            return AnalysisResultResponse(
                success=True,
                message="分析完成",
                task_id=task_id,
                original_code=original_code,
                optimized_code=optimized_code,
                explanation=explanation,
                issues=issues,
                suggestions=suggestions,
                validation_result=validation_result,
                performance_metrics=performance_metrics,
                optimization_history=state.get("optimization_history", [])
            )

        except Exception as e:
            logger.error(f"获取分析结果失败: {task_id}, 错误: {str(e)}")
            raise

    async def resume_task(self, task_id: str, user_input: Any) -> GlobalState:
        """
        恢复暂停的任务

        Args:
            task_id: 任务ID
            user_input: 用户输入

        Returns:
            GlobalState: 最终状态
        """
        logger.info(f"恢复任务: {task_id}")

        # 构建任务配置
        config = {"configurable": {"thread_id": task_id}}

        try:
            # 恢复任务
            final_state = await self.graph_manager.resume_task(config, user_input)
            logger.info(f"任务恢复完成: {task_id}")
            return final_state

        except Exception as e:
            logger.error(f"任务恢复失败: {task_id}, 错误: {str(e)}")
            raise

    # ========================================================================
    # 辅助方法
    # ========================================================================

    def _estimate_duration(self, optimization_level: OptimizationLevel) -> int:
        """
        预估任务执行时间

        Args:
            optimization_level: 优化级别

        Returns:
            int: 预估时间（秒）
        """
        duration_map = {
            OptimizationLevel.BASIC: 30,
            OptimizationLevel.BALANCED: 60,
            OptimizationLevel.AGGRESSIVE: 120,
            OptimizationLevel.PRODUCTION: 180
        }
        return duration_map.get(optimization_level, 60)

    def _format_stream_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化流式事件

        Args:
            event: 原始事件

        Returns:
            Dict[str, Any]: 格式化后的事件
        """
        # 提取节点名称和状态
        node_name = list(event.keys())[0] if event else "unknown"
        state = event.get(node_name, {})

        return {
            "type": "status_update",
            "data": {
                "node": node_name,
                "status": state.get("status"),
                "phase": state.get("current_phase"),
                "progress": state.get("progress", 0),
                "message": self._get_phase_message(state.get("current_phase"))
            }
        }

    def _get_phase_message(self, phase: Optional[Phase]) -> str:
        """
        获取阶段消息

        Args:
            phase: 当前阶段

        Returns:
            str: 阶段消息
        """
        if not phase:
            return "初始化中..."

        phase_messages = {
            Phase.INITIALIZATION: "初始化任务...",
            Phase.DISSECTION: "分析算法执行步骤...",
            Phase.REVIEW: "检测代码问题并生成优化建议...",
            Phase.HUMAN_INTERVENTION: "等待用户确认...",
            Phase.REPORT_GENERATION: "生成教学报告..."
        }
        return phase_messages.get(phase, "处理中...")

    def _build_explanation(self, state: GlobalState) -> AlgorithmExplanation:
        """
        构建算法讲解

        Args:
            state: 全局状态

        Returns:
            AlgorithmExplanation: 算法讲解
        """
        dissection_result = state.get("dissection_result", {})

        # 提取步骤
        steps_data = dissection_result.get("steps", [])
        steps = [
            ExecutionStep(
                step_number=i + 1,
                description=step.get("description", ""),
                code_snippet=step.get("code_snippet"),
                variables_state=step.get("variables_state"),
                time_complexity=step.get("time_complexity"),
                space_complexity=step.get("space_complexity")
            )
            for i, step in enumerate(steps_data)
        ]

        return AlgorithmExplanation(
            algorithm_name=dissection_result.get("algorithm_name", "未知算法"),
            steps=steps,
            pseudocode=dissection_result.get("pseudocode", ""),
            time_complexity=dissection_result.get("time_complexity", "O(n)"),
            space_complexity=dissection_result.get("space_complexity", "O(1)"),
            visualization=dissection_result.get("visualization"),
            key_insights=dissection_result.get("key_insights", [])
        )

    def _build_issues(self, state: GlobalState) -> list[CodeIssue]:
        """
        构建问题列表

        Args:
            state: 全局状态

        Returns:
            list[CodeIssue]: 问题列表
        """
        review_result = state.get("review_result", {})
        issues_data = review_result.get("issues", [])

        issues = []
        for issue_data in issues_data:
            issue = CodeIssue(
                issue_id=issue_data.get("issue_id", str(uuid.uuid4())),
                type=IssueType(issue_data.get("type", "logic_error")),
                severity=Severity(issue_data.get("severity", "medium")),
                line_number=issue_data.get("line_number", 0),
                column_number=issue_data.get("column_number"),
                description=issue_data.get("description", ""),
                suggestion=issue_data.get("suggestion", ""),
                example_fix=issue_data.get("example_fix"),
                impact_assessment=issue_data.get("impact_assessment")
            )
            issues.append(issue)

        return issues

    def _build_suggestions(self, state: GlobalState) -> list[Suggestion]:
        """
        构建建议列表

        Args:
            state: 全局状态

        Returns:
            list[Suggestion]: 建议列表
        """
        review_result = state.get("review_result", {})
        suggestions_data = review_result.get("suggestions", [])

        suggestions = []
        for sugg_data in suggestions_data:
            # 构建影响评估
            impact_data = sugg_data.get("impact_assessment", {})
            impact = ImpactAssessment(
                performance_impact=impact_data.get("performance_impact", "无影响"),
                readability_impact=impact_data.get("readability_impact", "无影响"),
                maintainability_impact=impact_data.get("maintainability_impact", "无影响"),
                risk_level=Severity(impact_data.get("risk_level", "low"))
            )

            suggestion = Suggestion(
                suggestion_id=sugg_data.get("suggestion_id", str(uuid.uuid4())),
                issue_id=sugg_data.get("issue_id", ""),
                improvement_type=ImprovementType(sugg_data.get("improvement_type", "code_refactoring")),
                title=sugg_data.get("title", ""),
                description=sugg_data.get("description", ""),
                original_code=sugg_data.get("original_code", ""),
                improved_code=sugg_data.get("improved_code", ""),
                explanation=sugg_data.get("explanation", ""),
                impact_assessment=impact,
                confidence_score=sugg_data.get("confidence_score", 0.5)
            )
            suggestions.append(suggestion)

        return suggestions

    def _build_validation_result(self, state: GlobalState) -> Optional[ValidationResult]:
        """
        构建验证结果

        Args:
            state: 全局状态

        Returns:
            Optional[ValidationResult]: 验证结果
        """
        review_result = state.get("review_result", {})
        validation_data = review_result.get("validation_result")

        if not validation_data:
            return None

        # 构建性能对比
        perf_comparison = {}
        if validation_data.get("performance_comparison"):
            for key, perf_data in validation_data["performance_comparison"].items():
                perf_comparison[key] = PerformanceMetrics(
                    execution_time_ms=perf_data.get("execution_time_ms", 0),
                    memory_usage_mb=perf_data.get("memory_usage_mb", 0),
                    cpu_usage_percent=perf_data.get("cpu_usage_percent"),
                    iterations_count=perf_data.get("iterations_count", 1),
                    average_time_ms=perf_data.get("average_time_ms", 0),
                    min_time_ms=perf_data.get("min_time_ms", 0),
                    max_time_ms=perf_data.get("max_time_ms", 0),
                    std_deviation_ms=perf_data.get("std_deviation_ms", 0)
                )

        return ValidationResult(
            is_valid=validation_data.get("is_valid", False),
            test_results=validation_data.get("test_results", []),
            performance_comparison=perf_comparison if perf_comparison else None,
            error_messages=validation_data.get("error_messages", []),
            warnings=validation_data.get("warnings", [])
        )

    def _build_performance_metrics(self, state: GlobalState) -> Optional[PerformanceMetrics]:
        """
        构建性能指标

        Args:
            state: 全局状态

        Returns:
            Optional[PerformanceMetrics]: 性能指标
        """
        perf_data = state.get("performance_metrics")

        if not perf_data:
            return None

        return PerformanceMetrics(
            execution_time_ms=perf_data.get("execution_time_ms", 0),
            memory_usage_mb=perf_data.get("memory_usage_mb", 0),
            cpu_usage_percent=perf_data.get("cpu_usage_percent"),
            iterations_count=perf_data.get("iterations_count", 1),
            average_time_ms=perf_data.get("average_time_ms", 0),
            min_time_ms=perf_data.get("min_time_ms", 0),
            max_time_ms=perf_data.get("max_time_ms", 0),
            std_deviation_ms=perf_data.get("std_deviation_ms", 0)
        )
