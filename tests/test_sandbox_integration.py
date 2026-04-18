"""
Python REPL 沙箱集成测试

测试沙箱与其他系统组件的集成
"""

import pytest
import asyncio
from app.graph.tools import PythonSandbox, PythonREPLTool, SandboxConfig


class TestSandboxIntegration:
    """沙箱集成测试"""
    
    @pytest.mark.asyncio
    async def test_import_from_tools_module(self):
        """测试从工具模块导入沙箱组件"""
        from app.graph.tools import (
            PythonSandbox,
            PythonREPLTool,
            ExecutionResult,
            SandboxConfig,
            CodeSecurityValidator
        )
        
        # 验证所有组件都可以正常导入和实例化
        config = SandboxConfig(timeout=5)
        sandbox = PythonSandbox(config)
        tool = PythonREPLTool(config)
        validator = CodeSecurityValidator()
        
        # 简单功能测试
        violations = validator.validate_code("print('Hello World')")
        assert len(violations) == 0
        
        result = await sandbox.execute_code("print('Integration test')")
        assert result.status == "success"
        assert "Integration test" in result.output
        
        # 清理资源
        sandbox.cleanup_resources()
        tool.sandbox.cleanup_resources()
    
    @pytest.mark.asyncio
    async def test_algorithm_execution_workflow(self):
        """测试算法执行工作流"""
        sandbox = PythonSandbox()
        
        try:
            # 模拟算法分析工作流
            algorithms = [
                ("冒泡排序", """
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n-i-1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
    return arr

test_array = [64, 34, 25, 12, 22, 11, 90]
sorted_array = bubble_sort(test_array.copy())
print(f"原始数组: {test_array}")
print(f"排序后: {sorted_array}")
"""),
                ("二分查找", """
def binary_search(arr, target):
    left, right = 0, len(arr) - 1
    
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    
    return -1

sorted_array = [1, 3, 5, 7, 9, 11, 13, 15]
target = 7
index = binary_search(sorted_array, target)
print(f"在数组 {sorted_array} 中查找 {target}")
print(f"找到位置: {index}")
"""),
                ("斐波那契数列", """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

def fibonacci_iterative(n):
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b

n = 10
recursive_result = fibonacci(n)
iterative_result = fibonacci_iterative(n)
print(f"递归方法: fibonacci({n}) = {recursive_result}")
print(f"迭代方法: fibonacci({n}) = {iterative_result}")
print(f"结果一致: {recursive_result == iterative_result}")
""")
            ]
            
            results = []
            for name, code in algorithms:
                print(f"\n执行算法: {name}")
                result = await sandbox.execute_code(code)
                results.append((name, result))
                
                assert result.status == "success", f"{name} 执行失败: {result.error}"
                assert result.execution_time > 0, f"{name} 执行时间异常"
                print(f"✓ {name} 执行成功，耗时 {result.execution_time:.3f}秒")
            
            # 验证所有算法都成功执行
            assert len(results) == 3
            for name, result in results:
                assert result.status == "success"
                assert len(result.output) > 0
                
        finally:
            sandbox.cleanup_resources()
    
    @pytest.mark.asyncio
    async def test_security_validation_workflow(self):
        """测试安全验证工作流"""
        sandbox = PythonSandbox()
        
        try:
            # 模拟代码质量检查工作流
            test_cases = [
                ("安全代码", """
def calculate_statistics(numbers):
    if not numbers:
        return {"mean": 0, "median": 0, "mode": None}
    
    mean = sum(numbers) / len(numbers)
    sorted_nums = sorted(numbers)
    n = len(sorted_nums)
    median = sorted_nums[n//2] if n % 2 == 1 else (sorted_nums[n//2-1] + sorted_nums[n//2]) / 2
    
    return {"mean": mean, "median": median}

data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
stats = calculate_statistics(data)
print(f"数据: {data}")
print(f"统计结果: {stats}")
""", "success"),
                ("危险导入", """
import os
import sys
print("尝试访问系统信息")
print(f"当前目录: {os.getcwd()}")
""", "blocked"),
                ("危险函数", """
user_input = "print('Hello')"
result = eval(user_input)
print(f"执行结果: {result}")
""", "blocked"),
                ("无限循环", """
counter = 0
while True:
    counter += 1
    if counter > 1000:
        break
print(f"计数器: {counter}")
""", "blocked")
            ]
            
            for name, code, expected_status in test_cases:
                print(f"\n测试: {name}")
                result = await sandbox.execute_code(code)
                
                if expected_status == "success":
                    assert result.status == "success", f"{name} 应该成功执行"
                    print(f"✓ {name} 成功执行")
                elif expected_status == "blocked":
                    assert result.status == "blocked", f"{name} 应该被阻止"
                    assert len(result.security_violations) > 0, f"{name} 应该有安全违规"
                    print(f"✓ {name} 被正确阻止")
                    
        finally:
            sandbox.cleanup_resources()
    
    @pytest.mark.asyncio
    async def test_performance_analysis_workflow(self):
        """测试性能分析工作流"""
        sandbox = PythonSandbox()
        
        try:
            # 模拟性能分析工作流
            performance_code = """
import time

def time_algorithm(func, *args):
    start = time.time()
    result = func(*args)
    end = time.time()
    return result, end - start

def linear_search(arr, target):
    for i, val in enumerate(arr):
        if val == target:
            return i
    return -1

def optimized_search(arr, target):
    # 使用 Python 内置的 index 方法
    try:
        return arr.index(target)
    except ValueError:
        return -1

# 测试数据
test_array = list(range(1000))
target = 500

# 性能比较
result1, time1 = time_algorithm(linear_search, test_array, target)
result2, time2 = time_algorithm(optimized_search, test_array, target)

print(f"线性搜索结果: {result1}, 耗时: {time1:.6f}秒")
print(f"优化搜索结果: {result2}, 耗时: {time2:.6f}秒")
print(f"性能提升: {time1/time2:.2f}倍" if time2 > 0 else "无法计算性能提升")
"""
            
            result = await sandbox.execute_code(performance_code)
            
            # 验证性能分析成功
            assert result.status == "success"
            assert "线性搜索结果" in result.output
            assert "优化搜索结果" in result.output
            assert "性能提升" in result.output or "无法计算性能提升" in result.output
            assert result.execution_time > 0
            
            print("✓ 性能分析工作流测试通过")
            
        finally:
            sandbox.cleanup_resources()
    
    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self):
        """测试错误恢复工作流"""
        sandbox = PythonSandbox()
        
        try:
            # 模拟错误处理和恢复工作流
            error_cases = [
                ("语法错误恢复", """
# 故意的语法错误
def broken_function(
    print("This will cause syntax error")
"""),
                ("运行时错误恢复", """
def risky_operation():
    return 10 / 0  # 除零错误

try:
    result = risky_operation()
    print(f"结果: {result}")
except ZeroDivisionError:
    print("捕获到除零错误，使用默认值")
    result = 0
    print(f"默认结果: {result}")
"""),
                ("名称错误恢复", """
try:
    print(f"未定义变量: {undefined_var}")
except NameError:
    print("捕获到名称错误，定义变量")
    undefined_var = "现在已定义"
    print(f"定义后的变量: {undefined_var}")
""")
            ]
            
            for name, code in error_cases:
                print(f"\n测试: {name}")
                result = await sandbox.execute_code(code)
                
                # 验证沙箱能够处理各种错误情况
                assert result.status in ["success", "error"], f"{name} 状态异常: {result.status}"
                
                if result.status == "error":
                    assert result.error is not None, f"{name} 错误信息为空"
                    print(f"✓ {name} 错误被正确捕获")
                else:
                    print(f"✓ {name} 成功执行")
                
                # 验证沙箱在错误后仍能正常工作
                test_result = await sandbox.execute_code("print('沙箱仍然正常工作')")
                assert test_result.status == "success"
                
        finally:
            sandbox.cleanup_resources()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])