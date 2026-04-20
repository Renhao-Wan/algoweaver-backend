"""
Supervisor Agent 单元测试

测试 Supervisor Agent 的核心功能，包括任务分析、路由决策、智能体协调和错误处理。
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from app.graph.state import (
    GlobalState,
    TaskStatus,
    Phase,
    CollaborationMode
)
from app.graph.supervisor.agent import (
    SupervisorAgent,
    TaskType,
    NextStep,
    RecoveryStrategy,
    TaskPlan,
    RoutingDecision,
    CoordinationResult,
    ErrorHandlingPlan
)
from app.graph.supervisor.prompts import SupervisorPrompts


class TestSupervisorAgent:
    """测试 Supervisor Agent"""

    @pytest.fixture
    def mock_llm(self):
        """创建模拟的 LLM"""
        llm = AsyncMock()
        llm.ainvoke = AsyncMock(return_value=Mock(
            content='{"task_type": "full_weaving", "complexity": "medium", "required_subgraphs": ["dissection_subgraph", "review_subgraph"], "execution_order": ["dissection_subgraph", "review_subgraph"], "estimated_duration": 60}'
        ))
        return llm

    @pytest.fixture
    def supervisor(self, mock_llm):
        """创建 Supervisor Agent 实例"""
        return SupervisorAgent(mock_llm, max_retries=3)

    @pytest.fixture
    def sample_state(self):
        """创建示例全局状态"""
        return GlobalState(
            task_id="test-task-1",
            user_id="user-1",
            original_code="def test(): pass",
            language="python",
            optimization_level="balanced",
            status=TaskStatus.PENDING,
            current_phase=Phase.ANALYSIS,
            progress=0.0,
            collaboration_mode=CollaborationMode.MASTER_EXPERT,
            active_agents=[],
            code_versions=["def test(): pass"],
            decision_history=[],
            human_intervention_required=False,
            shared_context={},
            execution_metadata={},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            retry_count=0
        )

    @pytest.mark.asyncio
    async def test_analyze_task(self, supervisor, sample_state):
        """测试任务分析"""
        task_plan = await supervisor.analyze_task(sample_state)

        # 验证返回的任务计划
        assert isinstance(task_plan, TaskPlan)
        assert task_plan.task_type in [TaskType.ALGORITHM_DISSECTION, TaskType.CODE_REVIEW, TaskType.FULL_WEAVING]
        assert task_plan.complexity in ["simple", "medium", "complex"]
        assert len(task_plan.required_subgraphs) > 0
        assert len(task_plan.execution_order) > 0
        assert task_plan.estimated_duration > 0

    @pytest.mark.asyncio
    async def test_route_to_next_step(self, supervisor, sample_state):
        """测试路由决策"""
        # 设置 LLM 返回路由决策
        supervisor.llm.ainvoke = AsyncMock(return_value=Mock(
            content='{"next_step": "dissection_subgraph", "reason": "开始算法拆解", "requires_human_input": false, "estimated_duration": 30}'
        ))

        decision = await supervisor.route_to_next_step(sample_state)

        # 验证路由决策
        assert isinstance(decision, RoutingDecision)
        assert decision.next_step in [e for e in NextStep]
        assert isinstance(decision.reason, str)
        assert isinstance(decision.requires_human_input, bool)
        assert decision.estimated_duration >= 0

    @pytest.mark.asyncio
    async def test_route_with_human_intervention(self, supervisor, sample_state):
        """测试需要人工干预时的路由"""
        sample_state['human_intervention_required'] = True

        decision = await supervisor.route_to_next_step(sample_state)

        # 应该返回人工干预决策
        assert decision.next_step == NextStep.HUMAN_INTERVENTION
        assert decision.requires_human_input is True

    @pytest.mark.asyncio
    async def test_coordinate_agents(self, supervisor):
        """测试智能体协调"""
        # 设置 LLM 返回协调结果
        supervisor.llm.ainvoke = AsyncMock(return_value=Mock(
            content='{"coordination_mode": "master_expert", "final_decision": "采用方案A", "consensus_level": 85.0, "dissenting_opinions": [], "action_items": ["执行方案A"]}'
        ))

        scenario = "代码优化方案选择"
        agents_info = {"agent1": "建议方案A", "agent2": "建议方案B"}
        opinions = {"agent1": "方案A更高效", "agent2": "方案B更安全"}
        conflicts = ["性能 vs 安全"]

        result = await supervisor.coordinate_agents(scenario, agents_info, opinions, conflicts)

        # 验证协调结果
        assert isinstance(result, CoordinationResult)
        assert result.coordination_mode in [e for e in CollaborationMode]
        assert isinstance(result.final_decision, str)
        assert 0 <= result.consensus_level <= 100
        assert isinstance(result.dissenting_opinions, list)
        assert isinstance(result.action_items, list)

    @pytest.mark.asyncio
    async def test_handle_human_intervention(self, supervisor, sample_state):
        """测试人工干预处理"""
        # 设置 LLM 返回干预请求
        supervisor.llm.ainvoke = AsyncMock(return_value=Mock(
            content='{"intervention_type": "confirmation", "title": "确认优化", "description": "是否应用优化建议？", "options": [{"id": "yes", "label": "是"}, {"id": "no", "label": "否"}], "default_option": "yes"}'
        ))

        reason = "需要确认优化建议"
        options = [
            {"id": "yes", "label": "是", "description": "应用所有优化建议"},
            {"id": "no", "label": "否", "description": "不应用优化建议"}
        ]

        request = await supervisor.handle_human_intervention(sample_state, reason, options)

        # 验证干预请求
        assert isinstance(request, dict)
        assert "intervention_type" in request
        assert "title" in request
        assert "description" in request
        assert "options" in request

    @pytest.mark.asyncio
    async def test_handle_error(self, supervisor):
        """测试错误处理"""
        # 设置 LLM 返回错误处理方案
        supervisor.llm.ainvoke = AsyncMock(return_value=Mock(
            content='{"error_type": "RuntimeError", "severity": "medium", "recovery_strategy": "retry", "retry_count": 1, "max_retries": 3, "fallback_action": "重试执行", "user_message": "执行失败，正在重试"}'
        ))

        error = RuntimeError("测试错误")
        context = {"node_name": "test_node", "phase": "testing"}
        retry_count = 1

        plan = await supervisor.handle_error(error, context, retry_count)

        # 验证错误处理方案
        assert isinstance(plan, ErrorHandlingPlan)
        assert plan.error_type in ["RuntimeError", "unknown"]
        assert plan.severity in ["low", "medium", "high", "critical"]
        assert plan.recovery_strategy in [e for e in RecoveryStrategy]
        assert plan.retry_count == retry_count
        assert plan.max_retries >= retry_count

    @pytest.mark.asyncio
    async def test_handle_error_max_retries(self, supervisor):
        """测试达到最大重试次数时的错误处理"""
        # 设置 LLM 返回中止策略
        supervisor.llm.ainvoke = AsyncMock(return_value=Mock(
            content='{"error_type": "RuntimeError", "severity": "high", "recovery_strategy": "abort", "retry_count": 3, "max_retries": 3, "fallback_action": "中止任务", "user_message": "已达到最大重试次数"}'
        ))

        error = RuntimeError("测试错误")
        context = {"node_name": "test_node", "phase": "testing"}
        retry_count = 3  # 达到最大重试次数

        plan = await supervisor.handle_error(error, context, retry_count)

        # 验证错误处理方案
        assert isinstance(plan, ErrorHandlingPlan)
        assert plan.retry_count == 3
        assert plan.max_retries == 3

    @pytest.mark.asyncio
    async def test_generate_summary(self, supervisor, sample_state):
        """测试总结生成"""
        # 添加一些执行结果
        sample_state['status'] = TaskStatus.COMPLETED
        sample_state['progress'] = 1.0
        sample_state['algorithm_explanation'] = Mock()
        sample_state['detected_issues'] = [Mock(), Mock()]
        sample_state['optimization_suggestions'] = [Mock()]

        # 设置 LLM 返回总结
        supervisor.llm.ainvoke = AsyncMock(return_value=Mock(
            content="# 任务执行总结\n\n任务已成功完成。"
        ))

        summary = await supervisor.generate_summary(sample_state)

        # 验证总结
        assert isinstance(summary, str)
        assert len(summary) > 0

    def test_parse_task_plan(self, supervisor):
        """测试任务计划解析"""
        response = '{"task_type": "algorithm_dissection", "complexity": "simple", "required_subgraphs": ["dissection_subgraph"], "execution_order": ["dissection_subgraph"], "estimated_duration": 30}'

        plan = supervisor._parse_task_plan(response)

        assert plan.task_type == TaskType.ALGORITHM_DISSECTION
        assert plan.complexity == "simple"
        assert "dissection_subgraph" in plan.required_subgraphs

    def test_parse_routing_decision(self, supervisor):
        """测试路由决策解析"""
        response = '{"next_step": "review_subgraph", "reason": "开始代码评审", "requires_human_input": false, "estimated_duration": 25}'

        decision = supervisor._parse_routing_decision(response)

        assert decision.next_step == NextStep.REVIEW_SUBGRAPH
        assert decision.reason == "开始代码评审"
        assert decision.requires_human_input is False

    def test_get_default_routing_decision(self, supervisor, sample_state):
        """测试默认路由决策"""
        # 测试分析阶段
        sample_state['current_phase'] = Phase.ANALYSIS
        decision = supervisor._get_default_routing_decision(sample_state)
        assert decision.next_step == NextStep.DISSECTION_SUBGRAPH

        # 测试拆解阶段
        sample_state['current_phase'] = Phase.DISSECTION
        decision = supervisor._get_default_routing_decision(sample_state)
        assert decision.next_step == NextStep.REVIEW_SUBGRAPH

        # 测试其他阶段（如报告生成）
        sample_state['current_phase'] = Phase.REPORT_GENERATION
        decision = supervisor._get_default_routing_decision(sample_state)
        assert decision.next_step == NextStep.COMPLETE

    def test_extract_json(self, supervisor):
        """测试 JSON 提取"""
        # 测试直接 JSON
        text1 = '{"key": "value"}'
        result1 = supervisor._extract_json(text1)
        assert result1 == {"key": "value"}

        # 测试 JSON 代码块
        text2 = '```json\n{"key": "value"}\n```'
        result2 = supervisor._extract_json(text2)
        assert result2 == {"key": "value"}

        # 测试嵌入的 JSON
        text3 = '这是一些文本 {"key": "value"} 更多文本'
        result3 = supervisor._extract_json(text3)
        assert result3 == {"key": "value"}

        # 测试无效 JSON
        text4 = '这是纯文本，没有 JSON'
        result4 = supervisor._extract_json(text4)
        assert result4 == {}


class TestSupervisorPrompts:
    """测试 Supervisor 提示词"""

    def test_get_task_analysis_prompt(self):
        """测试任务分析提示词"""
        prompt = SupervisorPrompts.get_task_analysis_prompt()
        assert prompt is not None

        # 测试格式化
        formatted = prompt.format_messages(
            user_id="user-1",
            task_id="task-1",
            code="def test(): pass",
            language="python",
            optimization_level="balanced",
            custom_requirements="无"
        )
        assert len(formatted) > 0

    def test_get_routing_decision_prompt(self):
        """测试路由决策提示词"""
        prompt = SupervisorPrompts.get_routing_decision_prompt()
        assert prompt is not None

    def test_get_coordination_prompt(self):
        """测试智能体协调提示词"""
        prompt = SupervisorPrompts.get_coordination_prompt()
        assert prompt is not None

    def test_get_human_intervention_prompt(self):
        """测试人工干预提示词"""
        prompt = SupervisorPrompts.get_human_intervention_prompt()
        assert prompt is not None

    def test_get_error_handling_prompt(self):
        """测试错误处理提示词"""
        prompt = SupervisorPrompts.get_error_handling_prompt()
        assert prompt is not None

    def test_get_summary_generation_prompt(self):
        """测试总结生成提示词"""
        prompt = SupervisorPrompts.get_summary_generation_prompt()
        assert prompt is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
