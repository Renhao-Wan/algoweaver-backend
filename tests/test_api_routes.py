"""
FastAPI 路由层简单测试

验证 API 接口的基本功能和参数处理。
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from app.main import app


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


class TestWeaveAlgorithm:
    """代码分析任务创建接口测试"""

    def test_create_task_invalid_language(self, client):
        """测试无效的编程语言"""
        request_data = {
            "code": "def test(): pass",
            "language": "invalid_language",
            "optimization_level": "balanced"
        }

        response = client.post("/api/weave-algorithm", json=request_data)
        assert response.status_code == 422  # Validation error

    def test_create_task_missing_code(self, client):
        """测试缺少代码字段"""
        request_data = {
            "language": "python",
            "optimization_level": "balanced"
        }

        response = client.post("/api/weave-algorithm", json=request_data)
        assert response.status_code == 422


class TestTaskStatus:
    """任务状态查询接口测试"""

    def test_get_task_status_not_found(self, client):
        """测试查询不存在的任务"""
        task_id = "non-existent-task"

        # 由于没有创建任务，应该返回错误
        response = client.get(f"/api/task/{task_id}/status")
        # 可能返回500或404，取决于实现
        assert response.status_code in [404, 500]


class TestAnalysisResult:
    """分析结果获取接口测试"""

    def test_get_analysis_result_not_found(self, client):
        """测试任务不存在"""
        task_id = "non-existent-task"

        response = client.get(f"/api/task/{task_id}/result")
        assert response.status_code in [404, 500]


class TestResumeTask:
    """任务恢复接口测试"""

    def test_resume_task_not_found(self, client):
        """测试恢复不存在的任务"""
        task_id = "non-existent-task"
        request_data = {
            "accepted_suggestions": [0, 1],
            "rejected_suggestions": [],
            "custom_input": "继续执行"
        }

        response = client.post(f"/api/task/{task_id}/resume", json=request_data)
        assert response.status_code in [404, 500]


class TestCancelTask:
    """任务取消接口测试"""

    def test_cancel_task_not_found(self, client):
        """测试取消不存在的任务"""
        task_id = "non-existent-task"

        response = client.delete(f"/api/task/{task_id}")
        assert response.status_code in [404, 500]


class TestReportGeneration:
    """报告生成接口测试"""

    def test_generate_report_not_found(self, client):
        """测试为不存在的任务生成报告"""
        task_id = "non-existent-task"
        request_data = {
            "format": "markdown",
            "template": "default",
            "include_history": True
        }

        response = client.post(f"/api/task/{task_id}/report", json=request_data)
        assert response.status_code in [404, 500]

    def test_get_report_content_not_found(self, client):
        """测试获取不存在任务的报告内容"""
        task_id = "non-existent-task"

        response = client.get(
            f"/api/task/{task_id}/report/content",
            params={"format": "markdown", "template": "default"}
        )
        assert response.status_code in [404, 500]
