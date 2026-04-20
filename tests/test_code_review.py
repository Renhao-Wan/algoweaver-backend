"""
代码评审子图单元测试

测试代码评审子图的核心功能，包括问题检测、建议生成和验证测试。
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from app.graph.state import ReviewState, CodeIssue, Suggestion, IssueType, Severity
from app.graph.subgraphs.review.agents import (
    MistakeDetectorAgent,
    SuggestionGeneratorAgent,
    ValidationTesterAgent,
    ReviewPhase
)
from app.graph.subgraphs.review.builder import (
    ReviewSubgraphBuilder,
    ReviewSubgraphManager
)
from app.graph.state import StateConverter


class TestMistakeDetectorAgent:
    """测试问题检测智能体"""

    @pytest.fixture
    def mock_llm(self):
        """创建模拟的 LLM"""
        llm = AsyncMock()
        llm.ainvoke = AsyncMock(return_value=Mock(content="检测到性能问题"))
        return llm

    @pytest.fixture
    def mock_sandbox(self):
        """创建模拟的沙箱"""
        sandbox = Mock()
        sandbox.execute_code = AsyncMock(return_value=Mock(
            status="success",
            output="执行成功"
        ))
        return sandbox

    @pytest.fixture
    def detector_agent(self, mock_llm, mock_sandbox):
        """创建问题检测智能体实例"""
        return MistakeDetectorAgent(mock_llm, mock_sandbox)

    @pytest.mark.asyncio
    async def test_detect_code_issues_basic(self, detector_agent):
        """测试基本的问题检测功能"""
        state = ReviewState(
            task_id="test-task-1",
            code="def test(): pass",
            language="python",
            optimization_level="balanced",
            review_phase=ReviewPhase.DETECTION.value,
            review_round=1,
            detected_issues=[],
            issue_categories={},
            generated_suggestions=[],
            validated_suggestions=[],
            rejected_suggestions=[],
            negotiation_rounds=0,
            consensus_reached=False,
            conflicting_suggestions=[],
            improved_code_versions=[],
            current_code_version=0,
            quality_threshold=7.0,
            validation_results=[],
            test_cases_passed=0,
            test_cases_failed=0,
            detection_errors=[],
            suggestion_errors=[],
            validation_errors=[]
        )

        result = await detector_agent.detect_code_issues(state)

        # 验证状态更新
        assert result['review_phase'] == ReviewPhase.SUGGESTION.value
        assert isinstance(result['detected_issues'], list)
        assert isinstance(result['issue_categories'], dict)

    @pytest.mark.asyncio
    async def test_static_code_analysis_syntax_error(self, detector_agent):
        """测试静态代码分析 - 语法错误检测"""
        code_with_syntax_error = "def test( pass"

        issues = await detector_agent._static_code_analysis(code_with_syntax_error, "python")

        # 应该检测到语法错误
        assert len(issues) > 0
        assert any(issue.type == IssueType.LOGIC_ERROR for issue in issues)
        assert any(issue.severity == Severity.CRITICAL for issue in issues)


class TestSuggestionGeneratorAgent:
    """测试建议生成智能体"""

    @pytest.fixture
    def mock_llm(self):
        """创建模拟的 LLM"""
        llm = AsyncMock()
        llm.ainvoke = AsyncMock(return_value=Mock(
            content="```python\ndef improved_test():\n    return True\n```"
        ))
        return llm

    @pytest.fixture
    def generator_agent(self, mock_llm):
        """创建建议生成智能体实例"""
        return SuggestionGeneratorAgent(mock_llm)

    @pytest.mark.asyncio
    async def test_generate_suggestions_no_issues(self, generator_agent):
        """测试无问题时的建议生成"""
        state = ReviewState(
            task_id="test-task-2",
            code="def test(): return True",
            language="python",
            optimization_level="balanced",
            review_phase=ReviewPhase.SUGGESTION.value,
            review_round=1,
            detected_issues=[],  # 无问题
            issue_categories={},
            generated_suggestions=[],
            validated_suggestions=[],
            rejected_suggestions=[],
            negotiation_rounds=0,
            consensus_reached=False,
            conflicting_suggestions=[],
            improved_code_versions=[],
            current_code_version=0,
            quality_threshold=7.0,
            validation_results=[],
            test_cases_passed=0,
            test_cases_failed=0,
            detection_errors=[],
            suggestion_errors=[],
            validation_errors=[]
        )

        result = await generator_agent.generate_suggestions(state)

        # 无问题时应该直接完成
        assert result['review_phase'] == ReviewPhase.COMPLETED.value
        assert result['consensus_reached'] is True

    @pytest.mark.asyncio
    async def test_generate_suggestions_with_issues(self, generator_agent):
        """测试有问题时的建议生成"""
        test_issue = CodeIssue(
            issue_id="issue-1",
            type=IssueType.PERFORMANCE,
            severity=Severity.MEDIUM,
            line_number=1,
            description="性能可以优化",
            suggestion="使用更高效的算法",
            example_fix="def optimized(): pass"
        )

        state = ReviewState(
            task_id="test-task-3",
            code="def test(): pass",
            language="python",
            optimization_level="balanced",
            review_phase=ReviewPhase.SUGGESTION.value,
            review_round=1,
            detected_issues=[test_issue],
            issue_categories={"performance": 1},
            generated_suggestions=[],
            validated_suggestions=[],
            rejected_suggestions=[],
            negotiation_rounds=0,
            consensus_reached=False,
            conflicting_suggestions=[],
            improved_code_versions=[],
            current_code_version=0,
            quality_threshold=7.0,
            validation_results=[],
            test_cases_passed=0,
            test_cases_failed=0,
            detection_errors=[],
            suggestion_errors=[],
            validation_errors=[]
        )

        result = await generator_agent.generate_suggestions(state)

        # 应该生成建议
        assert result['review_phase'] == ReviewPhase.VALIDATION.value
        assert len(result['generated_suggestions']) > 0
        assert len(result['improved_code_versions']) > 0


class TestValidationTesterAgent:
    """测试验证测试智能体"""

    @pytest.fixture
    def mock_llm(self):
        """创建模拟的 LLM"""
        llm = AsyncMock()
        llm.ainvoke = AsyncMock(return_value=Mock(
            content='{"readability": 8.0, "maintainability": 7.5, "performance": 8.5, "security": 7.0, "best_practices": 8.0}'
        ))
        return llm

    @pytest.fixture
    def mock_sandbox(self):
        """创建模拟的沙箱"""
        sandbox = Mock()
        sandbox.execute_code = AsyncMock(return_value=Mock(
            status="success",
            output="执行成功"
        ))
        return sandbox

    @pytest.fixture
    def validator_agent(self, mock_llm, mock_sandbox):
        """创建验证测试智能体实例"""
        return ValidationTesterAgent(mock_llm, mock_sandbox)

    @pytest.mark.asyncio
    async def test_validate_improvements_no_code(self, validator_agent):
        """测试无改进代码时的验证"""
        state = ReviewState(
            task_id="test-task-4",
            code="def test(): pass",
            language="python",
            optimization_level="balanced",
            review_phase=ReviewPhase.VALIDATION.value,
            review_round=1,
            detected_issues=[],
            issue_categories={},
            generated_suggestions=[],
            validated_suggestions=[],
            rejected_suggestions=[],
            negotiation_rounds=0,
            consensus_reached=False,
            conflicting_suggestions=[],
            improved_code_versions=[],  # 无改进代码
            current_code_version=0,
            quality_threshold=7.0,
            validation_results=[],
            test_cases_passed=0,
            test_cases_failed=0,
            detection_errors=[],
            suggestion_errors=[],
            validation_errors=[]
        )

        result = await validator_agent.validate_improvements(state)

        # 无改进代码时应该直接完成
        assert result['review_phase'] == ReviewPhase.COMPLETED.value


class TestReviewSubgraphBuilder:
    """测试代码评审子图构建器"""

    def test_build_review_subgraph(self):
        """测试子图构建"""
        builder = ReviewSubgraphBuilder(max_review_rounds=3)
        graph = builder.build_review_subgraph()

        # 验证图已创建
        assert graph is not None
        assert builder.graph is not None

    def test_compile_subgraph(self):
        """测试子图编译"""
        builder = ReviewSubgraphBuilder(max_review_rounds=3)
        builder.build_review_subgraph()
        compiled_graph = builder.compile_subgraph()

        # 验证编译成功
        assert compiled_graph is not None
        assert builder.compiled_graph is not None


class TestReviewSubgraphManager:
    """测试代码评审子图管理器"""

    def test_initialize_subgraph(self):
        """测试子图初始化"""
        manager = ReviewSubgraphManager(max_review_rounds=3)
        compiled_graph = manager.initialize_subgraph()

        # 验证初始化成功
        assert compiled_graph is not None
        assert manager.compiled_subgraph is not None

    def test_get_subgraph_info(self):
        """测试获取子图信息"""
        manager = ReviewSubgraphManager(max_review_rounds=3)
        manager.initialize_subgraph()

        info = manager.get_subgraph_info()

        # 验证信息完整
        assert info['name'] == "code_review_subgraph"
        assert info['collaboration_mode'] == "adversarial"
        assert info['max_review_rounds'] == 3
        assert info['initialized'] is True
        assert len(info['nodes']) > 0


class TestStateConversion:
    """测试状态转换函数"""

    def test_convert_global_to_review_state(self):
        """测试全局状态到评审状态的转换"""
        from app.graph.state import GlobalState, TaskStatus, Phase, CollaborationMode
        from datetime import datetime

        global_state = GlobalState(
            task_id="test-task-5",
            user_id="user-1",
            original_code="def test(): pass",
            language="python",
            optimization_level="balanced",
            status=TaskStatus.ANALYZING,
            current_phase=Phase.REVIEW,
            progress=0.5,
            collaboration_mode=CollaborationMode.ADVERSARIAL,
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

        review_state = StateConverter.global_to_review(global_state)

        # 验证转换正确
        assert review_state['task_id'] == "test-task-5"
        assert review_state['code'] == "def test(): pass"
        assert review_state['language'] == "python"
        assert review_state['optimization_level'] == "balanced"
        assert review_state['review_phase'] == ReviewPhase.DETECTION.value
        assert review_state['review_round'] == 1

    def test_merge_review_to_global_state(self):
        """测试评审状态到全局状态的合并"""
        from app.graph.state import GlobalState, TaskStatus, Phase, CollaborationMode
        from datetime import datetime

        global_state = GlobalState(
            task_id="test-task-6",
            user_id="user-1",
            original_code="def test(): pass",
            language="python",
            optimization_level="balanced",
            status=TaskStatus.ANALYZING,
            current_phase=Phase.REVIEW,
            progress=0.5,
            collaboration_mode=CollaborationMode.ADVERSARIAL,
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

        review_state = ReviewState(
            task_id="test-task-6",
            code="def test(): pass",
            language="python",
            optimization_level="balanced",
            review_phase=ReviewPhase.COMPLETED.value,
            review_round=2,
            detected_issues=[],
            issue_categories={},
            generated_suggestions=[],
            validated_suggestions=[],
            rejected_suggestions=[],
            negotiation_rounds=1,
            consensus_reached=True,
            conflicting_suggestions=[],
            improved_code_versions=["def improved_test(): return True"],
            current_code_version=0,
            quality_threshold=7.0,
            quality_metrics={"overall_score": 8.5, "readability": 9.0},  # 添加质量指标
            validation_results=[],
            test_cases_passed=3,
            test_cases_failed=0,
            detection_errors=[],
            suggestion_errors=[],
            validation_errors=[]
        )

        updated_global_state = StateConverter.review_to_global(global_state, review_state)

        # 验证合并正确
        assert len(updated_global_state['code_versions']) == 2
        assert updated_global_state['code_versions'][-1] == "def improved_test(): return True"
        # 新的StateConverter将quality_metrics存储在shared_context的review_result中
        assert 'review_result' in updated_global_state['shared_context']
        assert 'quality_metrics' in updated_global_state['shared_context']['review_result']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
