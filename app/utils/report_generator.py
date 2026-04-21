"""
教学报告生成模块

提供 Markdown 格式的教学报告生成功能，支持多格式导出。
"""

from typing import Dict, Any, List
from datetime import datetime, timezone
from enum import Enum

from app.graph.state import GlobalState
from app.core.logger import get_logger

logger = get_logger(__name__)


class ReportFormat(str, Enum):
    """报告格式枚举"""
    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"


class ReportTemplate(str, Enum):
    """报告模板枚举"""
    DEFAULT = "default"
    DETAILED = "detailed"
    SUMMARY = "summary"


class ReportGenerator:
    """
    教学报告生成器

    根据任务执行结果生成结构化的教学报告。
    """

    def __init__(self):
        """初始化报告生成器"""
        pass

    def generate_markdown_report(
        self,
        state: GlobalState,
        template: ReportTemplate = ReportTemplate.DEFAULT,
        include_history: bool = True
    ) -> str:
        """
        生成 Markdown 格式报告

        Args:
            state: 全局状态
            template: 报告模板
            include_history: 是否包含优化历史

        Returns:
            str: Markdown 格式报告
        """
        logger.info(f"生成 Markdown 报告: template={template}, include_history={include_history}")

        if template == ReportTemplate.DETAILED:
            return self._generate_detailed_report(state, include_history)
        elif template == ReportTemplate.SUMMARY:
            return self._generate_summary_report(state)
        else:
            return self._generate_default_report(state, include_history)

    def _generate_default_report(self, state: GlobalState, include_history: bool) -> str:
        """生成默认模板报告"""
        sections = []

        # 标题和元信息
        sections.append(self._generate_header(state))

        # 任务概览
        sections.append(self._generate_overview(state))

        # 算法分析
        sections.append(self._generate_algorithm_analysis(state))

        # 代码问题检测
        sections.append(self._generate_issues_section(state))

        # 优化建议
        sections.append(self._generate_suggestions_section(state))

        # 优化对比
        sections.append(self._generate_comparison_section(state))

        # 优化历史（可选）
        if include_history:
            sections.append(self._generate_history_section(state))

        # 总结
        sections.append(self._generate_conclusion(state))

        # 附录
        sections.append(self._generate_appendix(state))

        return "\n\n".join(sections)

    def _generate_detailed_report(self, state: GlobalState, include_history: bool) -> str:
        """生成详细模板报告"""
        sections = []

        # 标题和元信息
        sections.append(self._generate_header(state))

        # 执行摘要
        sections.append(self._generate_executive_summary(state))

        # 任务详情
        sections.append(self._generate_task_details(state))

        # 算法深度分析
        sections.append(self._generate_detailed_algorithm_analysis(state))

        # 代码质量评估
        sections.append(self._generate_code_quality_assessment(state))

        # 优化方案详解
        sections.append(self._generate_detailed_optimization_plan(state))

        # 性能测试结果
        sections.append(self._generate_performance_results(state))

        # 优化历史（可选）
        if include_history:
            sections.append(self._generate_history_section(state))

        # 最佳实践建议
        sections.append(self._generate_best_practices(state))

        # 总结与展望
        sections.append(self._generate_detailed_conclusion(state))

        return "\n\n".join(sections)

    def _generate_summary_report(self, state: GlobalState) -> str:
        """生成摘要模板报告"""
        sections = []

        # 标题
        sections.append(f"# {state.get('task_id', 'Unknown')} - 分析摘要\n")

        # 快速概览
        sections.append("## 快速概览\n")
        sections.append(f"- **语言**: {state.get('language', 'Unknown')}")
        sections.append(f"- **优化级别**: {state.get('optimization_level', 'Unknown')}")
        sections.append(f"- **状态**: {state.get('status', 'Unknown').value}")

        # 关键发现 - 从 algorithm_explanation 或 shared_context 获取
        algorithm_explanation = state.get("algorithm_explanation")
        sections.append("\n## 关键发现\n")
        if algorithm_explanation:
            sections.append(f"- **时间复杂度**: {algorithm_explanation.time_complexity}")
            sections.append(f"- **空间复杂度**: {algorithm_explanation.space_complexity}")
        else:
            sections.append("- 暂无算法分析结果")

        # 主要问题 - 直接从 detected_issues 获取
        issues = state.get("detected_issues", [])
        sections.append(f"\n## 主要问题 ({len(issues)})\n")
        for i, issue in enumerate(issues[:3], 1):  # 只显示前3个
            sections.append(f"{i}. **{issue.type.value}** (严重程度: {issue.severity.value})")
            sections.append(f"   {issue.description}")

        # 优化建议 - 直接从 optimization_suggestions 获取
        suggestions = state.get("optimization_suggestions", [])
        sections.append(f"\n## 优化建议 ({len(suggestions)})\n")
        for i, sugg in enumerate(suggestions[:3], 1):  # 只显示前3个
            sections.append(f"{i}. {sugg.improvement_type} (影响评分: {sugg.impact_score:.1f}/10)")

        return "\n".join(sections)

    # ========================================================================
    # 章节生成方法
    # ========================================================================

    def _generate_header(self, state: GlobalState) -> str:
        """生成报告头部"""
        task_id = state.get("task_id", "Unknown")
        created_at = state.get("created_at", datetime.now(timezone.utc))
        language = state.get("language", "Unknown")

        return f"""# AlgoWeaver AI 教学报告

**任务ID**: `{task_id}`
**生成时间**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}
**编程语言**: {language}
**分析开始时间**: {created_at.strftime('%Y-%m-%d %H:%M:%S')}

---"""

    def _generate_overview(self, state: GlobalState) -> str:
        """生成任务概览"""
        status = state.get("status")
        optimization_level = state.get("optimization_level", "Unknown")
        progress = state.get("progress", 0)

        return f"""## 任务概览

- **状态**: {status.value if status else 'Unknown'}
- **优化级别**: {optimization_level}
- **完成进度**: {int(progress * 100)}%
- **执行阶段**: {state.get('current_phase', 'Unknown').value if state.get('current_phase') else 'Unknown'}"""

    def _generate_algorithm_analysis(self, state: GlobalState) -> str:
        """生成算法分析章节"""
        # 从 algorithm_explanation 获取算法分析结果
        algorithm_explanation = state.get("algorithm_explanation")

        if not algorithm_explanation:
            return "## 算法分析\n\n暂无算法分析结果。"

        # 从 shared_context 获取算法类型（如果有）
        algorithm_type = state.get("shared_context", {}).get("dissection_result", {}).get("algorithm_type", "未知算法")
        time_complexity = algorithm_explanation.time_complexity
        space_complexity = algorithm_explanation.space_complexity
        pseudocode = algorithm_explanation.pseudocode
        steps = algorithm_explanation.steps
        key_insights = algorithm_explanation.key_insights

        lines = [
            "## 算法分析",
            "",
            f"### 算法类型: {algorithm_type}",
            "",
            "### 复杂度分析",
            "",
            f"- **时间复杂度**: {time_complexity}",
            f"- **空间复杂度**: {space_complexity}",
            ""
        ]

        # 伪代码
        if pseudocode:
            lines.extend([
                "### 伪代码",
                "",
                "```",
                pseudocode,
                "```",
                ""
            ])

        # 执行步骤
        if steps:
            lines.extend([
                f"### 执行步骤 ({len(steps)} 步)",
                ""
            ])
            for i, step in enumerate(steps, 1):
                lines.append(f"#### 步骤 {i}: {step.description}")
                lines.append("")
                if step.code_snippet:
                    lines.append("```python")
                    lines.append(step.code_snippet)
                    lines.append("```")
                    lines.append("")
                if step.variables_state:
                    lines.append("**变量状态**:")
                    for var, value in step.variables_state.items():
                        lines.append(f"- `{var}` = `{value}`")
                    lines.append("")

        # 关键洞察
        if key_insights:
            lines.extend([
                "### 关键洞察",
                ""
            ])
            for insight in key_insights:
                lines.append(f"- {insight}")

        return "\n".join(lines)

    def _generate_issues_section(self, state: GlobalState) -> str:
        """生成代码问题章节"""
        # 直接从 detected_issues 获取问题列表
        issues = state.get("detected_issues", [])

        if not issues:
            return "## 代码问题检测\n\n✅ 未发现明显问题。"

        lines = [
            f"## 代码问题检测 ({len(issues)} 个问题)",
            ""
        ]

        # 按严重程度分组
        critical_issues = [i for i in issues if i.severity.value == "critical"]
        high_issues = [i for i in issues if i.severity.value == "high"]
        medium_issues = [i for i in issues if i.severity.value == "medium"]
        low_issues = [i for i in issues if i.severity.value == "low"]

        if critical_issues:
            lines.append("### 🔴 严重问题")
            lines.append("")
            for issue in critical_issues:
                lines.extend(self._format_issue(issue))

        if high_issues:
            lines.append("### 🟠 高优先级问题")
            lines.append("")
            for issue in high_issues:
                lines.extend(self._format_issue(issue))

        if medium_issues:
            lines.append("### 🟡 中等问题")
            lines.append("")
            for issue in medium_issues:
                lines.extend(self._format_issue(issue))

        if low_issues:
            lines.append("### 🟢 低优先级问题")
            lines.append("")
            for issue in low_issues:
                lines.extend(self._format_issue(issue))

        return "\n".join(lines)

    def _format_issue(self, issue: Dict[str, Any]) -> List[str]:
        """格式化单个问题"""
        # 处理 Pydantic 模型或字典
        if hasattr(issue, 'type'):
            # Pydantic 模型
            issue_type = issue.type.value if hasattr(issue.type, 'value') else str(issue.type)
            line_number = issue.line_number
            description = issue.description
            suggestion = issue.suggestion
            example_fix = issue.example_fix
        else:
            # 字典
            issue_type = issue.get('type', 'Unknown')
            line_number = issue.get('line_number', '?')
            description = issue.get('description', '')
            suggestion = issue.get('suggestion', '')
            example_fix = issue.get('example_fix')

        lines = [
            f"#### {issue_type} (行 {line_number})",
            "",
            f"**描述**: {description}",
            "",
            f"**建议**: {suggestion}",
            ""
        ]

        if example_fix:
            lines.append("**修复示例**:")
            lines.append("")
            lines.append("```python")
            lines.append(example_fix)
            lines.append("```")
            lines.append("")

        return lines

    def _generate_suggestions_section(self, state: GlobalState) -> str:
        """生成优化建议章节"""
        # 直接从 optimization_suggestions 获取建议列表
        suggestions = state.get("optimization_suggestions", [])

        if not suggestions:
            return "## 优化建议\n\n暂无优化建议。"

        lines = [
            f"## 优化建议 ({len(suggestions)} 条)",
            ""
        ]

        for i, sugg in enumerate(suggestions, 1):
            # 处理 Pydantic 模型或字典
            if hasattr(sugg, 'improvement_type'):
                # Pydantic 模型
                improvement_type = sugg.improvement_type
                original_code = sugg.original_code
                improved_code = sugg.improved_code
                explanation = sugg.explanation
                impact_score = sugg.impact_score
            else:
                # 字典
                improvement_type = sugg.get('improvement_type', 'Unknown')
                original_code = sugg.get('original_code', '')
                improved_code = sugg.get('improved_code', '')
                explanation = sugg.get('explanation', '')
                impact_score = sugg.get('impact_score', 0)

            lines.extend([
                f"### 建议 {i}: {improvement_type}",
                "",
                f"**影响评分**: {impact_score:.1f}/10",
                "",
                f"**说明**: {explanation}",
                "",
                "#### 原始代码",
                "",
                "```python",
                original_code,
                "```",
                "",
                "#### 改进代码",
                "",
                "```python",
                improved_code,
                "```",
                ""
            ])

            # 影响评估（如果有）
            if hasattr(sugg, 'impact_assessment') and sugg.impact_assessment:
                impact = sugg.impact_assessment
                lines.extend([
                    "**影响评估**:",
                    "",
                    f"- 性能影响: {impact.performance_impact}",
                    f"- 可读性影响: {impact.readability_impact}",
                    f"- 可维护性影响: {impact.maintainability_impact}",
                    f"- 风险等级: {impact.risk_level.value}",
                    ""
                ])
            elif isinstance(sugg, dict) and sugg.get("impact_assessment"):
                impact = sugg["impact_assessment"]
                lines.extend([
                    "**影响评估**:",
                    "",
                    f"- 性能影响: {impact.get('performance_impact', 'Unknown')}",
                    f"- 可读性影响: {impact.get('readability_impact', 'Unknown')}",
                    f"- 可维护性影响: {impact.get('maintainability_impact', 'Unknown')}",
                    f"- 风险等级: {impact.get('risk_level', 'Unknown')}",
                    ""
                ])

        return "\n".join(lines)

    def _generate_comparison_section(self, state: GlobalState) -> str:
        """生成优化对比章节"""
        original_code = state.get("original_code", "")
        # 使用最新的代码版本作为优化后代码
        code_versions = state.get("code_versions", [])
        optimized_code = code_versions[-1] if len(code_versions) > 1 else None

        if not optimized_code or optimized_code == original_code:
            return "## 优化对比\n\n暂无优化代码。"

        lines = [
            "## 优化对比",
            "",
            "### 原始代码",
            "",
            "```python",
            original_code,
            "```",
            "",
            "### 优化后代码",
            "",
            "```python",
            optimized_code,
            "```",
            ""
        ]

        # 性能对比（从 shared_context 获取）
        perf_metrics = state.get("shared_context", {}).get("performance_metrics")
        if perf_metrics:
            lines.extend([
                "### 性能对比",
                "",
                f"- **执行时间**: {perf_metrics.get('execution_time_ms', 0):.2f} ms",
                f"- **内存使用**: {perf_metrics.get('memory_usage_mb', 0):.2f} MB",
                f"- **平均时间**: {perf_metrics.get('average_time_ms', 0):.2f} ms",
                ""
            ])

        return "\n".join(lines)

    def _generate_history_section(self, state: GlobalState) -> str:
        """生成优化历史章节"""
        # 从 shared_context 获取优化历史
        history = state.get("shared_context", {}).get("optimization_history", [])

        if not history:
            return "## 优化历史\n\n暂无优化历史记录。"

        lines = [
            f"## 优化历史 ({len(history)} 次迭代)",
            ""
        ]

        for i, record in enumerate(history, 1):
            lines.extend([
                f"### 迭代 {i}",
                "",
                f"- **时间**: {record.get('timestamp', 'Unknown')}",
                f"- **操作**: {record.get('action', 'Unknown')}",
                f"- **结果**: {record.get('result', 'Unknown')}",
                ""
            ])

        return "\n".join(lines)

    def _generate_conclusion(self, state: GlobalState) -> str:
        """生成总结章节"""
        final_summary = state.get("shared_context", {}).get("final_summary", {})

        lines = [
            "## 总结",
            ""
        ]

        if final_summary:
            lines.append(final_summary.get("summary", "分析完成。"))
        else:
            lines.append("本次代码分析已完成，请查看上述详细报告。")

        lines.extend([
            "",
            "---",
            "",
            f"*报告由 AlgoWeaver AI 自动生成于 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}*"
        ])

        return "\n".join(lines)

    def _generate_appendix(self, state: GlobalState) -> str:
        """生成附录章节"""
        lines = [
            "## 附录",
            "",
            "### 术语表",
            "",
            "- **时间复杂度**: 算法执行时间随输入规模增长的趋势",
            "- **空间复杂度**: 算法所需内存空间随输入规模增长的趋势",
            "- **置信度**: AI 对建议准确性的信心程度",
            ""
        ]

        return "\n".join(lines)

    # 详细报告专用方法
    def _generate_executive_summary(self, state: GlobalState) -> str:
        """生成执行摘要"""
        return "## 执行摘要\n\n本报告详细分析了提交的代码，包括算法分析、问题检测和优化建议。"

    def _generate_task_details(self, state: GlobalState) -> str:
        """生成任务详情"""
        return f"""## 任务详情

- **任务ID**: {state.get('task_id', 'Unknown')}
- **用户ID**: {state.get('user_id', 'Unknown')}
- **语言**: {state.get('language', 'Unknown')}
- **优化级别**: {state.get('optimization_level', 'Unknown')}"""

    def _generate_detailed_algorithm_analysis(self, state: GlobalState) -> str:
        """生成详细算法分析"""
        return self._generate_algorithm_analysis(state)

    def _generate_code_quality_assessment(self, state: GlobalState) -> str:
        """生成代码质量评估"""
        return self._generate_issues_section(state)

    def _generate_detailed_optimization_plan(self, state: GlobalState) -> str:
        """生成详细优化方案"""
        return self._generate_suggestions_section(state)

    def _generate_performance_results(self, state: GlobalState) -> str:
        """生成性能测试结果"""
        return self._generate_comparison_section(state)

    def _generate_best_practices(self, state: GlobalState) -> str:
        """生成最佳实践建议"""
        return "## 最佳实践建议\n\n- 保持代码简洁\n- 注重可读性\n- 优化关键路径"

    def _generate_detailed_conclusion(self, state: GlobalState) -> str:
        """生成详细总结"""
        return self._generate_conclusion(state)


# 便捷函数
def generate_report(
    state: GlobalState,
    format: ReportFormat = ReportFormat.MARKDOWN,
    template: ReportTemplate = ReportTemplate.DEFAULT,
    include_history: bool = True
) -> str:
    """
    生成教学报告的便捷函数

    Args:
        state: 全局状态
        format: 报告格式
        template: 报告模板
        include_history: 是否包含优化历史

    Returns:
        str: 生成的报告内容
    """
    generator = ReportGenerator()

    if format == ReportFormat.MARKDOWN:
        return generator.generate_markdown_report(state, template, include_history)
    else:
        # TODO: 支持其他格式
        raise NotImplementedError(f"暂不支持格式: {format}")
