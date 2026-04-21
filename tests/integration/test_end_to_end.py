"""
端到端完整流程验证测试

使用真实算法题和代码片段进行端到端测试，验证：
- Dissection → Review 的完整闭环
- 最终输出报告的结构完整性（步骤、伪代码、可视化、改进对比、优化代码）

需求: 1.x, 2.x, 11.0
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
from app.graph.subgraphs.dissection.builder import DissectionSubgraphBuilder
from app.graph.subgraphs.review.builder import ReviewSubgraphBuilder


class TestEndToEndWorkflow:
    """端到端完整流程测试"""

    @pytest.fixture
    def bubble_sort_code(self):
        """冒泡排序算法代码"""
        return """def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n-i-1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
    return arr"""

    @pytest.fixture
    def fibonacci_code(self):
        """斐波那契数列代码"""
        return """def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)"""

    @pytest.fixture
    def binary_search_code(self):
        """二分查找代码"""
        return """def binary_search(arr, target):
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1"""

    @pytest.mark.asyncio
    async def test_bubble_sort_end_to_end(self, bubble_sort_code):
        """测试冒泡排序的端到端流程"""
        # 创建初始全局状态
        global_state = StateFactory.create_global_state(
            task_id="e2e-bubble-sort",
            user_id="test-user",
            code=bubble_sort_code,
            language="python",
            optimization_level="balanced"
        )

        # 第一步：算法拆解
        dissection_state = StateConverter.global_to_dissection(global_state)
        dissection_state['input_data'] = {"arr": [64, 34, 25, 12, 22, 11, 90]}

        # 模拟拆解子图执行
        dissection_state['execution_steps'] = [
            {"step_number": 1, "description": "初始化数组长度n=7"},
            {"step_number": 2, "description": "外层循环i=0"},
            {"step_number": 3, "description": "内层循环比较相邻元素"},
            {"step_number": 4, "description": "交换arr[0]和arr[1]"},
        ]
        dissection_state['algorithm_type'] = "排序算法"
        dissection_state['time_complexity_analysis'] = {
            "best": "O(n)",
            "average": "O(n²)",
            "worst": "O(n²)"
        }
        dissection_state['space_complexity_analysis'] = "O(1)"
        dissection_state['pseudocode_generated'] = """
        BUBBLE-SORT(A)
        1. n = length(A)
        2. for i = 0 to n-1
        3.     for j = 0 to n-i-2
        4.         if A[j] > A[j+1]
        5.             swap A[j] and A[j+1]
        6. return A
        """
        dissection_state['analysis_phase'] = "completed"

        # 合并回全局状态
        global_state = StateConverter.dissection_to_global(global_state, dissection_state)

        # 验证拆解结果
        assert 'dissection_result' in global_state['shared_context']
        assert len(global_state['shared_context']['dissection_result']['execution_steps']) == 4
        assert global_state['shared_context']['dissection_result']['algorithm_type'] == "排序算法"

        # 第二步：代码评审
        review_state = StateConverter.global_to_review(global_state)

        # 模拟评审子图执行
        review_state['detected_issues'] = [
            {
                "issue_id": "perf-1",
                "type": "performance",
                "severity": "medium",
                "description": "冒泡排序时间复杂度为O(n²)，对大数据集效率较低"
            },
            {
                "issue_id": "opt-1",
                "type": "optimization",
                "severity": "low",
                "description": "可以添加提前退出优化"
            }
        ]
        review_state['generated_suggestions'] = [
            {
                "suggestion_id": "sug-1",
                "description": "添加swap标志，如果一轮没有交换则提前退出",
                "code_snippet": "swapped = False"
            }
        ]
        review_state['improved_code_versions'] = [
            """def bubble_sort_optimized(arr):
    n = len(arr)
    for i in range(n):
        swapped = False
        for j in range(0, n-i-1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
                swapped = True
        if not swapped:
            break
    return arr"""
        ]
        review_state['quality_metrics'] = {
            "overall_score": 8.5,
            "readability": 9.0,
            "maintainability": 8.5,
            "performance": 7.5,
            "security": 9.0,
            "best_practices": 8.5
        }
        review_state['consensus_reached'] = True
        review_state['review_phase'] = "completed"

        # 合并回全局状态
        global_state = StateConverter.review_to_global(global_state, review_state)

        # 验证最终状态
        assert 'review_result' in global_state['shared_context']
        assert len(global_state['code_versions']) == 2  # 原始代码 + 优化代码
        assert 'quality_metrics' in global_state['shared_context']['review_result']

        # 验证完整报告结构
        report = self._generate_report(global_state)
        assert 'algorithm_analysis' in report
        assert 'execution_steps' in report['algorithm_analysis']
        assert 'complexity_analysis' in report['algorithm_analysis']
        assert 'pseudocode' in report['algorithm_analysis']
        assert 'code_review' in report
        assert 'detected_issues' in report['code_review']
        assert 'improvements' in report['code_review']
        assert 'quality_metrics' in report['code_review']
        assert 'final_code' in report

    @pytest.mark.asyncio
    async def test_fibonacci_end_to_end(self, fibonacci_code):
        """测试斐波那契数列的端到端流程"""
        # 创建初始全局状态
        global_state = StateFactory.create_global_state(
            task_id="e2e-fibonacci",
            user_id="test-user",
            code=fibonacci_code,
            language="python",
            optimization_level="performance"
        )

        # 第一步：算法拆解
        dissection_state = StateConverter.global_to_dissection(global_state)
        dissection_state['input_data'] = {"n": 5}

        # 模拟拆解结果
        dissection_state['execution_steps'] = [
            {"step_number": 1, "description": "调用fibonacci(5)"},
            {"step_number": 2, "description": "递归调用fibonacci(4)和fibonacci(3)"},
            {"step_number": 3, "description": "基础情况：n<=1返回n"},
        ]
        dissection_state['algorithm_type'] = "递归算法"
        dissection_state['time_complexity_analysis'] = {
            "best": "O(2^n)",
            "average": "O(2^n)",
            "worst": "O(2^n)"
        }
        dissection_state['space_complexity_analysis'] = "O(n)"
        dissection_state['analysis_phase'] = "completed"

        global_state = StateConverter.dissection_to_global(global_state, dissection_state)

        # 第二步：代码评审
        review_state = StateConverter.global_to_review(global_state)

        # 模拟评审结果
        review_state['detected_issues'] = [
            {
                "issue_id": "perf-1",
                "type": "performance",
                "severity": "critical",
                "description": "递归实现存在大量重复计算，时间复杂度为O(2^n)"
            }
        ]
        review_state['improved_code_versions'] = [
            """def fibonacci_dp(n):
    if n <= 1:
        return n
    dp = [0] * (n + 1)
    dp[1] = 1
    for i in range(2, n + 1):
        dp[i] = dp[i-1] + dp[i-2]
    return dp[n]"""
        ]
        review_state['quality_metrics'] = {
            "overall_score": 9.0,
            "performance": 9.5
        }
        review_state['consensus_reached'] = True
        review_state['review_phase'] = "completed"

        global_state = StateConverter.review_to_global(global_state, review_state)

        # 验证完整流程
        assert 'dissection_result' in global_state['shared_context']
        assert 'review_result' in global_state['shared_context']
        assert len(global_state['code_versions']) == 2

    @pytest.mark.asyncio
    async def test_binary_search_end_to_end(self, binary_search_code):
        """测试二分查找的端到端流程"""
        # 创建初始全局状态
        global_state = StateFactory.create_global_state(
            task_id="e2e-binary-search",
            user_id="test-user",
            code=binary_search_code,
            language="python",
            optimization_level="balanced"
        )

        # 第一步：算法拆解
        dissection_state = StateConverter.global_to_dissection(global_state)
        dissection_state['input_data'] = {
            "arr": [1, 3, 5, 7, 9, 11, 13, 15],
            "target": 7
        }

        # 模拟拆解结果
        dissection_state['execution_steps'] = [
            {"step_number": 1, "description": "初始化left=0, right=7"},
            {"step_number": 2, "description": "计算mid=3"},
            {"step_number": 3, "description": "arr[3]=7等于target，返回3"},
        ]
        dissection_state['algorithm_type'] = "查找算法"
        dissection_state['time_complexity_analysis'] = {
            "best": "O(1)",
            "average": "O(log n)",
            "worst": "O(log n)"
        }
        dissection_state['space_complexity_analysis'] = "O(1)"
        dissection_state['analysis_phase'] = "completed"

        global_state = StateConverter.dissection_to_global(global_state, dissection_state)

        # 第二步：代码评审（二分查找代码质量较好，可能没有严重问题）
        review_state = StateConverter.global_to_review(global_state)

        # 模拟评审结果（只有轻微建议）
        review_state['detected_issues'] = [
            {
                "issue_id": "doc-1",
                "type": "documentation",
                "severity": "low",
                "description": "缺少函数文档字符串"
            }
        ]
        review_state['improved_code_versions'] = [
            """def binary_search(arr, target):
    \"\"\"
    在有序数组中使用二分查找算法查找目标值

    Args:
        arr: 有序数组
        target: 目标值

    Returns:
        目标值的索引，如果不存在返回-1
    \"\"\"
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1"""
        ]
        review_state['quality_metrics'] = {
            "overall_score": 9.5,
            "readability": 9.5,
            "performance": 10.0,
            "maintainability": 9.0
        }
        review_state['consensus_reached'] = True
        review_state['review_phase'] = "completed"

        global_state = StateConverter.review_to_global(global_state, review_state)

        # 验证完整流程
        assert 'dissection_result' in global_state['shared_context']
        assert 'review_result' in global_state['shared_context']
        assert len(global_state['code_versions']) == 2

        # 验证报告结构
        report = self._generate_report(global_state)
        assert report['code_review']['quality_metrics']['overall_score'] >= 9.0

    def _generate_report(self, global_state: GlobalState) -> dict:
        """生成最终报告结构"""
        dissection_result = global_state['shared_context'].get('dissection_result', {})
        review_result = global_state['shared_context'].get('review_result', {})

        return {
            "task_id": global_state['task_id'],
            "algorithm_analysis": {
                "execution_steps": dissection_result.get('execution_steps', []),
                "complexity_analysis": {
                    "time": dissection_result.get('time_complexity_analysis', {}),
                    "space": dissection_result.get('space_complexity_analysis', "")
                },
                "pseudocode": dissection_result.get('pseudocode_generated', ""),
                "algorithm_type": dissection_result.get('algorithm_type', "")
            },
            "code_review": {
                "detected_issues": review_result.get('detected_issues', []),
                "improvements": review_result.get('generated_suggestions', []),
                "quality_metrics": review_result.get('quality_metrics', {})
            },
            "final_code": global_state['code_versions'][-1] if global_state['code_versions'] else ""
        }


class TestWorkflowEdgeCases:
    """测试工作流的边界情况"""

    @pytest.mark.asyncio
    async def test_empty_code_handling(self):
        """测试空代码的处理"""
        global_state = StateFactory.create_global_state(
            task_id="edge-empty-code",
            user_id="test-user",
            code="",
            language="python",
            optimization_level="balanced"
        )

        # 验证状态创建成功
        assert global_state['task_id'] == "edge-empty-code"
        assert global_state['original_code'] == ""

    @pytest.mark.asyncio
    async def test_invalid_language_handling(self):
        """测试不支持的语言处理"""
        global_state = StateFactory.create_global_state(
            task_id="edge-invalid-lang",
            user_id="test-user",
            code="function test() { return 42; }",
            language="javascript",  # 假设暂不支持
            optimization_level="balanced"
        )

        # 验证状态创建成功
        assert global_state['language'] == "javascript"

    @pytest.mark.asyncio
    async def test_multiple_iterations(self):
        """测试多轮迭代流程"""
        global_state = StateFactory.create_global_state(
            task_id="edge-multi-iter",
            user_id="test-user",
            code="def test(): pass",
            language="python",
            optimization_level="balanced"
        )

        # 模拟多轮评审
        for iteration in range(3):
            review_state = StateConverter.global_to_review(global_state)
            review_state['iteration_count'] = iteration + 1
            review_state['review_round'] = iteration + 1

            if iteration < 2:
                # 前两轮未达成共识
                review_state['consensus_reached'] = False
                review_state['review_phase'] = "negotiation"
            else:
                # 第三轮达成共识
                review_state['consensus_reached'] = True
                review_state['review_phase'] = "completed"

            global_state = StateConverter.review_to_global(global_state, review_state)

        # 验证最终状态
        assert 'review_result' in global_state['shared_context']


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
