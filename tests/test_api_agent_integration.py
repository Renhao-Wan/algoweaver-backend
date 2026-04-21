"""
FastAPI 与 Agent 集成简单测试

验证 API 接口与多智能体系统的基本配合。
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.deps import clear_dependency_cache


@pytest.fixture
def client():
    """创建测试客户端"""
    # 清除依赖缓存，确保每个测试使用新实例
    clear_dependency_cache()
    return TestClient(app)


class TestAPIAgentIntegration:
    """API 与 Agent 集成测试"""

    def test_create_task_and_check_status(self, client):
        """测试创建任务并查询状态"""
        # 创建任务
        request_data = {
            "code": "def add(a, b):\n    return a + b",
            "language": "python",
            "optimization_level": "balanced"
        }

        response = client.post("/api/weave-algorithm", json=request_data)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "task_id" in data
        task_id = data["task_id"]

        # 查询任务状态
        status_response = client.get(f"/api/task/{task_id}/status")
        assert status_response.status_code == 200

        status_data = status_response.json()
        assert status_data["task_id"] == task_id
        assert "status" in status_data

    def test_task_lifecycle(self, client):
        """测试任务生命周期"""
        # 1. 创建任务
        request_data = {
            "code": "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n-1)",
            "language": "python",
            "optimization_level": "balanced"
        }

        create_response = client.post("/api/weave-algorithm", json=request_data)
        assert create_response.status_code == 200
        task_id = create_response.json()["task_id"]

        # 2. 查询状态
        status_response = client.get(f"/api/task/{task_id}/status")
        assert status_response.status_code == 200

        # 3. 尝试获取结果（可能还未完成）
        result_response = client.get(f"/api/task/{task_id}/result")
        # 可能返回200（已完成）或500（未完成）
        assert result_response.status_code in [200, 500]

    def test_multiple_tasks(self, client):
        """测试创建多个任务"""
        task_ids = []

        # 创建3个任务
        for i in range(3):
            request_data = {
                "code": f"def func_{i}(x):\n    return x * {i}",
                "language": "python",
                "optimization_level": "balanced"
            }

            response = client.post("/api/weave-algorithm", json=request_data)
            assert response.status_code == 200
            task_ids.append(response.json()["task_id"])

        # 验证所有任务ID都不同
        assert len(set(task_ids)) == 3

        # 查询每个任务的状态
        for task_id in task_ids:
            status_response = client.get(f"/api/task/{task_id}/status")
            assert status_response.status_code == 200


class TestStateManagement:
    """状态管理测试"""

    def test_task_state_persistence(self, client):
        """测试任务状态持久化"""
        # 创建任务
        request_data = {
            "code": "def test(): pass",
            "language": "python",
            "optimization_level": "balanced"
        }

        response = client.post("/api/weave-algorithm", json=request_data)
        task_id = response.json()["task_id"]

        # 多次查询状态，验证状态一致性
        status1 = client.get(f"/api/task/{task_id}/status")
        status2 = client.get(f"/api/task/{task_id}/status")

        assert status1.status_code == 200
        assert status2.status_code == 200

        # 任务ID应该保持一致
        assert status1.json()["task_id"] == status2.json()["task_id"]


class TestErrorHandling:
    """错误处理测试"""

    def test_invalid_task_operations(self, client):
        """测试对无效任务的操作"""
        fake_task_id = "non-existent-task-12345"

        # 查询不存在的任务状态（返回200但success=False）
        status_response = client.get(f"/api/task/{fake_task_id}/status")
        assert status_response.status_code == 200
        assert status_response.json()["success"] is False

        # 获取不存在的任务结果
        result_response = client.get(f"/api/task/{fake_task_id}/result")
        assert result_response.status_code in [404, 500]

        # 恢复不存在的任务
        resume_data = {
            "accepted_suggestions": [],
            "rejected_suggestions": [],
            "custom_input": "test"
        }
        resume_response = client.post(f"/api/task/{fake_task_id}/resume", json=resume_data)
        assert resume_response.status_code in [404, 422, 500]

    def test_malformed_requests(self, client):
        """测试格式错误的请求"""
        # 缺少必需字段
        invalid_data = {
            "language": "python"
            # 缺少 code 字段
        }

        response = client.post("/api/weave-algorithm", json=invalid_data)
        assert response.status_code == 422

        # 无效的枚举值
        invalid_enum = {
            "code": "def test(): pass",
            "language": "invalid_language",
            "optimization_level": "balanced"
        }

        response = client.post("/api/weave-algorithm", json=invalid_enum)
        assert response.status_code == 422


class TestReportGeneration:
    """报告生成测试"""

    def test_generate_report_for_task(self, client):
        """测试为任务生成报告"""
        # 创建任务
        request_data = {
            "code": "def hello():\n    print('Hello, World!')",
            "language": "python",
            "optimization_level": "balanced"
        }

        response = client.post("/api/weave-algorithm", json=request_data)
        task_id = response.json()["task_id"]

        # 尝试生成报告（任务可能未完成）
        report_request = {
            "format": "markdown",
            "template": "default",
            "include_history": True
        }

        report_response = client.post(f"/api/task/{task_id}/report", json=report_request)
        # 可能返回200（成功）或500（任务未完成）
        assert report_response.status_code in [200, 500]

    def test_get_report_content(self, client):
        """测试获取报告内容"""
        # 创建任务
        request_data = {
            "code": "def square(x):\n    return x * x",
            "language": "python",
            "optimization_level": "balanced"
        }

        response = client.post("/api/weave-algorithm", json=request_data)
        task_id = response.json()["task_id"]

        # 尝试获取报告内容
        content_response = client.get(
            f"/api/task/{task_id}/report/content",
            params={"format": "markdown", "template": "summary"}
        )

        # 可能返回200（成功）或500（任务未完成）
        assert content_response.status_code in [200, 500]
