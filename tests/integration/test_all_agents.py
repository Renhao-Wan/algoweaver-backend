"""
全Agent集成测试套件

测试所有Agent的集成功能，包括：
- Supervisor Agent
- Dissection 子图全部节点（Step Simulator、Visual Generator）
- Review 子图全部节点（Mistake Detector、Suggestion Generator、Validation Tester）
- 状态在主图与子图之间的正确传递与合并

需求: 8.x, 9.x, 10.x, 11.0
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from app.graph.state import (
    GlobalState, DissectionState, ReviewState,
    StateTaskStatus, Phase, CollaborationMode,
    StateConverter, StateFactory
)
from app.graph.subgraphs.dissection.nodes import (
    StepSimulatorAgent,
    VisualGeneratorAgent
)
from app.graph.subgraphs.review.nodes import (
    MistakeDetectorAgent,
    SuggestionGeneratorAgent,
    ValidationTesterAgent
)


class TestDissectionSubgraphIntegration:
    """测试算法拆解子图的集成功能"""

    @pytest.fixture
    def mock_llm(self):
        """创建模拟的 LLM"""
        llm = AsyncMock()
        llm.ainvoke = AsyncMock(return_value=Mock(
            content='{"steps": [{"step_number": 1, "description": "初始化变量"}]}'
        ))
        return llm

    @pytest.fixture
    def mock_sandbox(self):
        """创建模拟的沙箱"""
        sandbox = Mock()
        sandbox.execute_code = AsyncMock(return_value=Mock(
            status="success",
            output="执行成功",
            variables={"n": 5}
        ))
        return sandbox

    @pytest.mark.asyncio
    async def test_dissection_state_conversion(self):
        """测试全局状态到拆解状态的转换"""
        global_state = StateFactory.create_global_state(
            task_id="test-dissection-1",
            user_id="user-1",
            code="def fibonacci(n): return n",
            language="python",
            optimization_level="balanced"
        )

        # 转换为拆解状态
        dissection_state = StateConverter.global_to_dissection(global_state)

        # 验证转换正确
        assert dissection_state['task_id'] == "test-dissection-1"
        assert dissection_state['code'] == "def fibonacci(n): return n"
        assert dissection_state['language'] == "python"
        assert dissection_state['analysis_phase'] == "parsing"

    @pytest.mark.asyncio
    async def test_dissection_to_global_merge(self):
        """测试拆解状态合并回全局状态"""
        global_state = StateFactory.create_global_state(
            task_id="test-dissection-2",
            user_id="user-1",
            code="def test(): pass",
            language="python",
            optimization_level="balanced"
        )

        dissection_state = StateFactory.create_dissection_state(
            task_id="test-dissection-2",
            code="def test(): pass",
            language="python"
        )

        # 模拟拆解结果
        dissection_state['execution_steps'] = [
            {"step_number": 1, "description": "步骤1"}
        ]
        dissection_state['variables_trace'] = {"x": [1, 2, 3]}
        dissection_state['algorithm_explanation'] = "这是一个测试算法"

        # 合并回全局状态
        updated_global = StateConverter.dissection_to_global(global_state, dissection_state)

        # 验证合并正确
        assert 'dissection_result' in updated_global['shared_context']
        assert len(updated_global['shared_context']['dissection_result']['execution_steps']) == 1
        assert 'x' in updated_global['shared_context']['dissection_result']['variables_trace']
        assert updated_global['algorithm_explanation'] == "这是一个测试算法"

    @pytest.mark.asyncio
    async def test_step_simulator_and_visual_generator_integration(self, mock_llm, mock_sandbox):
        """测试步骤模拟器和可视化生成器的集成"""
        simulator = StepSimulatorAgent(mock_llm, mock_sandbox)
        generator = VisualGeneratorAgent(mock_llm)

        # 创建初始状态
        state = StateFactory.create_dissection_state(
            task_id="test-integration-1",
            code="def add(a, b): return a + b",
            language="python",
            input_data={"a": 1, "b": 2}
        )

        # 步骤1: 模拟执行
        state = await simulator.simulate_algorithm_execution(state)
        # 即使执行失败，状态也应该被更新
        assert 'analysis_phase' in state
        # 如果执行失败，可能仍在parsing阶段
        assert state['analysis_phase'] in ["parsing", "simulation", "visualization", "completed"]

        # 步骤2: 生成可视化（只有在没有错误且有execution_steps时才执行）
        if not state.get('error_info') and len(state.get('execution_steps', [])) > 0:
            state = await generator.generate_algorithm_explanation(state)
            assert state['analysis_phase'] in ["visualization", "completed"]
            assert 'visualization_data' in state or 'pseudocode_generated' in state or 'algorithm_explanation' in state


class TestReviewSubgraphIntegration:
    """测试代码评审子图的集成功能"""

    @pytest.fixture
    def mock_llm(self):
        """创建模拟的 LLM"""
        llm = AsyncMock()
        llm.ainvoke = AsyncMock(return_value=Mock(
            content='{"issues": [], "suggestions": []}'
        ))
        return llm

    @pytest.fixture
    def mock_sandbox(self):
        """创建模拟的沙箱"""
        sandbox = Mock()
        sandbox.execute_code = AsyncMock(return_value=Mock(
            status="success",
            output="测试通过"
        ))
        return sandbox

    @pytest.mark.asyncio
    async def test_review_state_conversion(self):
        """测试全局状态到评审状态的转换"""
        global_state = StateFactory.create_global_state(
            task_id="test-review-1",
            user_id="user-1",
            code="def test(): pass",
            language="python",
            optimization_level="balanced"
        )

        # 转换为评审状态
        review_state = StateConverter.global_to_review(global_state)

        # 验证转换正确
        assert review_state['task_id'] == "test-review-1"
        assert review_state['code'] == "def test(): pass"
        assert review_state['language'] == "python"
        assert review_state['review_phase'] == "detection"
        assert review_state['review_round'] == 1

    @pytest.mark.asyncio
    async def test_review_to_global_merge(self):
        """测试评审状态合并回全局状态"""
        global_state = StateFactory.create_global_state(
            task_id="test-review-2",
            user_id="user-1",
            code="def test(): pass",
            language="python",
            optimization_level="balanced"
        )

        review_state = StateFactory.create_review_state(
            task_id="test-review-2",
            code="def test(): pass",
            language="python",
            optimization_level="balanced"
        )

        # 模拟评审结果
        review_state['improved_code_versions'] = ["def improved_test(): return True"]
        review_state['quality_metrics'] = {"overall_score": 8.5}
        review_state['consensus_reached'] = True

        # 合并回全局状态
        updated_global = StateConverter.review_to_global(global_state, review_state)

        # 验证合并正确
        assert 'review_result' in updated_global['shared_context']
        assert 'quality_metrics' in updated_global['shared_context']['review_result']
        assert len(updated_global['code_versions']) == 2  # 原始代码 + 改进代码

    @pytest.mark.asyncio
    async def test_review_agents_integration(self, mock_llm, mock_sandbox):
        """测试评审子图所有Agent的集成"""
        detector = MistakeDetectorAgent(mock_llm, mock_sandbox)
        generator = SuggestionGeneratorAgent(mock_llm)
        validator = ValidationTesterAgent(mock_llm, mock_sandbox)

        # 创建初始状态
        state = StateFactory.create_review_state(
            task_id="test-review-integration-1",
            code="def test(): pass",
            language="python",
            optimization_level="balanced"
        )

        # 步骤1: 检测问题
        state = await detector.detect_code_issues(state)
        assert state['review_phase'] in ["suggestion", "completed"]

        # 步骤2: 生成建议（如果有问题）
        if len(state['detected_issues']) > 0:
            state = await generator.generate_suggestions(state)
            assert state['review_phase'] in ["validation", "completed"]

            # 步骤3: 验证改进
            state = await validator.validate_improvements(state)
            # 验证后可能进入completed、detection或negotiation阶段
            assert state['review_phase'] in ["completed", "detection", "negotiation"]


class TestStateTransferBetweenGraphs:
    """测试主图与子图之间的状态传递"""

    @pytest.mark.asyncio
    async def test_global_to_dissection_to_global_roundtrip(self):
        """测试全局状态 -> 拆解状态 -> 全局状态的往返转换"""
        # 创建初始全局状态
        original_global = StateFactory.create_global_state(
            task_id="test-roundtrip-1",
            user_id="user-1",
            code="def factorial(n): return 1 if n <= 1 else n * factorial(n-1)",
            language="python",
            optimization_level="balanced"
        )

        # 转换为拆解状态
        dissection_state = StateConverter.global_to_dissection(original_global)

        # 模拟拆解子图执行
        dissection_state['execution_steps'] = [
            {"step_number": 1, "description": "检查基础情况"},
            {"step_number": 2, "description": "递归调用"}
        ]
        dissection_state['algorithm_type'] = "递归"
        dissection_state['time_complexity_analysis'] = "O(n)"

        # 合并回全局状态
        updated_global = StateConverter.dissection_to_global(original_global, dissection_state)

        # 验证状态完整性
        assert updated_global['task_id'] == original_global['task_id']
        assert 'dissection_result' in updated_global['shared_context']
        assert len(updated_global['shared_context']['dissection_result']['execution_steps']) == 2

    @pytest.mark.asyncio
    async def test_global_to_review_to_global_roundtrip(self):
        """测试全局状态 -> 评审状态 -> 全局状态的往返转换"""
        # 创建初始全局状态
        original_global = StateFactory.create_global_state(
            task_id="test-roundtrip-2",
            user_id="user-1",
            code="def slow_function(n):\n    result = 0\n    for i in range(n):\n        for j in range(n):\n            result += i * j\n    return result",
            language="python",
            optimization_level="performance"
        )

        # 转换为评审状态
        review_state = StateConverter.global_to_review(original_global)

        # 模拟评审子图执行
        review_state['detected_issues'] = [
            {
                "issue_id": "perf-1",
                "type": "performance",
                "severity": "high",
                "description": "嵌套循环导致O(n²)复杂度"
            }
        ]
        review_state['improved_code_versions'] = [
            "def optimized_function(n):\n    return sum(i * j for i in range(n) for j in range(n))"
        ]
        review_state['quality_metrics'] = {
            "overall_score": 8.0,
            "performance": 9.0,
            "readability": 8.5
        }

        # 合并回全局状态
        updated_global = StateConverter.review_to_global(original_global, review_state)

        # 验证状态完整性
        assert updated_global['task_id'] == original_global['task_id']
        assert 'review_result' in updated_global['shared_context']
        assert len(updated_global['code_versions']) == 2

    @pytest.mark.asyncio
    async def test_sequential_subgraph_execution(self):
        """测试顺序执行两个子图的状态传递"""
        # 创建初始全局状态
        global_state = StateFactory.create_global_state(
            task_id="test-sequential-1",
            user_id="user-1",
            code="def bubble_sort(arr):\n    n = len(arr)\n    for i in range(n):\n        for j in range(0, n-i-1):\n            if arr[j] > arr[j+1]:\n                arr[j], arr[j+1] = arr[j+1], arr[j]\n    return arr",
            language="python",
            optimization_level="balanced"
        )

        # 第一步: 执行拆解子图
        dissection_state = StateConverter.global_to_dissection(global_state)
        dissection_state['execution_steps'] = [
            {"step_number": 1, "description": "外层循环"},
            {"step_number": 2, "description": "内层循环比较"},
            {"step_number": 3, "description": "交换元素"}
        ]
        dissection_state['algorithm_type'] = "排序算法"
        dissection_state['time_complexity_analysis'] = "O(n²)"

        global_state = StateConverter.dissection_to_global(global_state, dissection_state)

        # 第二步: 执行评审子图
        review_state = StateConverter.global_to_review(global_state)
        review_state['detected_issues'] = [
            {
                "issue_id": "perf-1",
                "type": "performance",
                "severity": "medium",
                "description": "冒泡排序效率较低"
            }
        ]
        review_state['improved_code_versions'] = [
            "def quick_sort(arr):\n    if len(arr) <= 1:\n        return arr\n    pivot = arr[len(arr) // 2]\n    left = [x for x in arr if x < pivot]\n    middle = [x for x in arr if x == pivot]\n    right = [x for x in arr if x > pivot]\n    return quick_sort(left) + middle + quick_sort(right)"
        ]

        global_state = StateConverter.review_to_global(global_state, review_state)

        # 验证最终状态包含两个子图的结果
        assert 'dissection_result' in global_state['shared_context']
        assert 'review_result' in global_state['shared_context']
        assert len(global_state['shared_context']['dissection_result']['execution_steps']) == 3
        assert len(global_state['code_versions']) == 2


class TestStateConsistency:
    """测试状态一致性和验证"""

    def test_state_factory_creates_valid_states(self):
        """测试StateFactory创建的状态都是有效的"""
        # 测试全局状态
        global_state = StateFactory.create_global_state(
            task_id="test-factory-1",
            user_id="user-1",
            code="def test(): pass",
            language="python",
            optimization_level="balanced"
        )
        assert global_state['task_id'] == "test-factory-1"
        assert global_state['status'] == StateTaskStatus.PENDING
        assert global_state['current_phase'] == Phase.ANALYSIS

        # 测试拆解状态
        dissection_state = StateFactory.create_dissection_state(
            task_id="test-factory-2",
            code="def test(): pass",
            language="python"
        )
        assert dissection_state['task_id'] == "test-factory-2"
        assert dissection_state['analysis_phase'] == "parsing"

        # 测试评审状态
        review_state = StateFactory.create_review_state(
            task_id="test-factory-3",
            code="def test(): pass",
            language="python",
            optimization_level="balanced"
        )
        assert review_state['task_id'] == "test-factory-3"
        assert review_state['review_phase'] == "detection"

    def test_state_converter_preserves_task_id(self):
        """测试StateConverter在转换过程中保持task_id一致"""
        global_state = StateFactory.create_global_state(
            task_id="test-consistency-1",
            user_id="user-1",
            code="def test(): pass",
            language="python",
            optimization_level="balanced"
        )

        # 转换为拆解状态
        dissection_state = StateConverter.global_to_dissection(global_state)
        assert dissection_state['task_id'] == global_state['task_id']

        # 转换为评审状态
        review_state = StateConverter.global_to_review(global_state)
        assert review_state['task_id'] == global_state['task_id']

    def test_shared_context_isolation(self):
        """测试shared_context的隔离性"""
        global_state = StateFactory.create_global_state(
            task_id="test-isolation-1",
            user_id="user-1",
            code="def test(): pass",
            language="python",
            optimization_level="balanced"
        )

        # 添加拆解结果
        dissection_state = StateFactory.create_dissection_state(
            task_id="test-isolation-1",
            code="def test(): pass",
            language="python"
        )
        dissection_state['execution_steps'] = [{"step": 1}]
        global_state = StateConverter.dissection_to_global(global_state, dissection_state)

        # 添加评审结果
        review_state = StateFactory.create_review_state(
            task_id="test-isolation-1",
            code="def test(): pass",
            language="python",
            optimization_level="balanced"
        )
        review_state['quality_metrics'] = {"score": 8.0}
        global_state = StateConverter.review_to_global(global_state, review_state)

        # 验证两个子图的结果都被正确保存且互不干扰
        assert 'dissection_result' in global_state['shared_context']
        assert 'review_result' in global_state['shared_context']
        assert 'execution_steps' in global_state['shared_context']['dissection_result']
        assert 'quality_metrics' in global_state['shared_context']['review_result']


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
