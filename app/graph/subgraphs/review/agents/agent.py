"""
代码评审子图 Agent 核心逻辑

本模块实现代码评审子图中的 Agent 类，包括：
- MistakeDetectorAgent: 问题检测智能体
- SuggestionGeneratorAgent: 建议生成智能体
- ValidationTesterAgent: 验证测试智能体
"""

import json
import re
import uuid
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

from langchain_core.messages import HumanMessage

from app.graph.state import (
    ReviewState,
    CodeIssue,
    Suggestion,
    IssueType,
    Severity
)
from app.graph.tools.python_repl import PythonSandbox
from app.graph.subgraphs.review.agents.prompts import (
    get_detection_prompt,
    get_suggestion_prompt,
    get_validation_prompt,
    get_fix_generation_prompt,
    get_improved_code_generation_prompt,
    get_quality_assessment_prompt
)
from app.core.logger import get_logger

logger = get_logger(__name__)


class ReviewPhase(str, Enum):
    """评审阶段枚举"""
    DETECTION = "detection"
    SUGGESTION = "suggestion"
    VALIDATION = "validation"
    NEGOTIATION = "negotiation"
    COMPLETED = "completed"


class ValidationStatus(str, Enum):
    """验证状态枚举"""
    PASSED = "passed"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class DetectionResult:
    """问题检测结果"""
    issues: List[CodeIssue]
    issue_categories: Dict[str, int]
    total_severity_score: float
    detection_confidence: float


@dataclass
class SuggestionResult:
    """建议生成结果"""
    suggestions: List[Suggestion]
    improved_code: str
    confidence_score: float
    explanation: str


@dataclass
class ValidationResult:
    """验证测试结果"""
    status: ValidationStatus
    passed_tests: int
    failed_tests: int
    test_details: List[Dict[str, Any]]
    quality_score: float
    issues_found: List[str]


class MistakeDetectorAgent:
    """
    问题检测智能体

    负责全面扫描代码，识别逻辑错误、边界条件问题、性能瓶颈和安全隐患。
    """

    def __init__(self, llm, sandbox: PythonSandbox):
        self.llm = llm
        self.sandbox = sandbox
        self.detection_prompt = get_detection_prompt()

    async def detect_code_issues(self, state: ReviewState) -> ReviewState:
        """
        检测代码问题

        Args:
            state: 当前评审状态

        Returns:
            更新后的评审状态，包含检测到的问题
        """
        try:
            logger.info(f"开始检测代码问题，代码长度: {len(state['code'])} 字符")

            # 1. 静态代码分析
            static_issues = await self._static_code_analysis(state['code'], state['language'])

            # 2. 使用 LLM 进行深度分析
            llm_issues = await self._llm_code_analysis(state)

            # 3. 运行时分析（如果适用）
            runtime_issues = await self._runtime_analysis(state['code'])

            # 4. 合并所有问题
            all_issues = static_issues + llm_issues + runtime_issues

            # 5. 去重和排序
            unique_issues = self._deduplicate_issues(all_issues)
            sorted_issues = self._sort_issues_by_severity(unique_issues)

            # 6. 统计问题类别
            issue_categories = self._categorize_issues(sorted_issues)

            # 7. 更新状态
            state['detected_issues'] = sorted_issues
            state['issue_categories'] = issue_categories
            state['review_phase'] = ReviewPhase.SUGGESTION.value

            logger.info(f"问题检测完成，发现 {len(sorted_issues)} 个问题")
            return state

        except Exception as e:
            logger.error(f"问题检测失败: {str(e)}")
            state['detection_errors'].append(f"问题检测失败: {str(e)}")
            return state

    async def _static_code_analysis(self, code: str, language: str) -> List[CodeIssue]:
        """静态代码分析"""
        issues = []

        if language.lower() == "python":
            try:
                import ast
                tree = ast.parse(code)

                # 检查常见问题
                for node in ast.walk(tree):
                    # 检查空的 except 块
                    if isinstance(node, ast.ExceptHandler) and not node.type:
                        issues.append(CodeIssue(
                            issue_id=str(uuid.uuid4()),
                            type=IssueType.MAINTAINABILITY,
                            severity=Severity.MEDIUM,
                            line_number=node.lineno,
                            description="使用了空的 except 块，可能会隐藏错误",
                            suggestion="指定具体的异常类型，避免捕获所有异常",
                            example_fix="except ValueError as e:\n    # 处理特定异常"
                        ))

                    # 检查过长的函数
                    if isinstance(node, ast.FunctionDef):
                        func_lines = node.end_lineno - node.lineno
                        if func_lines > 50:
                            issues.append(CodeIssue(
                                issue_id=str(uuid.uuid4()),
                                type=IssueType.MAINTAINABILITY,
                                severity=Severity.LOW,
                                line_number=node.lineno,
                                description=f"函数 '{node.name}' 过长 ({func_lines} 行)，建议拆分",
                                suggestion="将函数拆分为多个小函数，提高可读性和可维护性",
                                example_fix=None
                            ))

            except SyntaxError as e:
                issues.append(CodeIssue(
                    issue_id=str(uuid.uuid4()),
                    type=IssueType.LOGIC_ERROR,
                    severity=Severity.CRITICAL,
                    line_number=e.lineno or 0,
                    description=f"语法错误: {e.msg}",
                    suggestion="修复代码语法错误",
                    example_fix=None
                ))

        return issues

    async def _llm_code_analysis(self, state: ReviewState) -> List[CodeIssue]:
        """使用 LLM 进行深度代码分析"""
        try:
            response = await self.llm.ainvoke(
                self.detection_prompt.format_messages(
                    language=state['language'],
                    optimization_level=state['optimization_level'],
                    code=state['code']
                )
            )

            # 解析 LLM 响应
            issues = self._parse_llm_detection_response(response.content)
            return issues

        except Exception as e:
            logger.error(f"LLM 代码分析失败: {str(e)}")
            return []

    def _parse_llm_detection_response(self, response: str) -> List[CodeIssue]:
        """解析 LLM 的问题检测响应"""
        issues = []

        # 简化的解析实现
        # 实际项目中应该使用结构化输出或更复杂的解析逻辑
        lines = response.split('\n')

        current_issue = {}
        for line in lines:
            line = line.strip()

            # 检测问题类型
            if '逻辑错误' in line or 'logic error' in line.lower():
                current_issue['type'] = IssueType.LOGIC_ERROR
            elif '边界条件' in line or 'boundary' in line.lower():
                current_issue['type'] = IssueType.BOUNDARY_CONDITION
            elif '性能' in line or 'performance' in line.lower():
                current_issue['type'] = IssueType.PERFORMANCE
            elif '安全' in line or 'security' in line.lower():
                current_issue['type'] = IssueType.SECURITY

            # 检测严重程度
            if '严重' in line or 'critical' in line.lower():
                current_issue['severity'] = Severity.CRITICAL
            elif '高' in line or 'high' in line.lower():
                current_issue['severity'] = Severity.HIGH
            elif '中' in line or 'medium' in line.lower():
                current_issue['severity'] = Severity.MEDIUM
            elif '低' in line or 'low' in line.lower():
                current_issue['severity'] = Severity.LOW

        # 如果解析失败，返回一个通用问题
        if not issues:
            issues.append(CodeIssue(
                issue_id=str(uuid.uuid4()),
                type=IssueType.READABILITY,
                severity=Severity.LOW,
                line_number=1,
                description="代码可能存在改进空间",
                suggestion="建议进行代码审查和优化",
                example_fix=None
            ))

        return issues

    async def _runtime_analysis(self, code: str) -> List[CodeIssue]:
        """运行时分析"""
        issues = []

        try:
            # 尝试执行代码以检测运行时问题
            result = await self.sandbox.execute_code(code, timeout=5)

            if result.status == "error":
                issues.append(CodeIssue(
                    issue_id=str(uuid.uuid4()),
                    type=IssueType.LOGIC_ERROR,
                    severity=Severity.HIGH,
                    line_number=0,
                    description=f"运行时错误: {result.output[:200]}",
                    suggestion="修复代码中的运行时错误",
                    example_fix=None
                ))

        except Exception as e:
            logger.warning(f"运行时分析失败: {str(e)}")

        return issues

    def _deduplicate_issues(self, issues: List[CodeIssue]) -> List[CodeIssue]:
        """去除重复的问题"""
        seen = set()
        unique_issues = []

        for issue in issues:
            # 使用类型、行号和描述的组合作为唯一标识
            key = (issue.type, issue.line_number, issue.description[:50])
            if key not in seen:
                seen.add(key)
                unique_issues.append(issue)

        return unique_issues

    def _sort_issues_by_severity(self, issues: List[CodeIssue]) -> List[CodeIssue]:
        """按严重程度排序问题"""
        severity_order = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 1,
            Severity.MEDIUM: 2,
            Severity.LOW: 3
        }

        return sorted(issues, key=lambda x: severity_order.get(x.severity, 999))

    def _categorize_issues(self, issues: List[CodeIssue]) -> Dict[str, int]:
        """统计问题类别"""
        categories = {}

        for issue in issues:
            issue_type = issue.type.value
            categories[issue_type] = categories.get(issue_type, 0) + 1

        return categories


class SuggestionGeneratorAgent:
    """
    建议生成智能体

    负责根据检测到的问题生成具体的优化建议和改进代码。
    """

    def __init__(self, llm):
        self.llm = llm
        self.suggestion_prompt = get_suggestion_prompt()

    async def generate_suggestions(self, state: ReviewState) -> ReviewState:
        """
        生成优化建议

        Args:
            state: 当前评审状态

        Returns:
            更新后的评审状态，包含优化建议
        """
        try:
            logger.info(f"开始生成优化建议，问题数量: {len(state['detected_issues'])}")

            if not state['detected_issues']:
                logger.info("未检测到问题，跳过建议生成")
                state['review_phase'] = ReviewPhase.COMPLETED.value
                state['consensus_reached'] = True
                return state

            # 1. 按优先级分组问题
            prioritized_issues = self._prioritize_issues(state['detected_issues'])

            # 2. 为每个问题生成建议
            suggestions = []
            for issue in prioritized_issues:
                suggestion = await self._generate_single_suggestion(
                    state['code'],
                    state['language'],
                    issue,
                    state['optimization_level']
                )
                if suggestion:
                    suggestions.append(suggestion)

            # 3. 生成改进后的完整代码
            improved_code = await self._generate_improved_code(
                state['code'],
                state['language'],
                suggestions,
                state['optimization_level']
            )

            # 4. 更新状态
            state['generated_suggestions'] = suggestions
            state['improved_code_versions'].append(improved_code)
            state['current_code_version'] = len(state['improved_code_versions']) - 1
            state['review_phase'] = ReviewPhase.VALIDATION.value

            logger.info(f"优化建议生成完成，共 {len(suggestions)} 条建议")
            return state

        except Exception as e:
            logger.error(f"生成优化建议失败: {str(e)}")
            state['suggestion_errors'].append(f"生成优化建议失败: {str(e)}")
            return state

    def _prioritize_issues(self, issues: List[CodeIssue]) -> List[CodeIssue]:
        """按优先级排序问题"""
        # 已经在检测阶段排序过，这里可以进一步调整
        return issues

    async def _generate_single_suggestion(
        self,
        code: str,
        language: str,
        issue: CodeIssue,
        optimization_level: str
    ) -> Optional[Suggestion]:
        """为单个问题生成建议"""
        try:
            # 提取问题相关的代码片段
            code_lines = code.split('\n')
            line_idx = max(0, issue.line_number - 1)
            context_start = max(0, line_idx - 2)
            context_end = min(len(code_lines), line_idx + 3)
            original_snippet = '\n'.join(code_lines[context_start:context_end])

            # 使用 issue 中的建议或生成新建议
            improved_snippet = issue.example_fix or await self._generate_fix(
                original_snippet,
                issue,
                language
            )

            suggestion = Suggestion(
                suggestion_id=str(uuid.uuid4()),
                issue_id=issue.issue_id,
                improvement_type=issue.type.value,
                original_code=original_snippet,
                improved_code=improved_snippet,
                explanation=issue.suggestion,
                impact_score=self._calculate_impact_score(issue)
            )

            return suggestion

        except Exception as e:
            logger.error(f"生成单个建议失败: {str(e)}")
            return None

    async def _generate_fix(self, code_snippet: str, issue: CodeIssue, language: str) -> str:
        """生成修复代码"""
        try:
            prompt = get_fix_generation_prompt().format(
                issue_type=issue.type.value,
                description=issue.description,
                suggestion=issue.suggestion,
                language=language,
                code_snippet=code_snippet
            )

            response = await self.llm.ainvoke([HumanMessage(content=prompt)])

            # 提取代码块
            improved_code = self._extract_code_block(response.content)
            return improved_code or code_snippet

        except Exception as e:
            logger.error(f"生成修复代码失败: {str(e)}")
            return code_snippet

    def _extract_code_block(self, text: str) -> Optional[str]:
        """从文本中提取代码块"""
        # 匹配 ```language ... ``` 格式的代码块
        pattern = r'```(?:\w+)?\n(.*?)\n```'
        matches = re.findall(pattern, text, re.DOTALL)

        if matches:
            return matches[0].strip()

        # 如果没有代码块标记，返回整个文本
        return text.strip()

    def _calculate_impact_score(self, issue: CodeIssue) -> float:
        """计算影响评分"""
        severity_scores = {
            Severity.CRITICAL: 10.0,
            Severity.HIGH: 8.0,
            Severity.MEDIUM: 5.0,
            Severity.LOW: 2.0
        }

        return severity_scores.get(issue.severity, 5.0)

    async def _generate_improved_code(
        self,
        original_code: str,
        language: str,
        suggestions: List[Suggestion],
        optimization_level: str
    ) -> str:
        """生成改进后的完整代码"""
        try:
            # 构建改进说明
            improvements_desc = "\n".join([
                f"- {s.improvement_type}: {s.explanation}"
                for s in suggestions[:5]  # 限制数量
            ])

            prompt = get_improved_code_generation_prompt().format(
                language=language,
                original_code=original_code,
                improvements_desc=improvements_desc,
                optimization_level=optimization_level
            )

            response = await self.llm.ainvoke([HumanMessage(content=prompt)])

            # 提取改进后的代码
            improved_code = self._extract_code_block(response.content)
            return improved_code or original_code

        except Exception as e:
            logger.error(f"生成改进代码失败: {str(e)}")
            return original_code


class ValidationTesterAgent:
    """
    验证测试智能体

    负责验证改进代码的正确性和质量提升效果。
    """

    def __init__(self, llm, sandbox: PythonSandbox):
        self.llm = llm
        self.sandbox = sandbox
        self.validation_prompt = get_validation_prompt()

    async def validate_improvements(self, state: ReviewState) -> ReviewState:
        """
        验证代码改进

        Args:
            state: 当前评审状态

        Returns:
            更新后的评审状态，包含验证结果
        """
        try:
            logger.info("开始验证代码改进")

            if not state['improved_code_versions']:
                logger.warning("没有改进代码可供验证")
                state['review_phase'] = ReviewPhase.COMPLETED.value
                return state

            # 获取最新的改进代码
            improved_code = state['improved_code_versions'][-1]

            # 1. 功能正确性测试
            functionality_result = await self._test_functionality(
                state['code'],
                improved_code,
                state['language']
            )

            # 2. 问题修复验证
            fix_verification = await self._verify_fixes(
                state['code'],
                improved_code,
                state['detected_issues'],
                state['generated_suggestions']
            )

            # 3. 质量评估
            quality_metrics = await self._assess_quality(
                improved_code,
                state['language'],
                state['optimization_level']
            )

            # 4. 性能对比（如果适用）
            performance_comparison = await self._compare_performance(
                state['code'],
                improved_code
            )

            # 5. 综合评估
            validation_result = self._综合评估(
                functionality_result,
                fix_verification,
                quality_metrics,
                performance_comparison
            )

            # 6. 更新状态
            state['validation_results'].append(validation_result)
            state['quality_metrics'] = quality_metrics
            state['test_cases_passed'] = validation_result['passed_tests']
            state['test_cases_failed'] = validation_result['failed_tests']

            # 7. 判断是否达到质量阈值
            quality_score = quality_metrics.get('overall_score', 0)
            if quality_score >= state['quality_threshold']:
                state['consensus_reached'] = True
                state['review_phase'] = ReviewPhase.COMPLETED.value
                logger.info(f"质量评分 {quality_score} 达到阈值 {state['quality_threshold']}，评审完成")
            else:
                # 需要进一步协商或迭代
                state['review_phase'] = ReviewPhase.NEGOTIATION.value
                state['iteration_count'] += 1
                logger.info(f"质量评分 {quality_score} 未达到阈值，进入协商阶段")

            return state

        except Exception as e:
            logger.error(f"验证代码改进失败: {str(e)}")
            state['error_info'] = f"验证失败: {str(e)}"
            return state

    async def _test_functionality(
        self,
        original_code: str,
        improved_code: str,
        language: str
    ) -> Dict[str, Any]:
        """测试功能正确性"""
        try:
            # 在沙箱中执行两个版本的代码
            original_result = await self.sandbox.execute_code(original_code, timeout=10)
            improved_result = await self.sandbox.execute_code(improved_code, timeout=10)

            # 比较执行结果
            functionality_preserved = (
                original_result.status == improved_result.status and
                original_result.output == improved_result.output
            )

            return {
                "functionality_preserved": functionality_preserved,
                "original_status": original_result.status,
                "improved_status": improved_result.status,
                "details": "功能保持一致" if functionality_preserved else "功能可能有变化"
            }

        except Exception as e:
            logger.error(f"功能测试失败: {str(e)}")
            return {
                "functionality_preserved": False,
                "error": str(e)
            }

    async def _verify_fixes(
        self,
        original_code: str,
        improved_code: str,
        issues: List[CodeIssue],
        suggestions: List[Suggestion]
    ) -> Dict[str, Any]:
        """验证问题修复"""
        fixed_issues = []
        unfixed_issues = []

        for issue in issues:
            # 简化的验证逻辑
            # 实际项目中应该更详细地检查每个问题是否被修复
            corresponding_suggestion = next(
                (s for s in suggestions if s.issue_id == issue.issue_id),
                None
            )

            if corresponding_suggestion and corresponding_suggestion.improved_code in improved_code:
                fixed_issues.append(issue.issue_id)
            else:
                unfixed_issues.append(issue.issue_id)

        return {
            "fixed_count": len(fixed_issues),
            "unfixed_count": len(unfixed_issues),
            "fixed_issues": fixed_issues,
            "unfixed_issues": unfixed_issues,
            "fix_rate": len(fixed_issues) / len(issues) if issues else 1.0
        }

    async def _assess_quality(
        self,
        code: str,
        language: str,
        optimization_level: str
    ) -> dict[str, float] | dict[str, float | str] | Any:
        """评估代码质量"""
        try:
            # 使用 LLM 评估代码质量
            prompt = get_quality_assessment_prompt().format(
                language=language,
                code=code
            )

            response = await self.llm.ainvoke([HumanMessage(content=prompt)])

            # 尝试解析 JSON 响应
            try:
                metrics = json.loads(response.content)
            except:
                # 如果解析失败，使用默认值
                metrics = {
                    "readability": 7.0,
                    "maintainability": 7.0,
                    "performance": 7.0,
                    "security": 7.0,
                    "best_practices": 7.0
                }

            # 计算总体评分
            metrics['overall_score'] = sum(metrics.values()) / len(metrics)

            return metrics

        except Exception as e:
            logger.error(f"质量评估失败: {str(e)}")
            return {
                "overall_score": 5.0,
                "error": str(e)
            }

    async def _compare_performance(
        self,
        original_code: str,
        improved_code: str
    ) -> Dict[str, Any]:
        """比较性能"""
        try:
            # 简化的性能测试
            # 实际项目中应该使用更精确的性能测试方法

            # 测试原始代码
            start = time.time()
            original_result = await self.sandbox.execute_code(original_code, timeout=10)
            original_time = time.time() - start

            # 测试改进代码
            start = time.time()
            improved_result = await self.sandbox.execute_code(improved_code, timeout=10)
            improved_time = time.time() - start

            improvement_ratio = (original_time - improved_time) / original_time if original_time > 0 else 0

            return {
                "original_time": original_time,
                "improved_time": improved_time,
                "improvement_ratio": improvement_ratio,
                "performance_improved": improved_time < original_time
            }

        except Exception as e:
            logger.error(f"性能比较失败: {str(e)}")
            return {
                "performance_improved": False,
                "error": str(e)
            }

    def _综合评估(
        self,
        functionality_result: Dict[str, Any],
        fix_verification: Dict[str, Any],
        quality_metrics: Dict[str, float],
        performance_comparison: Dict[str, Any]
    ) -> Dict[str, Any]:
        """综合评估验证结果"""
        # 计算通过的测试数量
        passed_tests = 0
        failed_tests = 0
        test_details = []

        # 功能测试
        if functionality_result.get('functionality_preserved', False):
            passed_tests += 1
            test_details.append({
                "test": "功能正确性",
                "status": "passed",
                "details": functionality_result.get('details', '')
            })
        else:
            failed_tests += 1
            test_details.append({
                "test": "功能正确性",
                "status": "failed",
                "details": functionality_result.get('details', '')
            })

        # 问题修复验证
        fix_rate = fix_verification.get('fix_rate', 0)
        if fix_rate >= 0.8:  # 80% 的问题被修复
            passed_tests += 1
            test_details.append({
                "test": "问题修复",
                "status": "passed",
                "details": f"修复率: {fix_rate:.1%}"
            })
        else:
            failed_tests += 1
            test_details.append({
                "test": "问题修复",
                "status": "failed",
                "details": f"修复率: {fix_rate:.1%}"
            })

        # 质量评估
        quality_score = quality_metrics.get('overall_score', 0)
        if quality_score >= 7.0:
            passed_tests += 1
            test_details.append({
                "test": "代码质量",
                "status": "passed",
                "details": f"质量评分: {quality_score:.1f}/10"
            })
        else:
            failed_tests += 1
            test_details.append({
                "test": "代码质量",
                "status": "failed",
                "details": f"质量评分: {quality_score:.1f}/10"
            })

        # 确定总体状态
        if failed_tests == 0:
            status = ValidationStatus.PASSED
        elif passed_tests > 0:
            status = ValidationStatus.PARTIAL
        else:
            status = ValidationStatus.FAILED

        return {
            "status": status.value,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "test_details": test_details,
            "quality_score": quality_score,
            "issues_found": []
        }
