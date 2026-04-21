"""
Supervisor Agent 核心逻辑

本模块实现 Supervisor Agent 的核心功能，包括任务分析、路由决策、智能体协调和状态管理。
Supervisor Agent 是整个多智能体系统的全局调度主管，负责协调各个子图和智能体的执行。
"""

import json
import asyncio
from time import timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timezone

from app.graph.state import (
    GlobalState,
    StateTaskStatus,
    Phase,
    CollaborationMode,
)
from app.graph.supervisor.prompts import (
    get_task_analysis_prompt,
    get_routing_decision_prompt,
    get_coordination_prompt,
    get_human_intervention_prompt,
    get_error_handling_prompt,
    get_summary_generation_prompt
)
from app.core.logger import get_logger

logger = get_logger(__name__)


class TaskType(str, Enum):
    """任务类型枚举"""
    ALGORITHM_DISSECTION = "algorithm_dissection"
    CODE_REVIEW = "code_review"
    FULL_WEAVING = "full_weaving"


class NextStep(str, Enum):
    """下一步执行节点枚举"""
    DISSECTION_SUBGRAPH = "dissection_subgraph"
    REVIEW_SUBGRAPH = "review_subgraph"
    HUMAN_INTERVENTION = "human_intervention"
    COMPLETE = "complete"
    ERROR = "error"


class RecoveryStrategy(str, Enum):
    """错误恢复策略枚举"""
    RETRY = "retry"
    DEGRADE = "degrade"
    SKIP = "skip"
    ABORT = "abort"
    HUMAN = "human"


@dataclass
class TaskPlan:
    """任务执行计划"""
    task_type: TaskType
    complexity: str  # "simple", "medium", "complex"
    required_subgraphs: List[str]
    execution_order: List[str]
    estimated_duration: int  # 秒
    special_requirements: Optional[str] = None


@dataclass
class RoutingDecision:
    """路由决策"""
    next_step: NextStep
    reason: str
    requires_human_input: bool
    estimated_duration: int


@dataclass
class CoordinationResult:
    """协调结果"""
    coordination_mode: CollaborationMode
    final_decision: str
    consensus_level: float  # 0-100%
    dissenting_opinions: List[str]
    action_items: List[str]


@dataclass
class ErrorHandlingPlan:
    """错误处理方案"""
    error_type: str
    severity: str  # "low", "medium", "high", "critical"
    recovery_strategy: RecoveryStrategy
    retry_count: int
    max_retries: int
    fallback_action: str
    user_message: str


class SupervisorAgent:
    """
    Supervisor Agent - 全局任务调度主管

    负责整个多智能体系统的任务分析、路由决策、智能体协调和状态管理。
    """

    def __init__(self, llm, max_retries: int = 3):
        self.llm = llm
        self.max_retries = max_retries

        # 加载提示词模板
        self.task_analysis_prompt = get_task_analysis_prompt()
        self.routing_decision_prompt = get_routing_decision_prompt()
        self.coordination_prompt = get_coordination_prompt()
        self.human_intervention_prompt = get_human_intervention_prompt()
        self.error_handling_prompt = get_error_handling_prompt()
        self.summary_generation_prompt = get_summary_generation_prompt()

    async def analyze_task(self, state: GlobalState) -> TaskPlan:
        """
        分析任务并制定执行计划

        Args:
            state: 全局状态

        Returns:
            任务执行计划
        """
        try:
            logger.info(f"开始分析任务 {state['task_id']}")

            # 准备提示词输入
            prompt_input = {
                "user_id": state['user_id'],
                "task_id": state['task_id'],
                "code": state['original_code'],
                "language": state['language'],
                "optimization_level": state['optimization_level'],
                "custom_requirements": state.get('shared_context', {}).get('custom_requirements', '无特殊要求')
            }

            # 调用 LLM 进行任务分析
            response = await self.llm.ainvoke(
                self.task_analysis_prompt.format_messages(**prompt_input)
            )

            # 解析响应
            task_plan = self._parse_task_plan(response.content)

            logger.info(f"任务分析完成: 类型={task_plan.task_type}, 复杂度={task_plan.complexity}")
            return task_plan

        except Exception as e:
            logger.error(f"任务分析失败: {str(e)}")
            # 返回默认计划
            return TaskPlan(
                task_type=TaskType.FULL_WEAVING,
                complexity="medium",
                required_subgraphs=["dissection_subgraph", "review_subgraph"],
                execution_order=["dissection_subgraph", "review_subgraph"],
                estimated_duration=60,
                special_requirements=None
            )

    async def route_to_next_step(self, state: GlobalState) -> RoutingDecision:
        """
        决定下一步执行路径

        Args:
            state: 全局状态

        Returns:
            路由决策
        """
        try:
            logger.info(f"进行路由决策，当前阶段: {state['current_phase']}")

            # 检查是否需要人工干预
            if state.get('human_intervention_required', False):
                return RoutingDecision(
                    next_step=NextStep.HUMAN_INTERVENTION,
                    reason="需要用户确认或提供输入",
                    requires_human_input=True,
                    estimated_duration=0
                )

            # 准备提示词输入
            prompt_input = self._prepare_routing_input(state)

            # 调用 LLM 进行路由决策
            response = await self.llm.ainvoke(
                self.routing_decision_prompt.format_messages(**prompt_input)
            )

            # 解析响应
            decision = self._parse_routing_decision(response.content)

            logger.info(f"路由决策: {decision.next_step}, 理由: {decision.reason}")
            return decision

        except Exception as e:
            logger.error(f"路由决策失败: {str(e)}")
            # 返回默认决策
            return self._get_default_routing_decision(state)

    async def coordinate_agents(
        self,
        scenario: str,
        agents_info: Dict[str, Any],
        opinions: Dict[str, str],
        conflicts: List[str]
    ) -> CoordinationResult:
        """
        协调多个智能体的协作

        Args:
            scenario: 协作场景描述
            agents_info: 参与智能体信息
            opinions: 各方意见
            conflicts: 冲突点列表

        Returns:
            协调结果
        """
        try:
            logger.info(f"开始智能体协调: {scenario}")

            # 准备提示词输入
            prompt_input = {
                "scenario": scenario,
                "agents_info": json.dumps(agents_info, ensure_ascii=False, indent=2),
                "opinions": json.dumps(opinions, ensure_ascii=False, indent=2),
                "conflicts": "\n".join(f"- {c}" for c in conflicts),
                "time_constraint": "无严格限制",
                "quality_requirement": "高质量",
                "user_preference": "平衡质量和效率"
            }

            # 调用 LLM 进行协调
            response = await self.llm.ainvoke(
                self.coordination_prompt.format_messages(**prompt_input)
            )

            # 解析响应
            result = self._parse_coordination_result(response.content)

            logger.info(f"协调完成: 共识程度={result.consensus_level}%")
            return result

        except Exception as e:
            logger.error(f"智能体协调失败: {str(e)}")
            # 返回默认协调结果
            return CoordinationResult(
                coordination_mode=CollaborationMode.MASTER_EXPERT,
                final_decision="采用主控决策",
                consensus_level=100.0,
                dissenting_opinions=[],
                action_items=["继续执行"]
            )

    async def handle_human_intervention(
        self,
        state: GlobalState,
        reason: str,
        options: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        处理人工干预请求

        Args:
            state: 全局状态
            reason: 干预原因
            options: 可选项列表

        Returns:
            人工干预请求数据
        """
        try:
            logger.info(f"生成人工干预请求: {reason}")

            # 准备提示词输入
            prompt_input = {
                "reason": reason,
                "current_situation": self._describe_current_situation(state),
                "decision_content": reason,
                "available_options": json.dumps(options, ensure_ascii=False, indent=2),
                "recommended_option": options[0]['id'] if options else None,
                "impact_analysis": "各选项的影响分析"
            }

            # 调用 LLM 生成干预请求
            response = await self.llm.ainvoke(
                self.human_intervention_prompt.format_messages(**prompt_input)
            )

            # 解析响应
            intervention_request = self._parse_intervention_request(response.content)

            logger.info("人工干预请求生成完成")
            return intervention_request

        except Exception as e:
            logger.error(f"生成人工干预请求失败: {str(e)}")
            # 返回默认请求
            return {
                "intervention_type": "confirmation",
                "title": "需要确认",
                "description": reason,
                "options": options,
                "default_option": options[0]['id'] if options else None
            }

    async def handle_error(
        self,
        error: Exception,
        context: Dict[str, Any],
        retry_count: int
    ) -> ErrorHandlingPlan:
        """
        处理执行错误

        Args:
            error: 错误对象
            context: 执行上下文
            retry_count: 已重试次数

        Returns:
            错误处理方案
        """
        try:
            logger.error(f"处理错误: {str(error)}")

            # 准备提示词输入
            prompt_input = {
                "error_message": str(error),
                "error_stack": self._get_error_stack(error),
                "node_name": context.get('node_name', 'unknown'),
                "phase": context.get('phase', 'unknown'),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "execution_context": json.dumps(context, ensure_ascii=False, indent=2),
                "previous_attempts": f"已重试 {retry_count} 次",
                "retry_count": retry_count,
                "max_retries": self.max_retries,
                "resource_usage": "正常",
                "other_tasks": "无"
            }

            # 调用 LLM 分析错误
            response = await self.llm.ainvoke(
                self.error_handling_prompt.format_messages(**prompt_input)
            )

            # 解析响应
            plan = self._parse_error_handling_plan(response.content, retry_count)

            logger.info(f"错误处理方案: {plan.recovery_strategy}")
            return plan

        except Exception as e:
            logger.error(f"错误处理失败: {str(e)}")
            # 返回默认处理方案
            return self._get_default_error_handling_plan(error, retry_count)

    async def generate_summary(self, state: GlobalState) -> str:
        """
        生成任务执行总结

        Args:
            state: 全局状态

        Returns:
            Markdown 格式的总结
        """
        try:
            logger.info("生成任务执行总结")

            # 准备提示词输入
            prompt_input = self._prepare_summary_input(state)

            # 调用 LLM 生成总结
            response = await self.llm.ainvoke(
                self.summary_generation_prompt.format_messages(**prompt_input)
            )

            summary = response.content.strip()

            logger.info("任务执行总结生成完成")
            return summary

        except Exception as e:
            logger.error(f"生成总结失败: {str(e)}")
            return self._generate_default_summary(state)

    # ========================================================================
    # 辅助方法
    # ========================================================================

    def _parse_task_plan(self, response: str) -> TaskPlan:
        """解析任务计划响应"""
        try:
            # 尝试提取 JSON
            data = self._extract_json(response)

            return TaskPlan(
                task_type=TaskType(data.get('task_type', 'full_weaving')),
                complexity=data.get('complexity', 'medium'),
                required_subgraphs=data.get('required_subgraphs', ['dissection_subgraph', 'review_subgraph']),
                execution_order=data.get('execution_order', ['dissection_subgraph', 'review_subgraph']),
                estimated_duration=data.get('estimated_duration', 60),
                special_requirements=data.get('special_requirements')
            )
        except Exception as e:
            logger.warning(f"解析任务计划失败: {str(e)}")
            return TaskPlan(
                task_type=TaskType.FULL_WEAVING,
                complexity="medium",
                required_subgraphs=["dissection_subgraph", "review_subgraph"],
                execution_order=["dissection_subgraph", "review_subgraph"],
                estimated_duration=60
            )

    def _prepare_routing_input(self, state: GlobalState) -> Dict[str, Any]:
        """准备路由决策的输入"""
        # 计算已完成和待执行的步骤
        completed_steps = []
        pending_steps = []

        if state.get('algorithm_explanation'):
            completed_steps.append("算法拆解")
        else:
            pending_steps.append("算法拆解")

        if state.get('detected_issues'):
            completed_steps.append("问题检测")
        else:
            pending_steps.append("问题检测")

        if state.get('optimization_suggestions'):
            completed_steps.append("优化建议")
        else:
            pending_steps.append("优化建议")

        return {
            "task_id": state['task_id'],
            "current_phase": state['current_phase'].value,
            "progress": int(state['progress'] * 100),
            "completed_steps": ", ".join(completed_steps) if completed_steps else "无",
            "pending_steps": ", ".join(pending_steps) if pending_steps else "无",
            "execution_history": self._format_execution_history(state),
            "algorithm_explanation": state.get('algorithm_explanation') is not None,
            "detected_issues_count": len(state.get('detected_issues', [])),
            "suggestions_count": len(state.get('optimization_suggestions', [])),
            "quality_score": state.get('shared_context', {}).get('quality_metrics', {}).get('overall_score', 0),
            "optimization_level": state['optimization_level'],
            "human_intervention_required": state.get('human_intervention_required', False)
        }

    def _parse_routing_decision(self, response: str) -> RoutingDecision:
        """解析路由决策响应"""
        try:
            data = self._extract_json(response)

            next_step_str = data.get('next_step', 'complete')
            next_step = NextStep(next_step_str) if next_step_str in [e.value for e in NextStep] else NextStep.COMPLETE

            return RoutingDecision(
                next_step=next_step,
                reason=data.get('reason', '默认决策'),
                requires_human_input=data.get('requires_human_input', False),
                estimated_duration=data.get('estimated_duration', 30)
            )
        except Exception as e:
            logger.warning(f"解析路由决策失败: {str(e)}")
            return RoutingDecision(
                next_step=NextStep.COMPLETE,
                reason="解析失败，使用默认决策",
                requires_human_input=False,
                estimated_duration=0
            )

    def _get_default_routing_decision(self, state: GlobalState) -> RoutingDecision:
        """获取默认路由决策"""
        # 根据当前阶段决定下一步
        current_phase = state['current_phase']

        if current_phase == Phase.ANALYSIS:
            return RoutingDecision(
                next_step=NextStep.DISSECTION_SUBGRAPH,
                reason="开始算法拆解",
                requires_human_input=False,
                estimated_duration=30
            )
        elif current_phase == Phase.DISSECTION:
            return RoutingDecision(
                next_step=NextStep.REVIEW_SUBGRAPH,
                reason="开始代码评审",
                requires_human_input=False,
                estimated_duration=30
            )
        else:
            return RoutingDecision(
                next_step=NextStep.COMPLETE,
                reason="任务完成",
                requires_human_input=False,
                estimated_duration=0
            )

    def _parse_coordination_result(self, response: str) -> CoordinationResult:
        """解析协调结果响应"""
        try:
            data = self._extract_json(response)

            mode_str = data.get('coordination_mode', 'master_expert')
            mode = CollaborationMode(mode_str) if mode_str in [e.value for e in CollaborationMode] else CollaborationMode.MASTER_EXPERT

            return CoordinationResult(
                coordination_mode=mode,
                final_decision=data.get('final_decision', '采用默认方案'),
                consensus_level=float(data.get('consensus_level', 100)),
                dissenting_opinions=data.get('dissenting_opinions', []),
                action_items=data.get('action_items', [])
            )
        except Exception as e:
            logger.warning(f"解析协调结果失败: {str(e)}")
            return CoordinationResult(
                coordination_mode=CollaborationMode.MASTER_EXPERT,
                final_decision="采用默认方案",
                consensus_level=100.0,
                dissenting_opinions=[],
                action_items=[]
            )

    def _parse_intervention_request(self, response: str) -> Dict[str, Any]:
        """解析人工干预请求响应"""
        try:
            return self._extract_json(response)
        except Exception as e:
            logger.warning(f"解析人工干预请求失败: {str(e)}")
            return {
                "intervention_type": "confirmation",
                "title": "需要确认",
                "description": "请确认是否继续",
                "options": []
            }

    def _parse_error_handling_plan(self, response: str, retry_count: int) -> ErrorHandlingPlan:
        """解析错误处理方案响应"""
        try:
            data = self._extract_json(response)

            strategy_str = data.get('recovery_strategy', 'retry')
            strategy = RecoveryStrategy(strategy_str) if strategy_str in [e.value for e in RecoveryStrategy] else RecoveryStrategy.RETRY

            return ErrorHandlingPlan(
                error_type=data.get('error_type', 'unknown'),
                severity=data.get('severity', 'medium'),
                recovery_strategy=strategy,
                retry_count=retry_count,
                max_retries=data.get('max_retries', self.max_retries),
                fallback_action=data.get('fallback_action', '中止任务'),
                user_message=data.get('user_message', '执行过程中出现错误')
            )
        except Exception as e:
            logger.warning(f"解析错误处理方案失败: {str(e)}")
            return self._get_default_error_handling_plan(Exception(response), retry_count)

    def _get_default_error_handling_plan(self, error: Exception, retry_count: int) -> ErrorHandlingPlan:
        """获取默认错误处理方案"""
        if retry_count < self.max_retries:
            strategy = RecoveryStrategy.RETRY
            fallback = "重试执行"
        else:
            strategy = RecoveryStrategy.ABORT
            fallback = "中止任务"

        return ErrorHandlingPlan(
            error_type=type(error).__name__,
            severity="medium",
            recovery_strategy=strategy,
            retry_count=retry_count,
            max_retries=self.max_retries,
            fallback_action=fallback,
            user_message=f"执行过程中出现错误: {str(error)}"
        )

    def _prepare_summary_input(self, state: GlobalState) -> Dict[str, Any]:
        """准备总结生成的输入"""
        duration = (state['updated_at'] - state['created_at']).total_seconds()

        return {
            "task_id": state['task_id'],
            "user_id": state['user_id'],
            "start_time": state['created_at'].isoformat(),
            "end_time": state['updated_at'].isoformat(),
            "duration": f"{int(duration)}秒",
            "execution_results": self._format_execution_results(state),
            "algorithm_analysis": self._format_algorithm_analysis(state),
            "code_optimization": self._format_code_optimization(state),
            "quality_metrics": json.dumps(state.get('shared_context', {}).get('quality_metrics', {}), ensure_ascii=False, indent=2),
            "user_interactions": self._format_user_interactions(state)
        }

    def _generate_default_summary(self, state: GlobalState) -> str:
        """生成默认总结"""
        return f"""# 任务执行总结

## 任务信息
- 任务ID: {state['task_id']}
- 状态: {state['status'].value}
- 进度: {int(state['progress'] * 100)}%

## 执行结果
任务已完成基本处理。

## 后续建议
请查看详细结果。
"""

    # 格式化辅助方法

    def _format_execution_history(self, state: GlobalState) -> str:
        """格式化执行历史"""
        history = []
        if state.get('algorithm_explanation'):
            history.append("- 完成算法拆解")
        if state.get('detected_issues'):
            history.append(f"- 检测到 {len(state['detected_issues'])} 个问题")
        if state.get('optimization_suggestions'):
            history.append(f"- 生成 {len(state['optimization_suggestions'])} 条优化建议")

        return "\n".join(history) if history else "无执行历史"

    def _describe_current_situation(self, state: GlobalState) -> str:
        """描述当前情况"""
        completed_tasks = []
        if state.get('algorithm_explanation'):
            completed_tasks.append("算法拆解")
        if state.get('detected_issues'):
            completed_tasks.append("问题检测")
        if state.get('optimization_suggestions'):
            completed_tasks.append("优化建议")

        completed_str = "、".join(completed_tasks) if completed_tasks else "无"

        return f"""当前任务处于 {state['current_phase'].value} 阶段，进度 {int(state['progress'] * 100)}%。
已完成: {completed_str}"""

    def _format_execution_results(self, state: GlobalState) -> str:
        """格式化执行结果"""
        results = []
        results.append(f"- 状态: {state['status'].value}")
        results.append(f"- 进度: {int(state['progress'] * 100)}%")
        results.append(f"- 代码版本: {len(state['code_versions'])} 个")

        return "\n".join(results)

    def _format_algorithm_analysis(self, state: GlobalState) -> str:
        """格式化算法分析"""
        if state.get('algorithm_explanation'):
            return "已完成算法分析和讲解"
        return "未进行算法分析"

    def _format_code_optimization(self, state: GlobalState) -> str:
        """格式化代码优化"""
        issues = len(state.get('detected_issues', []))
        suggestions = len(state.get('optimization_suggestions', []))

        return f"检测到 {issues} 个问题，生成 {suggestions} 条优化建议"

    def _format_user_interactions(self, state: GlobalState) -> str:
        """格式化用户交互"""
        decisions = len(state.get('decision_history', []))
        return f"用户做出 {decisions} 次决策"

    def _get_error_stack(self, error: Exception) -> str:
        """获取错误堆栈"""
        import traceback
        return traceback.format_exc()

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """从文本中提取 JSON"""
        # 尝试直接解析
        try:
            return json.loads(text)
        except:
            pass

        # 尝试提取 JSON 代码块
        import re
        json_pattern = r'```json\s*(.*?)\s*```'
        matches = re.findall(json_pattern, text, re.DOTALL)

        if matches:
            try:
                return json.loads(matches[0])
            except:
                pass

        # 尝试查找 JSON 对象
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, text, re.DOTALL)

        if matches:
            for match in matches:
                try:
                    return json.loads(match)
                except:
                    continue

        # 返回空字典
        return {}


# 节点函数定义（用于 LangGraph）

async def supervisor_analyze_task_node(state: GlobalState) -> GlobalState:
    """Supervisor 任务分析节点"""
    # 使用全局单例 LLM 实例
    from app.core.llm import get_llm_instance

    llm = get_llm_instance()
    supervisor = SupervisorAgent(llm)

    try:
        # 分析任务
        task_plan = await supervisor.analyze_task(state)

        # 更新状态
        state['shared_context']['task_plan'] = asdict(task_plan)
        state['status'] = StateTaskStatus.ANALYZING
        state['current_phase'] = Phase.ANALYSIS

        logger.info(f"任务分析完成: {task_plan.task_type}")

    except Exception as e:
        logger.error(f"任务分析节点执行失败: {str(e)}")
        state['last_error'] = str(e)

    return state


async def supervisor_routing_node(state: GlobalState) -> GlobalState:
    """Supervisor 路由决策节点"""
    # 使用全局单例 LLM 实例
    from app.core.llm import get_llm_instance

    llm = get_llm_instance()
    supervisor = SupervisorAgent(llm)

    try:
        # 路由决策
        decision = await supervisor.route_to_next_step(state)

        # 更新状态
        state['shared_context']['routing_decision'] = asdict(decision)

        logger.info(f"路由决策: {decision.next_step}")

    except Exception as e:
        logger.error(f"路由决策节点执行失败: {str(e)}")
        state['last_error'] = str(e)

    return state
