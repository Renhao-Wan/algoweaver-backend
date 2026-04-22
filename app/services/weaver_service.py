"""
Weaver Service 业务逻辑层

负责解析 API 请求，调用 LangGraph 编译后的 graph.invoke/astream 方法，
处理流式输出和状态管理。
"""

from typing import Dict, Any, AsyncGenerator, Optional
from datetime import datetime, timezone
import uuid

from app.graph.main_graph import MainGraphManager
from app.graph.state import GlobalState, Phase, IssueType
from app.schemas.requests import TaskRequest, OptimizationLevel, ReportGenerationRequest
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
    ReportResponse,
    Severity,
    ImprovementType,
    ResponseTaskStatus
)
from app.core.logger import get_logger
from app.core.config import Settings
from app.utils.report_generator import ReportGenerator, ReportFormat, ReportTemplate

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
        self.report_generator = ReportGenerator()

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
            status=ResponseTaskStatus.CREATED,
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
                    status=ResponseTaskStatus.FAILED,
                    progress_percent=0,
                    current_phase="unknown",
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )

            # 构建响应
            # 将状态从 StateTaskStatus 转换为 ResponseTaskStatus
            state_status = state["status"]  # 必需字段，直接访问
            # 映射状态值
            response_status = ResponseTaskStatus(state_status.value) if hasattr(state_status, 'value') else ResponseTaskStatus.PENDING

            # 构建 result 字典
            final_summary = state["shared_context"].get("final_summary")
            result_dict = None
            if final_summary:
                result_dict = {
                    "summary": final_summary,
                    "completed": True
                }

            return TaskStatusResponse(
                success=True,
                message="查询成功",
                task_id=task_id,
                status=response_status,
                progress_percent=int(state["progress"] * 100),  # 必需字段
                current_phase=state["current_phase"].value,  # 必需字段
                created_at=state["created_at"],  # 必需字段
                updated_at=state["updated_at"],  # 必需字段
                result=result_dict,
                logs=None  # execution_logs 字段不存在于 GlobalState
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
            original_code = state["original_code"]  # 必需字段
            # 使用最新的代码版本作为优化后代码
            code_versions = state["code_versions"]  # 必需字段
            optimized_code = code_versions[-1] if len(code_versions) > 1 else None

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
                optimization_history=state["shared_context"].get("optimization_history", [])  # shared_context 必需，内容可选
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
                "status": state.get("status"),  # 可能不存在于事件状态中
                "phase": state.get("current_phase"),  # 可能不存在于事件状态中
                "progress": state.get("progress", 0),  # 可能不存在于事件状态中
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
            Phase.ANALYSIS: "分析任务...",
            Phase.DISSECTION: "分析算法执行步骤...",
            Phase.REVIEW: "检测代码问题并生成优化建议...",
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
        # 从 algorithm_explanation（可选字段）或 shared_context 获取算法分析结果
        algorithm_explanation = state.get("algorithm_explanation")  # NotRequired 字段，使用 get

        if algorithm_explanation:
            # 如果有 algorithm_explanation，直接使用
            steps = [
                ExecutionStep(
                    step_number=step.step_number,
                    description=step.description,
                    code_snippet=step.code_snippet,
                    variables_state=step.variables_state,
                    time_complexity=step.time_complexity,
                    space_complexity=step.space_complexity
                )
                for step in algorithm_explanation.steps
            ]

            return AlgorithmExplanation(
                algorithm_name=state["shared_context"].get("dissection_result", {}).get("algorithm_type") or "未知算法",
                steps=steps,
                pseudocode=algorithm_explanation.pseudocode,
                time_complexity=algorithm_explanation.time_complexity,
                space_complexity=algorithm_explanation.space_complexity,
                visualization=algorithm_explanation.visualization,
                key_insights=algorithm_explanation.key_insights
            )
        else:
            # 兜底：返回空的算法讲解
            return AlgorithmExplanation(
                algorithm_name="未知算法",
                steps=[],
                pseudocode="",
                time_complexity="O(n)",
                space_complexity="O(1)",
                visualization=None,
                key_insights=[]
            )

    def _build_issues(self, state: GlobalState) -> list[CodeIssue]:
        """
        构建问题列表

        Args:
            state: 全局状态

        Returns:
            list[CodeIssue]: 问题列表
        """
        # 直接从 detected_issues（可选字段）获取问题列表
        detected_issues = state.get("detected_issues", [])  # NotRequired 字段，使用 get

        issues = []
        for issue_data in detected_issues:
            # 处理 Pydantic 模型或字典
            if hasattr(issue_data, 'issue_id'):
                # 已经是 Pydantic 模型
                issue = CodeIssue(
                    issue_id=issue_data.issue_id,
                    type=issue_data.type,
                    severity=issue_data.severity,
                    line_number=issue_data.line_number,
                    column_number=getattr(issue_data, 'column_number', None),
                    description=issue_data.description,
                    suggestion=issue_data.suggestion,
                    example_fix=issue_data.example_fix,
                    impact_assessment=getattr(issue_data, 'impact_assessment', None)
                )
            else:
                # 字典格式
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

    def _map_improvement_type(self, type_str: str) -> ImprovementType:
        """
        映射改进类型字符串到枚举

        Args:
            type_str: 类型字符串

        Returns:
            ImprovementType: 改进类型枚举
        """
        # 映射表
        type_mapping = {
            "readability": ImprovementType.READABILITY_IMPROVEMENT,
            "readability_improvement": ImprovementType.READABILITY_IMPROVEMENT,
            "performance": ImprovementType.PERFORMANCE_TUNING,
            "performance_tuning": ImprovementType.PERFORMANCE_TUNING,
            "algorithm": ImprovementType.ALGORITHM_OPTIMIZATION,
            "algorithm_optimization": ImprovementType.ALGORITHM_OPTIMIZATION,
            "refactoring": ImprovementType.CODE_REFACTORING,
            "code_refactoring": ImprovementType.CODE_REFACTORING,
            "security": ImprovementType.SECURITY_ENHANCEMENT,
            "security_enhancement": ImprovementType.SECURITY_ENHANCEMENT,
        }

        # 尝试直接匹配
        if type_str in type_mapping:
            return type_mapping[type_str]

        # 尝试作为枚举值
        try:
            return ImprovementType(type_str)
        except ValueError:
            # 默认返回代码重构
            logger.warning(f"未知的改进类型: {type_str}，使用默认值 CODE_REFACTORING")
            return ImprovementType.CODE_REFACTORING

    def _build_suggestions(self, state: GlobalState) -> list[Suggestion]:
        """
        构建建议列表

        Args:
            state: 全局状态

        Returns:
            list[Suggestion]: 建议列表
        """
        # 直接从 optimization_suggestions（可选字段）获取建议列表
        optimization_suggestions = state.get("optimization_suggestions", [])  # NotRequired 字段，使用 get

        suggestions = []
        for sugg_data in optimization_suggestions:
            # 处理 Pydantic 模型或字典
            if hasattr(sugg_data, 'suggestion_id'):
                # 已经是 Pydantic 模型
                suggestion = Suggestion(
                    suggestion_id=sugg_data.suggestion_id,
                    issue_id=sugg_data.issue_id,
                    improvement_type=self._map_improvement_type(sugg_data.improvement_type),
                    title=sugg_data.improvement_type,  # 使用 improvement_type 作为 title
                    description=sugg_data.explanation,
                    original_code=sugg_data.original_code,
                    improved_code=sugg_data.improved_code,
                    explanation=sugg_data.explanation,
                    impact_score=sugg_data.impact_score,  # 添加 impact_score 字段
                    impact_assessment=ImpactAssessment(
                        performance_impact="待评估",
                        readability_impact="待评估",
                        maintainability_impact="待评估",
                        risk_level=Severity.LOW
                    ),
                    confidence_score=sugg_data.impact_score / 10.0  # 转换为 0-1 范围
                )
            else:
                # 字典格式
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
                    improvement_type=self._map_improvement_type(sugg_data.get("improvement_type", "code_refactoring")),
                    title=sugg_data.get("title", ""),
                    description=sugg_data.get("description", ""),
                    original_code=sugg_data.get("original_code", ""),
                    improved_code=sugg_data.get("improved_code", ""),
                    explanation=sugg_data.get("explanation", ""),
                    impact_score=sugg_data.get("impact_score", 5.0),  # 添加 impact_score 字段
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
        # 从 shared_context（必需字段）获取验证结果
        validation_data = state["shared_context"].get("review_result", {}).get("validation_results")

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
        # 从 shared_context（必需字段）获取性能指标
        perf_data = state["shared_context"].get("performance_metrics")

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

    # ========================================================================
    # 报告生成方法
    # ========================================================================

    async def generate_report(
        self,
        task_id: str,
        request: Optional[ReportGenerationRequest] = None
    ) -> ReportResponse:
        """
        生成教学报告

        Args:
            task_id: 任务ID
            request: 报告生成请求（可选）

        Returns:
            ReportResponse: 报告响应
        """
        logger.info(f"生成教学报告: {task_id}")

        # 构建任务配置
        config = {"configurable": {"thread_id": task_id}}

        try:
            # 获取状态
            state = await self.graph_manager.get_state(config)

            if not state:
                raise ValueError(f"任务不存在: {task_id}")

            # 解析请求参数
            if request:
                report_format = ReportFormat(request.format)
                template = ReportTemplate(request.template)
                include_history = request.include_history
            else:
                report_format = ReportFormat.MARKDOWN
                template = ReportTemplate.DEFAULT
                include_history = True

            # 生成报告
            if report_format == ReportFormat.MARKDOWN:
                report_content = self.report_generator.generate_markdown_report(
                    state,
                    template=template,
                    include_history=include_history
                )
            else:
                raise NotImplementedError(f"暂不支持格式: {report_format}")

            # 保存报告（这里简化处理，实际应该保存到文件系统或对象存储）
            report_id = str(uuid.uuid4())
            report_filename = f"report_{task_id}_{report_id}.md"

            # TODO: 实际保存到文件系统
            # report_path = os.path.join(self.settings.reports_dir, report_filename)
            # with open(report_path, 'w', encoding='utf-8') as f:
            #     f.write(report_content)

            # 构建响应
            report_url = f"http://{self.settings.host}:{self.settings.port}/reports/{report_filename}"
            expires_at = datetime.now(timezone.utc).replace(hour=23, minute=59, second=59)  # 当天结束

            return ReportResponse(
                success=True,
                message="报告生成成功",
                report_id=report_id,
                report_url=report_url,
                format=report_format.value,
                size_bytes=len(report_content.encode('utf-8')),
                expires_at=expires_at
            )

        except Exception as e:
            logger.error(f"生成报告失败: {task_id}, 错误: {str(e)}")
            raise

    async def get_report_content(
        self,
        task_id: str,
        format: str = "markdown",
        template: str = "default",
        include_history: bool = True
    ) -> str:
        """
        获取报告内容（不保存文件）

        Args:
            task_id: 任务ID
            format: 报告格式
            template: 报告模板
            include_history: 是否包含优化历史

        Returns:
            str: 报告内容
        """
        logger.info(f"获取报告内容: {task_id}")

        # 构建任务配置
        config = {"configurable": {"thread_id": task_id}}

        try:
            # 获取状态
            state = await self.graph_manager.get_state(config)

            if not state:
                raise ValueError(f"任务不存在: {task_id}")

            # 生成报告
            report_format = ReportFormat(format)
            report_template = ReportTemplate(template)

            if report_format == ReportFormat.MARKDOWN:
                return self.report_generator.generate_markdown_report(
                    state,
                    template=report_template,
                    include_history=include_history
                )
            else:
                raise NotImplementedError(f"暂不支持格式: {report_format}")

        except Exception as e:
            logger.error(f"获取报告内容失败: {task_id}, 错误: {str(e)}")
            raise

