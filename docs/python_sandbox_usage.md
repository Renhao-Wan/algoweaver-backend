# Python REPL 安全沙箱使用指南

## 概述

Python REPL 安全沙箱是 AlgoWeaver AI 系统的核心组件，提供安全的 Python 代码执行环境。它实现了多层安全防护，确保用户提交的代码不会对系统造成安全威胁。

## 核心特性

### 🔒 安全防护
- **文件系统访问限制**: 阻止对系统文件的读写操作
- **网络访问禁用**: 防止代码进行网络通信
- **危险操作检测**: 自动识别和阻止危险的代码模式
- **权限隔离**: 使用非特权用户执行代码

### ⏱️ 资源控制
- **执行超时**: 默认 30 秒超时，防止无限循环
- **内存限制**: 限制代码执行时的内存使用
- **CPU 限制**: 控制 CPU 使用率，防止资源耗尽
- **进程数限制**: 限制可创建的子进程数量

### 🧹 资源管理
- **自动清理**: 执行完成后自动清理临时文件
- **容器隔离**: 使用 Docker 容器提供完全隔离
- **异常恢复**: 出现异常时自动清理资源

## 快速开始

### 基本使用

```python
from app.graph.tools.python_repl import PythonSandbox

# 创建沙箱实例
sandbox = PythonSandbox()

# 执行安全代码
code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

result = fibonacci(10)
print(f"Fibonacci(10) = {result}")
"""

try:
    result = await sandbox.execute_code(code)
    print(f"执行状态: {result.status}")
    print(f"输出: {result.output}")
finally:
    sandbox.cleanup_resources()
```

### 自定义配置

```python
from app.graph.tools.python_repl import PythonSandbox, SandboxConfig

# 自定义沙箱配置
config = SandboxConfig(
    timeout=60,           # 60秒超时
    memory_limit="256m",  # 256MB 内存限制
    cpu_quota=100000,     # 100% CPU
    pids_limit=100        # 最多100个进程
)

sandbox = PythonSandbox(config)
```

### LangChain 工具集成

```python
from app.graph.tools.python_repl import PythonREPLTool

# 创建 LangChain 工具
tool = PythonREPLTool()

# 异步执行
output = await tool.arun("print('Hello from sandbox!')")
print(output)

# 同步执行
output = tool.run("print('Hello from sandbox!')")
print(output)
```

## 安全机制详解

### 危险操作检测

沙箱会自动检测和阻止以下危险操作：

#### 1. 危险模块导入
```python
# 这些导入会被阻止
import os
import sys
import subprocess
import socket
from urllib import request
```

#### 2. 危险内置函数
```python
# 这些函数调用会被阻止
eval("malicious_code")
exec("dangerous_operation")
open("/etc/passwd", "r")
__import__("os")
```

#### 3. 危险代码模式
```python
# 这些模式会被检测
while True:  # 无限循环
    pass

for i in range(1000000):  # 大范围循环
    pass

os.system("rm -rf /")  # 系统调用
```

### 代码清理

沙箱会自动清理危险代码：

```python
# 原始代码
import os
print("Hello World")
os.system("ls")

# 清理后的代码
# BLOCKED: import os
print("Hello World")
# BLOCKED: os.system("ls")
```

## 执行结果

### ExecutionResult 对象

```python
@dataclass
class ExecutionResult:
    status: str              # "success", "error", "timeout", "blocked"
    output: str              # 程序输出
    error: Optional[str]     # 错误信息
    execution_time: float    # 执行时间（秒）
    memory_usage: int        # 内存使用（字节）
    exit_code: int          # 退出码
    security_violations: List[str]  # 安全违规列表
```

### 状态说明

- **success**: 代码成功执行
- **error**: 代码执行出错（语法错误、运行时错误等）
- **timeout**: 代码执行超时
- **blocked**: 代码包含安全违规，被阻止执行

## 性能测试

沙箱支持性能基准测试：

```python
# 性能测试示例
test_cases = [
    {"input": 10},
    {"input": 20},
    {"input": 30}
]

results = await sandbox.run_performance_test(
    code="def factorial(n): return 1 if n <= 1 else n * factorial(n-1)",
    test_cases=test_cases,
    iterations=3
)

print(f"平均执行时间: {results['summary']['average_execution_time']:.3f}秒")
print(f"峰值内存使用: {results['summary']['peak_memory_usage']} 字节")
```

## 错误处理

### 常见错误类型

1. **语法错误**: Python 语法不正确
2. **运行时错误**: 代码执行时出现异常
3. **安全违规**: 代码包含危险操作
4. **超时错误**: 代码执行时间超过限制
5. **资源限制**: 内存或 CPU 使用超过限制

### 错误处理最佳实践

```python
async def safe_execute(code: str):
    sandbox = PythonSandbox()
    try:
        result = await sandbox.execute_code(code)
        
        if result.status == "success":
            return result.output
        elif result.status == "blocked":
            return f"代码被阻止: {'; '.join(result.security_violations)}"
        elif result.status == "timeout":
            return "代码执行超时"
        else:
            return f"执行错误: {result.error}"
            
    except Exception as e:
        return f"沙箱异常: {str(e)}"
    finally:
        sandbox.cleanup_resources()
```

## 部署配置

### Docker 环境

沙箱需要 Docker 环境支持：

```bash
# 检查 Docker 是否安装
docker --version

# 拉取 Python 镜像
docker pull python:3.11-alpine

# 启动 Docker 服务
sudo systemctl start docker
```

### 环境变量

```bash
# .env 文件配置
SANDBOX_TIMEOUT=30
SANDBOX_MEMORY_LIMIT=128m
SANDBOX_CPU_QUOTA=50000
SANDBOX_USE_DOCKER=true
```

### 无 Docker 模式

如果 Docker 不可用，沙箱会自动切换到模拟模式：

```python
# 强制使用模拟模式
sandbox = PythonSandbox(use_docker=False)
```

## 监控和日志

### 日志配置

```python
import logging

# 配置沙箱日志
logging.getLogger('app.graph.tools.python_repl').setLevel(logging.INFO)
```

### 监控指标

- 执行成功率
- 平均执行时间
- 安全违规次数
- 资源使用情况
- 错误类型分布

## 最佳实践

### 1. 资源管理
```python
# 总是使用 try-finally 确保资源清理
sandbox = PythonSandbox()
try:
    result = await sandbox.execute_code(code)
    # 处理结果
finally:
    sandbox.cleanup_resources()
```

### 2. 错误处理
```python
# 检查执行结果状态
if result.status == "success":
    # 处理成功结果
    process_output(result.output)
elif result.status == "blocked":
    # 处理安全违规
    log_security_violation(result.security_violations)
else:
    # 处理其他错误
    handle_error(result.error)
```

### 3. 性能优化
```python
# 重用沙箱实例
sandbox = PythonSandbox()
try:
    for code in code_list:
        result = await sandbox.execute_code(code)
        # 处理结果
finally:
    sandbox.cleanup_resources()
```

### 4. 安全考虑
```python
# 验证代码安全性
validator = CodeSecurityValidator()
violations = validator.validate_code(user_code)
if violations:
    # 拒绝执行
    return {"error": "代码包含安全违规", "violations": violations}
```

## 故障排除

### 常见问题

1. **Docker 连接失败**
   - 检查 Docker 服务是否运行
   - 验证 Docker 权限设置
   - 尝试使用模拟模式

2. **执行超时**
   - 增加超时时间配置
   - 优化代码算法复杂度
   - 检查是否存在无限循环

3. **内存不足**
   - 增加内存限制配置
   - 优化代码内存使用
   - 检查是否存在内存泄漏

4. **权限错误**
   - 检查 Docker 用户权限
   - 验证文件系统权限
   - 确认容器配置正确

### 调试技巧

```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 检查沙箱状态
print(f"使用 Docker: {sandbox.use_docker}")
print(f"配置: {sandbox.config}")

# 测试简单代码
simple_result = await sandbox.execute_code("print('Hello World')")
print(f"简单测试结果: {simple_result.status}")
```

## 扩展开发

### 自定义安全规则

```python
class CustomSecurityValidator(CodeSecurityValidator):
    def validate_code(self, code: str) -> List[str]:
        violations = super().validate_code(code)
        
        # 添加自定义规则
        if "custom_dangerous_function" in code:
            violations.append("禁止使用自定义危险函数")
        
        return violations
```

### 自定义执行环境

```python
class CustomSandbox(PythonSandbox):
    def _prepare_container_config(self, temp_file: str, timeout: int) -> Dict[str, Any]:
        config = super()._prepare_container_config(temp_file, timeout)
        
        # 添加自定义配置
        config['environment'] = ['CUSTOM_VAR=value']
        
        return config
```

## 总结

Python REPL 安全沙箱提供了一个强大而安全的代码执行环境，适用于：

- 在线代码教学平台
- 代码质量分析工具
- 算法竞赛平台
- 自动化测试系统
- AI 代码生成验证

通过多层安全防护和资源控制，确保用户代码的安全执行，同时提供良好的性能和可扩展性。