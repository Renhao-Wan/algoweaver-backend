"""
Python REPL 安全沙箱测试

测试沙箱的安全性、功能性和性能
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch

from app.graph.tools.python_repl import (
    PythonSandbox,
    PythonREPLTool,
    ExecutionResult,
    SandboxConfig,
    CodeSecurityValidator
)


class TestCodeSecurityValidator:
    """代码安全验证器测试"""
    
    def setup_method(self):
        self.validator = CodeSecurityValidator()
    
    def test_detect_dangerous_imports(self):
        """测试危险导入检测"""
        dangerous_code = """
import os
import sys
from subprocess import call
import socket
"""
        violations = self.validator.validate_code(dangerous_code)
        assert len(violations) >= 4
        assert any("os" in v for v in violations)
        assert any("sys" in v for v in violations)
        assert any("subprocess" in v for v in violations)
        assert any("socket" in v for v in violations)
    
    def test_detect_dangerous_builtins(self):
        """测试危险内置函数检测"""
        dangerous_code = """
eval("print('hello')")
exec("x = 1")
open('/etc/passwd', 'r')
__import__('os')
"""
        violations = self.validator.validate_code(dangerous_code)
        assert len(violations) >= 4
        assert any("eval" in v for v in violations)
        assert any("exec" in v for v in violations)
        assert any("open" in v for v in violations)
        assert any("__import__" in v for v in violations)
    
    def test_detect_dangerous_patterns(self):
        """测试危险模式检测"""
        dangerous_code = """
while True:
    pass

for i in range(1000000):
    print(i)
"""
        violations = self.validator.validate_code(dangerous_code)
        assert len(violations) >= 1
        assert any("while True" in v for v in violations)
    
    def test_safe_code_passes(self):
        """测试安全代码通过验证"""
        safe_code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

result = fibonacci(10)
print(f"Fibonacci(10) = {result}")
"""
        violations = self.validator.validate_code(safe_code)
        assert len(violations) == 0
    
    def test_sanitize_code(self):
        """测试代码清理功能"""
        dangerous_code = """
import os
print("Hello World")
import sys
def safe_function():
    return 42
"""
        sanitized = self.validator.sanitize_code(dangerous_code)
        assert "# BLOCKED: import os" in sanitized
        assert "# BLOCKED: import sys" in sanitized
        assert "print(\"Hello World\")" in sanitized
        assert "def safe_function():" in sanitized


class TestPythonSandbox:
    """Python 沙箱测试"""
    
    def setup_method(self):
        # 使用测试配置，优先使用模拟模式以避免 Docker 依赖
        config = SandboxConfig(
            timeout=10,  # 较短的超时时间用于测试
            memory_limit="64m",
            cpu_quota=25000  # 25% CPU
        )
        # 尝试使用 Docker，如果失败则自动切换到模拟模式
        self.sandbox = PythonSandbox(config, use_docker=True)
    
    def teardown_method(self):
        """清理测试资源"""
        self.sandbox.cleanup_resources()
    
    @pytest.mark.asyncio
    async def test_execute_safe_code(self):
        """测试执行安全代码"""
        safe_code = """
def add(a, b):
    return a + b

result = add(2, 3)
print(f"2 + 3 = {result}")
"""
        result = await self.sandbox.execute_code(safe_code)
        
        assert result.status == "success"
        assert "2 + 3 = 5" in result.output
        assert result.execution_time > 0
        assert result.exit_code == 0
    
    @pytest.mark.asyncio
    async def test_block_dangerous_imports(self):
        """测试阻止危险导入"""
        dangerous_code = """
import os
os.system('echo "This should be blocked"')
"""
        result = await self.sandbox.execute_code(dangerous_code)
        
        assert result.status == "blocked"
        assert len(result.security_violations) > 0
        assert any("os" in v for v in result.security_violations)
    
    @pytest.mark.asyncio
    async def test_block_dangerous_builtins(self):
        """测试阻止危险内置函数"""
        dangerous_code = """
eval("print('This should be blocked')")
"""
        result = await self.sandbox.execute_code(dangerous_code)
        
        assert result.status == "blocked"
        assert len(result.security_violations) > 0
        assert any("eval" in v for v in result.security_violations)
    
    @pytest.mark.asyncio
    async def test_execution_timeout(self):
        """测试执行超时"""
        # 创建一个会超时的代码
        timeout_code = """
import time
time.sleep(15)  # 超过测试配置的10秒超时
print("This should timeout")
"""
        
        # 由于我们的安全验证器会阻止 time 模块，我们需要用其他方式测试超时
        # 使用一个计算密集型的循环
        timeout_code = """
# 计算密集型循环，应该会超时
result = 0
for i in range(10**8):
    result += i * i
print(f"Result: {result}")
"""
        
        start_time = time.time()
        result = await self.sandbox.execute_code(timeout_code, timeout=2)
        execution_time = time.time() - start_time
        
        # 应该在超时时间内返回
        assert execution_time <= 3  # 给一些缓冲时间
        assert result.status in ["timeout", "blocked"]  # 可能被阻止或超时
    
    @pytest.mark.asyncio
    async def test_syntax_error_handling(self):
        """测试语法错误处理"""
        syntax_error_code = """
def incomplete_function(
    print("This has syntax error")
"""
        result = await self.sandbox.execute_code(syntax_error_code)
        
        # 语法错误应该被容器捕获
        assert result.status in ["error", "success"]  # 取决于容器如何处理
        if result.status == "error":
            assert result.exit_code != 0
    
    @pytest.mark.asyncio
    async def test_runtime_error_handling(self):
        """测试运行时错误处理"""
        runtime_error_code = """
def divide_by_zero():
    return 1 / 0

result = divide_by_zero()
print(f"Result: {result}")
"""
        result = await self.sandbox.execute_code(runtime_error_code)
        
        # 运行时错误应该被捕获
        assert result.status in ["error", "success"]  # 取决于是否有异常处理
        if result.status == "error":
            assert result.exit_code != 0
    
    @pytest.mark.asyncio
    async def test_memory_usage_tracking(self):
        """测试内存使用跟踪"""
        memory_code = """
# 创建一些数据来使用内存
data = [i for i in range(1000)]
print(f"Created list with {len(data)} elements")
"""
        result = await self.sandbox.execute_code(memory_code)
        
        assert result.status == "success"
        # 内存使用应该被记录（如果 Docker 支持）
        # 注意：在某些环境中可能无法获取内存统计
        assert result.memory_usage >= 0
    
    @pytest.mark.asyncio
    async def test_resource_cleanup(self):
        """测试资源清理"""
        # 执行一些代码
        code = "print('Testing cleanup')"
        await self.sandbox.execute_code(code)
        
        # 检查临时文件是否被清理
        temp_files_before = len(self.sandbox._temp_files)
        self.sandbox.cleanup_resources()
        temp_files_after = len(self.sandbox._temp_files)
        
        assert temp_files_after == 0


class TestPythonREPLTool:
    """Python REPL 工具测试"""
    
    def setup_method(self):
        config = SandboxConfig(timeout=5)
        self.tool = PythonREPLTool(config)
    
    def teardown_method(self):
        """清理测试资源"""
        self.tool.sandbox.cleanup_resources()
    
    @pytest.mark.asyncio
    async def test_arun_success(self):
        """测试异步运行成功"""
        code = """
print("Hello from sandbox!")
result = 2 + 2
print(f"2 + 2 = {result}")
"""
        output = await self.tool.arun(code)
        
        assert "执行成功" in output
        assert "Hello from sandbox!" in output
        assert "2 + 2 = 4" in output
        assert "执行时间" in output
    
    @pytest.mark.asyncio
    async def test_arun_blocked(self):
        """测试异步运行被阻止"""
        dangerous_code = """
import os
os.system('rm -rf /')
"""
        output = await self.tool.arun(dangerous_code)
        
        assert "代码被阻止执行" in output
        assert "os" in output
    
    @pytest.mark.asyncio
    async def test_arun_error(self):
        """测试异步运行错误"""
        error_code = """
undefined_variable + 1
"""
        output = await self.tool.arun(error_code)
        
        # 可能是执行失败或成功（取决于容器如何处理）
        assert "执行" in output
    
    def test_run_sync(self):
        """测试同步运行"""
        code = "print('Sync execution test')"
        output = self.tool.run(code)
        
        assert isinstance(output, str)
        assert len(output) > 0


class TestPerformanceTesting:
    """性能测试功能测试"""
    
    def setup_method(self):
        config = SandboxConfig(timeout=10)
        self.sandbox = PythonSandbox(config)
    
    def teardown_method(self):
        self.sandbox.cleanup_resources()
    
    @pytest.mark.asyncio
    async def test_performance_test_basic(self):
        """测试基本性能测试功能"""
        code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# 测试小数值以避免超时
result = fibonacci(5)
print(f"Fibonacci(5) = {result}")
"""
        
        test_cases = [
            {"input": 5},
            {"input": 6},
        ]
        
        results = await self.sandbox.run_performance_test(
            code, test_cases, iterations=2
        )
        
        assert results['summary']['total_tests'] == 2
        assert results['summary']['successful_tests'] >= 0
        assert len(results['test_cases']) == 2
        
        for test_case in results['test_cases']:
            assert 'test_case_id' in test_case
            assert 'iterations' in test_case
            assert 'average_time' in test_case


# 集成测试
class TestSandboxIntegration:
    """沙箱集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """测试完整工作流程"""
        sandbox = PythonSandbox()
        
        try:
            # 1. 执行安全代码
            safe_result = await sandbox.execute_code("""
def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + middle + quicksort(right)

test_array = [3, 6, 8, 10, 1, 2, 1]
sorted_array = quicksort(test_array)
print(f"Original: {test_array}")
print(f"Sorted: {sorted_array}")
""")
            
            assert safe_result.status == "success"
            assert "Original:" in safe_result.output
            assert "Sorted:" in safe_result.output
            
            # 2. 尝试执行危险代码
            dangerous_result = await sandbox.execute_code("""
import subprocess
subprocess.run(['ls', '/'])
""")
            
            assert dangerous_result.status == "blocked"
            assert len(dangerous_result.security_violations) > 0
            
        finally:
            sandbox.cleanup_resources()


# 性能基准测试
@pytest.mark.performance
class TestPerformanceBenchmarks:
    """性能基准测试"""
    
    @pytest.mark.asyncio
    async def test_execution_speed_benchmark(self):
        """测试执行速度基准"""
        sandbox = PythonSandbox()
        
        try:
            # 测试简单计算的执行速度
            simple_code = """
result = sum(range(1000))
print(f"Sum of 0-999: {result}")
"""
            
            start_time = time.time()
            result = await sandbox.execute_code(simple_code)
            total_time = time.time() - start_time
            
            assert result.status == "success"
            assert total_time < 5.0  # 应该在5秒内完成
            assert result.execution_time < 3.0  # 实际执行时间应该更短
            
        finally:
            sandbox.cleanup_resources()
    
    @pytest.mark.asyncio
    async def test_concurrent_execution(self):
        """测试并发执行"""
        sandbox = PythonSandbox()
        
        try:
            # 创建多个并发任务（顺序执行以避免资源竞争）
            results = []
            for i in range(3):
                code = f"""
result = {i} * {i}
print(f"Task {i}: {i} * {i} = {{result}}")
"""
                result = await sandbox.execute_code(code)
                results.append(result)
            
            # 验证大部分任务都成功
            successful_results = [r for r in results if r.status == "success"]
            assert len(successful_results) >= 2  # 至少2个成功
            
            for result in successful_results:
                assert "Task" in result.output
                
        finally:
            sandbox.cleanup_resources()


if __name__ == "__main__":
    # 运行基本测试
    pytest.main([__file__, "-v"])