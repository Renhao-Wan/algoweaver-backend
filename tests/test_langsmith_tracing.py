"""
LangSmith 追踪集成测试

验证 LangSmith 追踪功能是否正常工作
"""
import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from app.core.logger import (
    log_agent_execution,
    log_graph_execution,
    LangSmithHandler,
    get_logger
)


class TestLangSmithTracing:
    """LangSmith 追踪功能测试"""

    def test_log_agent_execution_basic(self):
        """测试基本的智能体执行日志"""
        # 不应该抛出异常
        log_agent_execution(
            agent_name="test_agent",
            agent_type="supervisor",
            phase="test_phase",
            task_id="test_task_123"
        )

    def test_log_agent_execution_with_details(self):
        """测试带详细信息的智能体执行日志"""
        log_agent_execution(
            agent_name="test_agent",
            agent_type="dissection",
            phase="step_simulation",
            task_id="test_task_123",
            inputs={"code": "print('hello')"},
            outputs={"result": "success"},
            duration_ms=150.5,
            trace_id="trace_123",
            span_id="span_456"
        )

    def test_log_agent_execution_with_error(self):
        """测试带错误信息的智能体执行日志"""
        log_agent_execution(
            agent_name="test_agent",
            agent_type="review",
            phase="mistake_detection",
            task_id="test_task_123",
            error="Test error message",
            duration_ms=50.0
        )

    def test_log_graph_execution_basic(self):
        """测试基本的图执行日志"""
        log_graph_execution(
            graph_name="main_graph",
            node_name="test_node",
            task_id="test_task_123"
        )

    def test_log_graph_execution_with_state(self):
        """测试带状态快照的图执行日志"""
        log_graph_execution(
            graph_name="dissection_subgraph",
            node_name="step_simulator",
            task_id="test_task_123",
            state_snapshot={
                "phase": "dissection",
                "progress": 0.5
            },
            duration_ms=200.0,
            trace_id="trace_123",
            span_id="span_456"
        )

    def test_log_graph_execution_with_error(self):
        """测试带错误的图执行日志"""
        log_graph_execution(
            graph_name="review_subgraph",
            node_name="validation_tester",
            task_id="test_task_123",
            error="Validation failed",
            duration_ms=100.0
        )

    @patch('app.core.logger.settings')
    def test_langsmith_handler_disabled(self, mock_settings):
        """测试 LangSmith 处理器禁用时的行为"""
        mock_settings.langsmith_tracing = False
        mock_settings.langsmith_api_key = None

        handler = LangSmithHandler()
        assert handler.langsmith_client is None

    @patch('app.core.logger.settings')
    @patch('langsmith.Client')
    def test_langsmith_handler_enabled(self, mock_client_class, mock_settings):
        """测试 LangSmith 处理器启用时的行为"""
        mock_settings.langsmith_tracing = True
        mock_settings.langsmith_api_key = "test_key"
        mock_settings.langsmith_endpoint = "https://api.smith.langchain.com"
        mock_settings.langsmith_project = "test_project"

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        handler = LangSmithHandler()
        assert handler.langsmith_client is not None

    @patch('app.core.logger.settings')
    @patch('langsmith.Client')
    def test_langsmith_handler_emit(self, mock_client_class, mock_settings):
        """测试 LangSmith 处理器发送日志"""
        mock_settings.langsmith_tracing = True
        mock_settings.langsmith_api_key = "test_key"
        mock_settings.langsmith_endpoint = "https://api.smith.langchain.com"
        mock_settings.langsmith_project = "test_project"

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        handler = LangSmithHandler()

        # 创建日志记录
        logger = get_logger(__name__)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.agent_name = "test_agent"
        record.task_id = "test_task_123"

        # 发送日志
        handler.emit(record)

        # 验证 create_run 被调用
        mock_client.create_run.assert_called_once()

    def test_trace_context_propagation(self):
        """测试追踪上下文传播"""
        trace_id = "trace_123"
        span_id = "span_456"
        parent_span_id = "parent_789"

        # 记录带追踪上下文的日志
        log_agent_execution(
            agent_name="test_agent",
            agent_type="supervisor",
            phase="routing",
            task_id="test_task_123",
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id
        )

        # 验证不抛出异常即可


class TestTracingIntegration:
    """追踪集成测试"""

    def test_multiple_agent_executions(self):
        """测试多个智能体执行的追踪"""
        task_id = "test_task_123"
        trace_id = "trace_123"

        # 模拟多个智能体执行
        agents = [
            ("supervisor", "supervisor", "analyze_task"),
            ("step_simulator", "dissection", "simulate_steps"),
            ("visual_generator", "dissection", "generate_visuals"),
            ("mistake_detector", "review", "detect_mistakes"),
            ("suggestion_generator", "review", "generate_suggestions")
        ]

        for agent_name, agent_type, phase in agents:
            log_agent_execution(
                agent_name=agent_name,
                agent_type=agent_type,
                phase=phase,
                task_id=task_id,
                trace_id=trace_id,
                span_id=f"span_{agent_name}"
            )

    def test_graph_execution_flow(self):
        """测试图执行流程的追踪"""
        task_id = "test_task_123"
        trace_id = "trace_123"

        # 模拟图执行流程
        nodes = [
            ("main_graph", "supervisor_analyze_task"),
            ("main_graph", "dissection_subgraph"),
            ("dissection_subgraph", "step_simulator"),
            ("dissection_subgraph", "visual_generator"),
            ("main_graph", "review_subgraph"),
            ("review_subgraph", "mistake_detector"),
            ("main_graph", "generate_summary")
        ]

        for graph_name, node_name in nodes:
            log_graph_execution(
                graph_name=graph_name,
                node_name=node_name,
                task_id=task_id,
                trace_id=trace_id,
                span_id=f"span_{node_name}"
            )

    def test_error_tracking(self):
        """测试错误追踪"""
        task_id = "test_task_123"
        trace_id = "trace_123"

        # 记录正常执行
        log_agent_execution(
            agent_name="test_agent",
            agent_type="supervisor",
            phase="start",
            task_id=task_id,
            trace_id=trace_id,
            span_id="span_1"
        )

        # 记录错误
        log_agent_execution(
            agent_name="test_agent",
            agent_type="supervisor",
            phase="error",
            task_id=task_id,
            error="Test error occurred",
            trace_id=trace_id,
            span_id="span_2"
        )

        # 记录恢复
        log_agent_execution(
            agent_name="test_agent",
            agent_type="supervisor",
            phase="recovery",
            task_id=task_id,
            trace_id=trace_id,
            span_id="span_3"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
