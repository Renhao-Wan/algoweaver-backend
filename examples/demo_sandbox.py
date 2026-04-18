#!/usr/bin/env python3
"""
Python REPL 安全沙箱演示脚本

演示沙箱的各种安全特性和功能
"""

import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.graph.tools.python_repl import PythonSandbox, PythonREPLTool, SandboxConfig


async def demo_safe_execution():
    """演示安全代码执行"""
    print("=== 演示 1: 安全代码执行 ===")
    
    sandbox = PythonSandbox()
    
    safe_code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# 计算斐波那契数列
for i in range(10):
    result = fibonacci(i)
    print(f"fibonacci({i}) = {result}")

# 简单的数学计算
import math
print(f"圆周率: {math.pi}")
print(f"自然对数的底: {math.e}")
"""
    
    try:
        result = await sandbox.execute_code(safe_code)
        print(f"执行状态: {result.status}")
        print(f"执行时间: {result.execution_time:.3f}秒")
        print("输出:")
        print(result.output)
        if result.error:
            print(f"错误: {result.error}")
    finally:
        sandbox.cleanup_resources()


async def demo_security_blocking():
    """演示安全阻止功能"""
    print("\n=== 演示 2: 安全阻止功能 ===")
    
    sandbox = PythonSandbox()
    
    dangerous_codes = [
        ("文件系统访问", """
import os
print("当前目录:", os.getcwd())
os.system('ls -la')
"""),
        ("网络访问", """
import urllib.request
response = urllib.request.urlopen('http://httpbin.org/get')
print(response.read())
"""),
        ("危险内置函数", """
eval("print('This should be blocked')")
exec("import os; os.system('echo dangerous')")
"""),
        ("进程操作", """
import subprocess
result = subprocess.run(['echo', 'hello'], capture_output=True, text=True)
print(result.stdout)
""")
    ]
    
    try:
        for name, code in dangerous_codes:
            print(f"\n--- 测试: {name} ---")
            result = await sandbox.execute_code(code)
            print(f"执行状态: {result.status}")
            if result.status == "blocked":
                print("安全违规:")
                for violation in result.security_violations:
                    print(f"  - {violation}")
            elif result.error:
                print(f"错误: {result.error}")
            else:
                print("输出:", result.output[:100] + "..." if len(result.output) > 100 else result.output)
    finally:
        sandbox.cleanup_resources()


async def demo_timeout_protection():
    """演示超时保护"""
    print("\n=== 演示 3: 超时保护 ===")
    
    config = SandboxConfig(timeout=3)  # 3秒超时
    sandbox = PythonSandbox(config)
    
    timeout_code = """
# 计算密集型任务，可能会超时
result = 0
for i in range(10**7):  # 大循环
    result += i * i
    if i % 1000000 == 0:
        print(f"进度: {i}")

print(f"最终结果: {result}")
"""
    
    try:
        print("执行计算密集型任务（3秒超时）...")
        result = await sandbox.execute_code(timeout_code)
        print(f"执行状态: {result.status}")
        print(f"执行时间: {result.execution_time:.3f}秒")
        if result.status == "timeout":
            print("任务因超时被终止")
        elif result.output:
            print("输出:", result.output)
        if result.error:
            print(f"错误: {result.error}")
    finally:
        sandbox.cleanup_resources()


async def demo_langchain_tool():
    """演示 LangChain 工具集成"""
    print("\n=== 演示 4: LangChain 工具集成 ===")
    
    tool = PythonREPLTool()
    
    test_codes = [
        ("数据处理", """
# 简单的数据处理示例
data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
squared = [x**2 for x in data]
filtered = [x for x in squared if x > 25]
print(f"原始数据: {data}")
print(f"平方后: {squared}")
print(f"过滤后 (>25): {filtered}")
print(f"平均值: {sum(filtered) / len(filtered)}")
"""),
        ("算法实现", """
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
print(f"原始数组: {test_array}")
print(f"排序后: {sorted_array}")
""")
    ]
    
    try:
        for name, code in test_codes:
            print(f"\n--- {name} ---")
            output = await tool.arun(code)
            print(output)
    finally:
        tool.sandbox.cleanup_resources()


async def demo_error_handling():
    """演示错误处理"""
    print("\n=== 演示 5: 错误处理 ===")
    
    sandbox = PythonSandbox()
    
    error_codes = [
        ("语法错误", """
def incomplete_function(
    print("语法错误示例")
"""),
        ("运行时错误", """
def divide_by_zero():
    return 10 / 0

result = divide_by_zero()
print(f"结果: {result}")
"""),
        ("名称错误", """
print(f"未定义的变量: {undefined_variable}")
""")
    ]
    
    try:
        for name, code in error_codes:
            print(f"\n--- {name} ---")
            result = await sandbox.execute_code(code)
            print(f"执行状态: {result.status}")
            print(f"退出码: {result.exit_code}")
            if result.output:
                print(f"输出: {result.output}")
            if result.error:
                print(f"错误: {result.error}")
    finally:
        sandbox.cleanup_resources()


async def main():
    """主演示函数"""
    print("Python REPL 安全沙箱演示")
    print("=" * 50)
    
    try:
        await demo_safe_execution()
        await demo_security_blocking()
        await demo_timeout_protection()
        await demo_langchain_tool()
        await demo_error_handling()
        
        print("\n" + "=" * 50)
        print("演示完成！")
        print("\n沙箱特性总结:")
        print("✓ 安全代码执行")
        print("✓ 危险操作阻止")
        print("✓ 执行超时保护")
        print("✓ 错误处理和恢复")
        print("✓ 资源自动清理")
        print("✓ LangChain 工具集成")
        
    except Exception as e:
        print(f"演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())