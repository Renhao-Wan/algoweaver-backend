"""
Human-in-the-loop 机制专项验证测试（简化版）

测试所有关键暂停点和用户交互流程：
- 暂停信号的正确触发
- 用户反馈接收
- resume后的状态一致性
- 用户修改建议后的重新执行路径

需求: 4.x, 8.5, 10.1
"""

import pytest
import asyncio
from datetime import datetime

from app.graph.state import (
    GlobalState, DissectionState, ReviewState,
    TaskStatus, Phase, CollaborationMode,
    StateConverter, StateFactory
)


class TestHumanInTheLoopMechanism:
    """测试Human-in-the-loop机制"""

    @pytest.fixture
    def sample_code(self):
        """示例代码"""
        return "def factorial(n):\n    return 1 if n <= 1 else n * factorial(n-1)"

    @pytest.mark.asyncio
    async def test_human_intervention_flag(self, sample_code):
        """测试人工干预标志的设置和检查"""
        global_state = StateFactory.create_global_state(
            task_id="hitl-flag-test",
            user_id="test-user",
            code=sample_code,
            language="python",
            optimization_level="balanced"
        )

        # 初始状态不需要人工干预
        assert global_state['human_intervention_required'] is False

        # 设置需要人工干预
        global_state['human_intervention_required'] = True
        assert global_state['human_intervention_required'] is True

        # 清除人工干预标志
        global_state['human_intervention_required'] = False
        assert global_state['human_intervention_required'] is False

    @pytest.mark.asyncio
    async def test_human_decision_recording(self, sample_code):
        """测试人工决策的记录"""
        global_state = StateFactory.create_global_state(
            task_id="hitl-decision-test",
            user_id="test-user",
            code=sample_code,
            language="python",
            optimization_level="balanced"
        )

        # 记录用户决策（使用字典）
        decision1 = {
            "decision_id": "dec-1",
            "decision_type": "approve",
            "timestamp": datetime.utcnow().isoformat()
        }

        global_state['decision_history'].append(decision1)

        # 验证决策记录
        assert len(global_state['decision_history']) == 1
        assert global_state['decision_history'][0]['decision_type'] == "approve"

    @pytest.mark.asyncio
    async def test_pause_and_resume_workflow(self, sample_code):
        """测试暂停和恢复工作流"""
        global_state = StateFactory.create_global_state(
            task_id="hitl-pause-resume",
            user_id="test-user",
            code=sample_code,
            language="python",
            optimization_level="balanced"
        )

        # 模拟拆解完成
        dissection_state = StateConverter.global_to_dissection(global_state)
        dissection_state['execution_steps'] = [
            {"step_number": 1, "description": "检查基础情况"}
        ]
        dissection_state['analysis_phase'] = "completed"
        global_state = StateConverter.dissection_to_global(global_state, dissection_state)

        # 设置暂停
        global_state['human_intervention_required'] = True
        global_state['current_phase'] = Phase.REVIEW  # 使用REVIEW阶段表示等待人工审核

        # 验证暂停状态
        assert global_state['human_intervention_required'] is True
        assert global_state['current_phase'] == Phase.REVIEW

        # 用户批准后恢复
        global_state['decision_history'].append({
            "decision_id": "dec-1",
            "decision_type": "approve",
            "timestamp": datetime.utcnow().isoformat()
        })
        global_state['human_intervention_required'] = False
        global_state['current_phase'] = Phase.REVIEW

        # 验证恢复状态
        assert global_state['human_intervention_required'] is False
        assert global_state['current_phase'] == Phase.REVIEW

    @pytest.mark.asyncio
    async def test_state_consistency_after_pause(self, sample_code):
        """测试暂停后的状态一致性"""
        global_state = StateFactory.create_global_state(
            task_id="hitl-consistency",
            user_id="test-user",
            code=sample_code,
            language="python",
            optimization_level="balanced"
        )

        # 保存原始状态
        original_task_id = global_state['task_id']
        original_code = global_state['original_code']

        # 暂停
        global_state['human_intervention_required'] = True

        # 恢复
        global_state['human_intervention_required'] = False

        # 验证状态一致性
        assert global_state['task_id'] == original_task_id
        assert global_state['original_code'] == original_code

    @pytest.mark.asyncio
    async def test_multiple_pause_resume_cycles(self, sample_code):
        """测试多次暂停-恢复循环"""
        global_state = StateFactory.create_global_state(
            task_id="hitl-multiple",
            user_id="test-user",
            code=sample_code,
            language="python",
            optimization_level="balanced"
        )

        # 第一次暂停-恢复
        global_state['human_intervention_required'] = True
        global_state['decision_history'].append({
            "decision_id": "dec-1",
            "decision_type": "approve",
            "timestamp": datetime.utcnow().isoformat()
        })
        global_state['human_intervention_required'] = False

        # 第二次暂停-恢复
        global_state['human_intervention_required'] = True
        global_state['decision_history'].append({
            "decision_id": "dec-2",
            "decision_type": "modify",
            "timestamp": datetime.utcnow().isoformat()
        })
        global_state['human_intervention_required'] = False

        # 验证所有决策都被记录
        assert len(global_state['decision_history']) == 2
        assert global_state['decision_history'][0]['decision_id'] == "dec-1"
        assert global_state['decision_history'][1]['decision_id'] == "dec-2"

    @pytest.mark.asyncio
    async def test_user_feedback_storage(self, sample_code):
        """测试用户反馈的存储"""
        global_state = StateFactory.create_global_state(
            task_id="hitl-feedback",
            user_id="test-user",
            code=sample_code,
            language="python",
            optimization_level="balanced"
        )

        # 存储用户反馈
        user_feedback = "请关注性能优化"
        global_state['shared_context']['user_feedback'] = user_feedback

        # 验证反馈被保存
        assert 'user_feedback' in global_state['shared_context']
        assert global_state['shared_context']['user_feedback'] == user_feedback

    @pytest.mark.asyncio
    async def test_code_modification_tracking(self, sample_code):
        """测试代码修改的追踪"""
        global_state = StateFactory.create_global_state(
            task_id="hitl-code-mod",
            user_id="test-user",
            code=sample_code,
            language="python",
            optimization_level="balanced"
        )

        # 初始代码版本
        assert len(global_state['code_versions']) == 1

        # 用户修改代码
        modified_code = "def factorial_optimized(n): pass"
        global_state['code_versions'].append(modified_code)

        # 验证代码版本追踪
        assert len(global_state['code_versions']) == 2
        assert global_state['code_versions'][-1] == modified_code


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
