"""
主图 (Main Graph) 单元测试

测试主图的核心功能，包括图构建、节点执行、路由决策和 Human-in-the-loop 机制。
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from app.graph.state import (
    GlobalState,
    TaskStatus,
    Phase,
    CollaborationMode,
    AlgorithmExplanation,
    ExecutionStep,
    CodeIssue,
    IssueType,
    Severity
)
from app.graph.main_graph import (
    MainGraphBuilder,
    MainGraphManager,
    create_main_graph
)
from app.graph.supervisor.agent import NextStep


class TestMainGraphBuilder:
    """测试主图构建器"""

    @pytest.fixture
    def mock_llm(self):
        """创建模拟的 LLM"""
        llm = AsyncMock()
        llm.ainvoke = AsyncMock(return_value=Mock(
            content='{"task_type": "full_weaving", "complexity": "medium"}'
        ))
        return llm

    @pytest.fixture
    def builder(self, mock_llm):
        """创建主图构建器实例"""
        return MainGraphBuilder(llm=mock_llm)

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

    def test_builder_initialization(self, builder):
        """测试构建器初始化"""
        assert builder.llm is not None
        assert builder.checkpointer is not None
        assert builder.supervisor is not None
        assert builder.dissection_subgraph is not None
        assert builder.review_subgraph is not None

    def test_build_main_graph(self, builder):
        """测试主图构建"""
        graph = builder.build_main_graph()

        assert graph is not None
        assert builder.graph is not None

    def test_compile_main_graph(self, builder):
        """测试主图编译"""
        compiled_graph = builder.compile()

        assert compiled_graph is not None
        assert builder.compiled_graph is not None

    def test_route_next_step_with_error(self, builder, sample_state):
        """测试有错误时的路由决策"""
        sample_state["last_error"] = "测试错误"

        next_node = builder._route_next_step(sample_state)

        assert next_node == "handle_error"

    def test_route_next_step_with_human_intervention(self, builder, sample_state):
        """测试需要人工干预时的路由决策"""
        sample_state["human_intervention_required"] = True

        next_node = builder._route_next_step(sample_state)

        assert next_node == "human_intervention"

    def test_route_next_step_to_dissection(self, builder, sample_state):
        """测试路由到算法拆解子图"""
        sample_state["shared_context"]["routing_decision"] = {
            "next_step": NextStep.DISSECTION_SUBGRAPH
        }

        next_node = builder._route_next_step(sample_state)

        assert next_node == "dissection_subgraph"

    def test_route_next_step_to_review(self, builder, sample_state):
        """测试路由到代码评审子图"""
        sample_state["shared_context"]["routing_decision"] = {
            "next_step": NextStep.REVIEW_SUBGRAPH
        }

        next_node = builder._route_next_step(sample_state)

        assert next_node == "review_subgraph"

    def test_route_next_step_to_complete(self, builder, sample_state):
        """测试路由到完成节点"""
        sample_state["shared_context"]["routing_decision"] = {
            "next_step": NextStep.COMPLETE
        }

        next_node = builder._route_next_step(sample_state)

        assert next_node == "generate_summary"

    def test_route_next_step_default(self, builder, sample_state):
        """测试默认路由决策"""
        # 没有路由决策时，默认进入总结生成
        next_node = builder._route_next_step(sample_state)

        assert next_node == "generate_summary"

    @pytest.mark.asyncio
    async def test_call_dissection_subgraph(self, builder, sample_state):
        """测试调用算法拆解子图"""
        # Mock 子图执行结果
        mock_result = {
            "task_id": "test-task-1",
            "code": "def test(): pass",
            "language": "python",
            "analysis_phase": "completed",
            "execution_steps": [],
            "current_step": 0,
            "data_structures_used": [],
            "error_info": None
        }

        with patch.object(builder.dissection_subgraph, 'ainvoke', return_value=mock_result):
            result = await builder._call_dissection_subgraph(sample_state)

            assert result["current_phase"] == Phase.DISSECTION
            assert result["status"] == TaskStatus.ANALYZING

    @pytest.mark.asyncio
    async def test_call_review_subgraph(self, builder, sample_state):
        """测试调用代码评审子图"""
        # Mock 子图执行结果
        mock_result = {
            "task_id": "test-task-1",
            "code": "def test(): pass",
            "language": "python",
            "detected_issues": [],
            "optimization_suggestions": [],
            "iteration_count": 1,
            "quality_metrics": {"overall_score": 8.0},
            "error_info": None
        }

        with patch.object(builder.review_subgraph, 'ainvoke', return_value=mock_result):
            result = await builder._call_review_subgraph(sample_state)

            assert result["current_phase"] == Phase.REVIEW
            assert result["status"] == TaskStatus.OPTIMIZING

    @pytest.mark.asyncio
    async def test_human_intervention_node(self, builder, sample_state):
        """测试 Human-in-the-loop 节点"""
        # 设置待决策内容
        sample_state["pending_human_decision"] = {
            "intervention_type": "confirmation",
            "title": "确认优化",
            "description": "是否应用优化建议？",
            "options": [
                {"id": "yes", "label": "是"},
                {"id": "no", "label": "否"}
            ]
        }

        # Mock interrupt 函数返回用户决策
        with patch('app.graph.main_graph.interrupt', return_value={"action": "continue"}):
            result = await builder._human_intervention_node(sample_state)

            assert result["status"] == TaskStatus.ANALYZING
            assert result["human_intervention_required"] is False

    @pytest.mark.asyncio
    async def test_human_intervention_node_cancel(self, builder, sample_state):
        """测试用户取消任务"""
        sample_state["pending_human_decision"] = {
            "intervention_type": "confirmation",
            "title": "确认继续",
            "options": []
        }

        # Mock interrupt 函数返回取消决策
        with patch('app.graph.main_graph.interrupt', return_value={"action": "cancel"}):
            result = await builder._human_intervention_node(sample_state)

            assert result["status"] == TaskStatus.CANCELED

    @pytest.mark.asyncio
    async def test_generate_summary_node(self, builder, sample_state):
        """测试总结生成节点"""
        # Mock Supervisor 的 generate_summary 方法
        mock_summary = "# 任务执行总结\n\n任务已完成。"
        builder.supervisor.generate_summary = AsyncMock(return_value=mock_summary)

        result = await builder._generate_summary_node(sample_state)

        assert result["status"] == TaskStatus.COMPLETED
        assert result["progress"] == 1.0
        assert result["current_phase"] == Phase.REPORT_GENERATION
        assert result["shared_context"]["final_summary"] == mock_summary

    @pytest.mark.asyncio
    async def test_handle_error_node_retry(self, builder, sample_state):
        """测试错误处理节点 - 重试策略"""
        sample_state["last_error"] = "测试错误"
        sample_state["retry_count"] = 1

        # Mock Supervisor 的 handle_error 方法返回重试策略
        from app.graph.supervisor.agent import ErrorHandlingPlan, RecoveryStrategy
        mock_plan = ErrorHandlingPlan(
            error_type="RuntimeError",
            severity="medium",
            recovery_strategy=RecoveryStrategy.RETRY,
            retry_count=1,
            max_retries=3,
            fallback_action="重试执行",
            user_message="执行失败，正在重试"
        )
        builder.supervisor.handle_error = AsyncMock(return_value=mock_plan)

        result = await builder._handle_error_node(sample_state)

        assert result.get("last_error") is None
        assert result["retry_count"] == 2

    @pytest.mark.asyncio
    async def test_handle_error_node_abort(self, builder, sample_state):
        """测试错误处理节点 - 中止策略"""
        sample_state["last_error"] = "严重错误"
        sample_state["retry_count"] = 3

        # Mock Supervisor 的 handle_error 方法返回中止策略
        from app.graph.supervisor.agent import ErrorHandlingPlan, RecoveryStrategy
        mock_plan = ErrorHandlingPlan(
            error_type="RuntimeError",
            severity="critical",
            recovery_strategy=RecoveryStrategy.ABORT,
            retry_count=3,
            max_retries=3,
            fallback_action="中止任务",
            user_message="已达到最大重试次数"
        )
        builder.supervisor.handle_error = AsyncMock(return_value=mock_plan)

        result = await builder._handle_error_node(sample_state)

        assert result["status"] == TaskStatus.FAILED

    @pytest.mark.asyncio
    async def test_handle_error_node_human_intervention(self, builder, sample_state):
        """测试错误处理节点 - 人工介入策略"""
        sample_state["last_error"] = "需要人工决策的错误"

        # Mock Supervisor 的 handle_error 方法返回人工介入策略
        from app.graph.supervisor.agent import ErrorHandlingPlan, RecoveryStrategy
        mock_plan = ErrorHandlingPlan(
            error_type="RuntimeError",
            severity="high",
            recovery_strategy=RecoveryStrategy.HUMAN,
            retry_count=0,
            max_retries=3,
            fallback_action="请求人工介入",
            user_message="需要您的决策"
        )
        builder.supervisor.handle_error = AsyncMock(return_value=mock_plan)

        result = await builder._handle_error_node(sample_state)

        assert result["human_intervention_required"] is True
        assert "pending_human_decision" in result


class TestMainGraphManager:
    """测试主图管理器"""

    @pytest.fixture
    def mock_llm(self):
        """创建模拟的 LLM"""
        llm = AsyncMock()
        return llm

    @pytest.fixture
    def manager(self, mock_llm):
        """创建主图管理器实例"""
        return MainGraphManager(llm=mock_llm)

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

    def test_manager_initialization(self, manager):
        """测试管理器初始化"""
        assert manager.builder is not None
        assert manager.graph is not None


class TestFactoryFunctions:
    """测试工厂函数"""

    def test_create_main_graph(self):
        """测试创建主图工厂函数"""
        mock_llm = AsyncMock()
        graph = create_main_graph(llm=mock_llm)

        assert graph is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
