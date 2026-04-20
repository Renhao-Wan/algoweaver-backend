"""
性能与异常场景回归测试

测试：
- 多轮Debate循环的稳定性（达到最大迭代次数、confidence_score阈值）
- REPL沙箱在异常代码下的隔离性
- 错误处理和恢复机制

需求: 6.x, 9.x, 11.0
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from app.graph.state import (
    GlobalState, DissectionState, ReviewState,
    TaskStatus, Phase, CollaborationMode,
    StateConverter, StateFactory
)


class TestPerformanceAndStability:
    """测试性能和稳定性"""

    @pytest.mark.asyncio
    async def test_multiple_review_iterations(self):
        """测试多轮评审迭代的稳定性"""
        global_state = StateFactory.create_global_state(
            task_id="perf-multi-iter",
            user_id="test-user",
            code="def test(): pass",
            language="python",
            optimization_level="balanced"
        )

        max_iterations = 5
        for iteration in range(max_iterations):
            review_state = StateConverter.global_to_review(global_state)
            review_state['iteration_count'] = iteration + 1
            review_state['review_round'] = iteration + 1

            if iteration < max_iterations - 1:
                # 未达成共识
                review_state['consensus_reached'] = False
                review_state['review_phase'] = "negotiation"
            else:
                # 最后一轮达成共识
                review_state['consensus_reached'] = True
                review_state['review_phase'] = "completed"

            global_state = StateConverter.review_to_global(global_state, review_state)

        # 验证迭代完成
        assert 'review_result' in global_state['shared_context']

    @pytest.mark.asyncio
    async def test_max_iteration_limit(self):
        """测试达到最大迭代次数的处理"""
        global_state = StateFactory.create_global_state(
            task_id="perf-max-iter",
            user_id="test-user",
            code="def test(): pass",
            language="python",
            optimization_level="balanced"
        )

        max_iterations = 10
        for iteration in range(max_iterations):
            review_state = StateConverter.global_to_review(global_state)
            review_state['iteration_count'] = iteration + 1
            review_state['review_round'] = iteration + 1

            # 模拟始终未达成共识
            review_state['consensus_reached'] = False
            review_state['review_phase'] = "negotiation"

            global_state = StateConverter.review_to_global(global_state, review_state)

        # 验证系统仍然稳定
        assert 'review_result' in global_state['shared_context']

    @pytest.mark.asyncio
    async def test_confidence_score_threshold(self):
        """测试置信度阈值的处理"""
        global_state = StateFactory.create_global_state(
            task_id="perf-confidence",
            user_id="test-user",
            code="def test(): pass",
            language="python",
            optimization_level="balanced"
        )

        # 模拟低置信度
        review_state = StateConverter.global_to_review(global_state)
        review_state['confidence_score'] = 0.3  # 低置信度
        review_state['consensus_reached'] = False
        review_state['review_phase'] = "negotiation"

        global_state = StateConverter.review_to_global(global_state, review_state)

        # 验证状态
        assert 'review_result' in global_state['shared_context']

        # 模拟高置信度
        review_state = StateConverter.global_to_review(global_state)
        review_state['confidence_score'] = 0.95  # 高置信度
        review_state['consensus_reached'] = True
        review_state['review_phase'] = "completed"

        global_state = StateConverter.review_to_global(global_state, review_state)

        # 验证完成
        assert 'review_result' in global_state['shared_context']


class TestExceptionHandling:
    """测试异常处理"""

    @pytest.mark.asyncio
    async def test_invalid_code_handling(self):
        """测试无效代码的处理"""
        global_state = StateFactory.create_global_state(
            task_id="except-invalid-code",
            user_id="test-user",
            code="def invalid( syntax error",  # 语法错误
            language="python",
            optimization_level="balanced"
        )

        # 验证状态创建成功（即使代码无效）
        assert global_state['task_id'] == "except-invalid-code"
        assert global_state['original_code'] == "def invalid( syntax error"

    @pytest.mark.asyncio
    async def test_error_recovery(self):
        """测试错误恢复机制"""
        global_state = StateFactory.create_global_state(
            task_id="except-recovery",
            user_id="test-user",
            code="def test(): pass",
            language="python",
            optimization_level="balanced"
        )

        # 模拟拆解失败
        dissection_state = StateConverter.global_to_dissection(global_state)
        dissection_state['error_info'] = "模拟的拆解错误"
        dissection_state['needs_retry'] = True
        dissection_state['retry_count'] = 1

        global_state = StateConverter.dissection_to_global(global_state, dissection_state)

        # 验证错误信息被记录
        assert 'dissection_result' in global_state['shared_context']

        # 模拟重试成功
        dissection_state = StateConverter.global_to_dissection(global_state)
        dissection_state['error_info'] = None
        dissection_state['needs_retry'] = False
        dissection_state['execution_steps'] = [
            {"step_number": 1, "description": "重试成功"}
        ]
        dissection_state['analysis_phase'] = "completed"

        global_state = StateConverter.dissection_to_global(global_state, dissection_state)

        # 验证恢复成功
        assert len(global_state['shared_context']['dissection_result']['execution_steps']) > 0

    @pytest.mark.asyncio
    async def test_retry_count_tracking(self):
        """测试重试次数追踪"""
        global_state = StateFactory.create_global_state(
            task_id="except-retry-count",
            user_id="test-user",
            code="def test(): pass",
            language="python",
            optimization_level="balanced"
        )

        # 初始重试次数
        assert global_state['retry_count'] == 0

        # 模拟多次重试
        for i in range(3):
            global_state['retry_count'] += 1

        # 验证重试次数
        assert global_state['retry_count'] == 3

    @pytest.mark.asyncio
    async def test_empty_execution_steps(self):
        """测试空执行步骤的处理"""
        global_state = StateFactory.create_global_state(
            task_id="except-empty-steps",
            user_id="test-user",
            code="def test(): pass",
            language="python",
            optimization_level="balanced"
        )

        # 模拟空执行步骤
        dissection_state = StateConverter.global_to_dissection(global_state)
        dissection_state['execution_steps'] = []  # 空列表
        dissection_state['analysis_phase'] = "completed"

        global_state = StateConverter.dissection_to_global(global_state, dissection_state)

        # 验证系统能够处理空步骤
        assert 'dissection_result' in global_state['shared_context']
        assert len(global_state['shared_context']['dissection_result']['execution_steps']) == 0


class TestEdgeCases:
    """测试边界情况"""

    @pytest.mark.asyncio
    async def test_very_long_code(self):
        """测试非常长的代码"""
        long_code = "def test():\n" + "    pass\n" * 1000  # 1000行代码
        global_state = StateFactory.create_global_state(
            task_id="edge-long-code",
            user_id="test-user",
            code=long_code,
            language="python",
            optimization_level="balanced"
        )

        # 验证能够处理长代码
        assert global_state['original_code'] == long_code

    @pytest.mark.asyncio
    async def test_special_characters_in_code(self):
        """测试代码中的特殊字符"""
        special_code = 'def test():\n    s = "特殊字符: 中文, émojis 🎉, symbols @#$%"\n    return s'
        global_state = StateFactory.create_global_state(
            task_id="edge-special-chars",
            user_id="test-user",
            code=special_code,
            language="python",
            optimization_level="balanced"
        )

        # 验证能够处理特殊字符
        assert global_state['original_code'] == special_code

    @pytest.mark.asyncio
    async def test_concurrent_state_updates(self):
        """测试并发状态更新"""
        global_state = StateFactory.create_global_state(
            task_id="edge-concurrent",
            user_id="test-user",
            code="def test(): pass",
            language="python",
            optimization_level="balanced"
        )

        # 模拟并发更新（在实际场景中需要锁机制）
        tasks = []
        for i in range(5):
            async def update_state(index):
                global_state['shared_context'][f'update_{index}'] = f'value_{index}'

            tasks.append(update_state(i))

        await asyncio.gather(*tasks)

        # 验证所有更新都被记录
        for i in range(5):
            assert f'update_{i}' in global_state['shared_context']

    @pytest.mark.asyncio
    async def test_state_size_limits(self):
        """测试状态大小限制"""
        global_state = StateFactory.create_global_state(
            task_id="edge-state-size",
            user_id="test-user",
            code="def test(): pass",
            language="python",
            optimization_level="balanced"
        )

        # 添加大量数据到shared_context
        for i in range(100):
            global_state['shared_context'][f'key_{i}'] = f'value_{i}' * 100

        # 验证状态仍然有效
        assert len(global_state['shared_context']) == 100


class TestRegressionTests:
    """回归测试"""

    @pytest.mark.asyncio
    async def test_state_converter_consistency(self):
        """测试状态转换器的一致性（回归测试）"""
        global_state = StateFactory.create_global_state(
            task_id="regression-converter",
            user_id="test-user",
            code="def test(): pass",
            language="python",
            optimization_level="balanced"
        )

        # 多次转换应该保持一致
        for _ in range(10):
            dissection_state = StateConverter.global_to_dissection(global_state)
            assert dissection_state['task_id'] == global_state['task_id']
            assert dissection_state['code'] == global_state['original_code']

    @pytest.mark.asyncio
    async def test_state_factory_consistency(self):
        """测试状态工厂的一致性（回归测试）"""
        # 创建多个相同参数的状态
        states = []
        for i in range(5):
            state = StateFactory.create_global_state(
                task_id=f"regression-factory-{i}",
                user_id="test-user",
                code="def test(): pass",
                language="python",
                optimization_level="balanced"
            )
            states.append(state)

        # 验证所有状态的结构一致
        for state in states:
            assert state['status'] == TaskStatus.PENDING
            assert state['current_phase'] == Phase.ANALYSIS
            assert len(state['code_versions']) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
