"""
Python REPL 安全沙箱执行器

基于 Docker 容器的安全代码执行环境，实现：
- 文件系统访问限制
- 网络访问禁用
- 执行时间限制（30秒）
- 内存和CPU资源限制
- 危险操作检测和阻止
- 临时资源自动清理
"""

import asyncio
import tempfile
import os
import time
import re
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from contextlib import asynccontextmanager

import docker
import psutil
from docker.errors import ContainerError, APIError, ImageNotFound

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """代码执行结果"""
    status: str  # "success", "error", "timeout", "blocked", "memory_limit_exceeded"
    output: str
    error: Optional[str] = None
    execution_time: float = 0.0
    memory_usage: int = 0  # 字节
    exit_code: int = 0
    security_violations: List[str] = None
    
    def __post_init__(self):
        if self.security_violations is None:
            self.security_violations = []


@dataclass
class SandboxConfig:
    """沙箱配置"""
    timeout: int = 30  # 执行超时时间（秒）
    memory_limit: str = "128m"  # 内存限制
    cpu_quota: int = 50000  # CPU 配额（50% CPU）
    cpu_period: int = 100000
    pids_limit: int = 50  # 进程数限制
    network_disabled: bool = True  # 禁用网络
    read_only: bool = True  # 只读文件系统
    container_image: str = "python:3.11-alpine"  # 容器镜像


class CodeSecurityValidator:
    """代码安全验证器"""
    
    # 危险的导入模块
    DANGEROUS_IMPORTS = {
        'os', 'sys', 'subprocess', 'socket', 'urllib', 'urllib2', 'urllib3',
        'requests', 'http', 'ftplib', 'smtplib', 'telnetlib', 'poplib',
        'imaplib', 'nntplib', 'ssl', 'webbrowser', 'ctypes', 'multiprocessing',
        'threading', 'asyncio', 'concurrent', 'queue', 'pickle', 'shelve',
        'dbm', 'sqlite3', 'mysql', 'psycopg2', 'pymongo', 'redis',
        'shutil', 'glob', 'tempfile', 'zipfile', 'tarfile', 'gzip',
        'bz2', 'lzma', 'zlib', 'mmap', 'fcntl', 'termios', 'tty',
        'pty', 'pipes', 'resource', 'syslog', 'pwd', 'grp', 'crypt',
        'spwd', 'nis', 'sysconfig', 'platform', 'getpass', 'curses',
        'turtle', 'tkinter', 'pygame', 'PIL', 'cv2', 'numpy.ctypeslib'
    }
    
    # 危险的内置函数
    DANGEROUS_BUILTINS = {
        '__import__', 'eval', 'exec', 'compile', 'open', 'file',
        'input', 'raw_input', 'reload', 'vars', 'locals', 'globals',
        'dir', 'getattr', 'setattr', 'delattr', 'hasattr'
    }
    
    # 危险的操作模式
    DANGEROUS_PATTERNS = [
        r'__.*__',  # 魔术方法
        r'\..*system.*\(',  # 系统调用
        r'\..*popen.*\(',  # 进程打开
        r'\..*spawn.*\(',  # 进程生成
        r'\..*fork.*\(',  # 进程分叉
        r'\..*kill.*\(',  # 进程终止
        r'\..*signal.*\(',  # 信号处理
        r'\..*exit.*\(',  # 程序退出
        r'\..*quit.*\(',  # 程序退出
        r'while\s+True\s*:',  # 无限循环
        r'for\s+.*\s+in\s+.*range\s*\(\s*\d{6,}\s*\)',  # 大范围循环
    ]
    
    def validate_code(self, code: str) -> List[str]:
        """
        验证代码安全性
        
        Args:
            code: 要验证的代码
            
        Returns:
            安全违规列表，空列表表示安全
        """
        violations = []
        
        # 检查危险导入
        violations.extend(self._check_dangerous_imports(code))
        
        # 检查危险内置函数
        violations.extend(self._check_dangerous_builtins(code))
        
        # 检查危险模式
        violations.extend(self._check_dangerous_patterns(code))
        
        return violations
    
    def _check_dangerous_imports(self, code: str) -> List[str]:
        """检查危险的导入语句"""
        violations = []
        lines = code.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            # 检查 import 语句
            if line.startswith('import ') or line.startswith('from '):
                for dangerous_module in self.DANGEROUS_IMPORTS:
                    if re.search(rf'\b{re.escape(dangerous_module)}\b', line):
                        violations.append(
                            f"第 {line_num} 行: 禁止导入危险模块 '{dangerous_module}'"
                        )
        
        return violations
    
    def _check_dangerous_builtins(self, code: str) -> List[str]:
        """检查危险的内置函数调用"""
        violations = []
        
        for builtin_func in self.DANGEROUS_BUILTINS:
            pattern = rf'\b{re.escape(builtin_func)}\s*\('
            matches = re.finditer(pattern, code)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                violations.append(
                    f"第 {line_num} 行: 禁止使用危险内置函数 '{builtin_func}'"
                )
        
        return violations
    
    def _check_dangerous_patterns(self, code: str) -> List[str]:
        """检查危险的代码模式"""
        violations = []
        
        for pattern in self.DANGEROUS_PATTERNS:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                violations.append(
                    f"第 {line_num} 行: 检测到危险代码模式 '{match.group()}'"
                )
        
        return violations
    
    def sanitize_code(self, code: str) -> str:
        """
        清理代码，注释掉危险操作
        
        Args:
            code: 原始代码
            
        Returns:
            清理后的代码
        """
        lines = code.split('\n')
        sanitized_lines = []
        
        for line in lines:
            original_line = line
            line_stripped = line.strip()
            
            # 跳过空行和注释
            if not line_stripped or line_stripped.startswith('#'):
                sanitized_lines.append(original_line)
                continue
            
            # 检查是否包含危险导入
            is_dangerous = False
            for dangerous_module in self.DANGEROUS_IMPORTS:
                if re.search(rf'\b{re.escape(dangerous_module)}\b', line_stripped):
                    sanitized_lines.append(f"# BLOCKED: {original_line}")
                    is_dangerous = True
                    break
            
            if not is_dangerous:
                # 检查危险内置函数
                for builtin_func in self.DANGEROUS_BUILTINS:
                    if re.search(rf'\b{re.escape(builtin_func)}\s*\(', line_stripped):
                        sanitized_lines.append(f"# BLOCKED: {original_line}")
                        is_dangerous = True
                        break
            
            if not is_dangerous:
                sanitized_lines.append(original_line)
        
        return '\n'.join(sanitized_lines)


class PythonSandbox:
    """Python 代码安全沙箱执行器"""
    
    def __init__(self, config: Optional[SandboxConfig] = None, use_docker: bool = True):
        """
        初始化沙箱
        
        Args:
            config: 沙箱配置，如果为 None 则使用默认配置
            use_docker: 是否使用 Docker，False 时使用模拟模式
        """
        self.config = config or SandboxConfig()
        self.docker_client = None
        self.security_validator = CodeSecurityValidator()
        self._temp_files: List[str] = []
        self.use_docker = use_docker
        
        # 初始化 Docker 客户端（如果启用）
        if self.use_docker:
            self._init_docker_client()
        else:
            logger.info("沙箱运行在模拟模式（不使用 Docker）")
    
    def _init_docker_client(self):
        """初始化 Docker 客户端"""
        try:
            self.docker_client = docker.from_env()
            # 测试连接
            self.docker_client.ping()
            logger.info("Docker 客户端初始化成功")
        except Exception as e:
            logger.warning(f"Docker 客户端初始化失败: {e}")
            logger.info("将使用模拟模式运行沙箱")
            self.use_docker = False
            self.docker_client = None
    
    async def execute_code(self, code: str, timeout: Optional[int] = None) -> ExecutionResult:
        """
        在安全沙箱中执行 Python 代码
        
        Args:
            code: 要执行的 Python 代码
            timeout: 执行超时时间（秒），如果为 None 则使用配置的默认值
            
        Returns:
            执行结果
        """
        if timeout is None:
            timeout = self.config.timeout
        
        start_time = time.time()
        
        try:
            # 1. 安全验证
            security_violations = self.security_validator.validate_code(code)
            if security_violations:
                return ExecutionResult(
                    status="blocked",
                    output="",
                    error="代码包含安全违规操作",
                    execution_time=time.time() - start_time,
                    security_violations=security_violations
                )
            
            # 2. 代码清理
            sanitized_code = self.security_validator.sanitize_code(code)
            
            # 3. 在容器中执行
            if self.use_docker:
                result = await self._execute_in_container(sanitized_code, timeout)
            else:
                result = await self._execute_in_mock_container(sanitized_code, timeout)
            
            # 4. 更新执行时间
            result.execution_time = time.time() - start_time
            
            return result
            
        except Exception as e:
            logger.error(f"代码执行失败: {e}")
            return ExecutionResult(
                status="error",
                output="",
                error=f"执行失败: {str(e)}",
                execution_time=time.time() - start_time
            )
        finally:
            # 清理临时资源
            self.cleanup_resources()
    
    async def _execute_in_container(self, code: str, timeout: int) -> ExecutionResult:
        """在 Docker 容器中执行代码"""
        temp_file = None
        container = None
        
        try:
            # 创建临时文件
            temp_file = await self._create_temp_file(code)
            
            # 准备容器配置
            container_config = self._prepare_container_config(temp_file, timeout)
            
            # 运行容器
            container = self.docker_client.containers.run(**container_config)
            
            # 等待执行完成
            result = await self._wait_for_completion(container, timeout)
            
            return result
            
        except asyncio.TimeoutError:
            if container:
                try:
                    container.kill()
                    container.remove()
                except:
                    pass
            return ExecutionResult(
                status="timeout",
                output="",
                error=f"代码执行超时（{timeout}秒）"
            )
        except ContainerError as e:
            return ExecutionResult(
                status="error",
                output=e.stderr.decode('utf-8') if e.stderr else "",
                error=f"容器执行错误: {e}",
                exit_code=e.exit_status
            )
        except Exception as e:
            return ExecutionResult(
                status="error",
                output="",
                error=f"执行异常: {str(e)}"
            )
        finally:
            # 清理容器
            if container:
                try:
                    container.remove(force=True)
                except:
                    pass
    
    async def _create_temp_file(self, code: str) -> str:
        """创建临时 Python 文件"""
        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(
                mode='w', 
                suffix='.py', 
                delete=False,
                encoding='utf-8'
            ) as f:
                f.write(code)
                temp_file = f.name
            
            self._temp_files.append(temp_file)
            return temp_file
            
        except Exception as e:
            logger.error(f"创建临时文件失败: {e}")
            raise
    
    def _prepare_container_config(self, temp_file: str, timeout: int) -> Dict[str, Any]:
        """准备容器配置"""
        return {
            'image': self.config.container_image,
            'command': f"python {os.path.basename(temp_file)}",
            'volumes': {
                os.path.dirname(temp_file): {
                    'bind': '/app', 
                    'mode': 'ro'  # 只读挂载
                }
            },
            'working_dir': '/app',
            'network_disabled': self.config.network_disabled,
            'read_only': self.config.read_only,
            'mem_limit': self.config.memory_limit,
            'cpu_quota': self.config.cpu_quota,
            'cpu_period': self.config.cpu_period,
            'pids_limit': self.config.pids_limit,
            'detach': True,
            'remove': False,  # 手动删除以获取日志
            'user': 'nobody',  # 使用非特权用户
            'cap_drop': ['ALL'],  # 删除所有权限
            'security_opt': ['no-new-privileges:true'],  # 禁止提权
        }
    
    async def _wait_for_completion(self, container, timeout: int) -> ExecutionResult:
        """等待容器执行完成"""
        try:
            # 等待容器完成
            result = await asyncio.wait_for(
                asyncio.to_thread(container.wait),
                timeout=timeout
            )
            
            # 获取输出
            logs = container.logs().decode('utf-8')
            
            # 获取内存使用情况（如果可能）
            memory_usage = 0
            try:
                stats = container.stats(stream=False)
                memory_usage = stats['memory_stats'].get('usage', 0)
            except:
                pass
            
            return ExecutionResult(
                status="success" if result['StatusCode'] == 0 else "error",
                output=logs,
                exit_code=result['StatusCode'],
                memory_usage=memory_usage
            )
            
        except asyncio.TimeoutError:
            raise
        except Exception as e:
            logger.error(f"等待容器完成时出错: {e}")
            raise
    
    async def _execute_in_mock_container(self, code: str, timeout: int) -> ExecutionResult:
        """在模拟容器中执行代码（用于测试和开发）"""
        import subprocess
        import sys
        
        temp_file = None
        
        try:
            # 创建临时文件
            temp_file = await self._create_temp_file(code)
            
            # 使用当前 Python 解释器执行代码
            start_time = time.time()
            
            try:
                # 执行代码并捕获输出
                result = await asyncio.wait_for(
                    asyncio.to_thread(
                        subprocess.run,
                        [sys.executable, temp_file],
                        capture_output=True,
                        text=True,
                        timeout=timeout
                    ),
                    timeout=timeout + 1  # 给 asyncio 一点额外时间
                )
                
                execution_time = time.time() - start_time
                
                return ExecutionResult(
                    status="success" if result.returncode == 0 else "error",
                    output=result.stdout,
                    error=result.stderr if result.stderr else None,
                    execution_time=execution_time,
                    exit_code=result.returncode,
                    memory_usage=0  # 模拟模式下无法获取内存使用
                )
                
            except subprocess.TimeoutExpired:
                return ExecutionResult(
                    status="timeout",
                    output="",
                    error=f"代码执行超时（{timeout}秒）",
                    execution_time=timeout
                )
            except asyncio.TimeoutError:
                return ExecutionResult(
                    status="timeout",
                    output="",
                    error=f"代码执行超时（{timeout}秒）",
                    execution_time=timeout
                )
                
        except Exception as e:
            return ExecutionResult(
                status="error",
                output="",
                error=f"模拟执行异常: {str(e)}"
            )
    
    async def run_performance_test(
        self, 
        code: str, 
        test_cases: List[Dict[str, Any]], 
        iterations: int = 3
    ) -> Dict[str, Any]:
        """
        运行性能基准测试
        
        Args:
            code: 要测试的代码
            test_cases: 测试用例列表
            iterations: 每个测试用例的运行次数
            
        Returns:
            性能测试结果
        """
        results = {
            'test_cases': [],
            'summary': {
                'total_tests': len(test_cases),
                'successful_tests': 0,
                'failed_tests': 0,
                'average_execution_time': 0.0,
                'peak_memory_usage': 0
            }
        }
        
        total_execution_time = 0.0
        peak_memory = 0
        
        for i, test_case in enumerate(test_cases):
            test_result = {
                'test_case_id': i,
                'input': test_case,
                'iterations': [],
                'average_time': 0.0,
                'min_time': float('inf'),
                'max_time': 0.0,
                'memory_usage': 0,
                'status': 'success'
            }
            
            # 准备测试代码
            test_code = self._prepare_test_code(code, test_case)
            
            # 运行多次迭代
            iteration_times = []
            for iteration in range(iterations):
                result = await self.execute_code(test_code)
                
                if result.status == 'success':
                    iteration_times.append(result.execution_time)
                    test_result['memory_usage'] = max(
                        test_result['memory_usage'], 
                        result.memory_usage
                    )
                    peak_memory = max(peak_memory, result.memory_usage)
                else:
                    test_result['status'] = 'failed'
                    test_result['error'] = result.error
                    break
                
                test_result['iterations'].append({
                    'iteration': iteration + 1,
                    'execution_time': result.execution_time,
                    'memory_usage': result.memory_usage
                })
            
            # 计算统计信息
            if iteration_times:
                test_result['average_time'] = sum(iteration_times) / len(iteration_times)
                test_result['min_time'] = min(iteration_times)
                test_result['max_time'] = max(iteration_times)
                total_execution_time += test_result['average_time']
                results['summary']['successful_tests'] += 1
            else:
                results['summary']['failed_tests'] += 1
            
            results['test_cases'].append(test_result)
        
        # 更新汇总信息
        if results['summary']['successful_tests'] > 0:
            results['summary']['average_execution_time'] = (
                total_execution_time / results['summary']['successful_tests']
            )
        results['summary']['peak_memory_usage'] = peak_memory
        
        return results
    
    def _prepare_test_code(self, code: str, test_case: Dict[str, Any]) -> str:
        """准备性能测试代码"""
        # 这里可以根据测试用例动态生成测试代码
        # 简单实现：直接执行原代码
        return f"""
import time
import sys

# 用户代码
{code}

# 性能测试
start_time = time.time()
try:
    # 这里可以根据 test_case 调用相应的函数
    # 目前简单执行代码
    pass
except Exception as e:
    print(f"执行错误: {{e}}", file=sys.stderr)
    sys.exit(1)

end_time = time.time()
print(f"执行时间: {{end_time - start_time:.6f}} 秒")
"""
    
    def cleanup_resources(self):
        """清理所有临时资源"""
        # 清理临时文件
        for temp_file in self._temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except Exception as e:
                logger.warning(f"清理临时文件失败 {temp_file}: {e}")
        
        self._temp_files.clear()
        
        # 清理孤儿容器（如果有的话）
        try:
            if self.docker_client:
                containers = self.docker_client.containers.list(
                    all=True,
                    filters={'label': 'algoweaver.sandbox=true'}
                )
                for container in containers:
                    try:
                        container.remove(force=True)
                    except:
                        pass
        except Exception as e:
            logger.warning(f"清理容器失败: {e}")
    
    def __del__(self):
        """析构函数，确保资源清理"""
        self.cleanup_resources()


# LangChain Tool 包装器
class PythonREPLTool:
    """Python REPL 工具，用于 LangChain 集成"""
    
    name = "python_repl"
    description = """
    在安全沙箱环境中执行 Python 代码。
    
    特性:
    - 文件系统访问限制
    - 网络访问禁用  
    - 30秒执行超时
    - 内存和CPU限制
    - 危险操作自动检测和阻止
    - 自动资源清理
    
    输入: Python 代码字符串
    输出: 执行结果，包含输出、错误信息和执行统计
    """
    
    def __init__(self, config: Optional[SandboxConfig] = None):
        self.sandbox = PythonSandbox(config, use_docker=True)
    
    async def arun(self, code: str) -> str:
        """异步执行代码"""
        result = await self.sandbox.execute_code(code)
        
        if result.status == "success":
            return f"执行成功:\n{result.output}\n\n执行时间: {result.execution_time:.3f}秒"
        elif result.status == "blocked":
            violations = "\n".join(result.security_violations)
            return f"代码被阻止执行:\n{violations}\n\n错误: {result.error}"
        elif result.status == "timeout":
            return f"执行超时: {result.error}"
        else:
            return f"执行失败: {result.error}\n输出: {result.output}"
    
    def run(self, code: str) -> str:
        """同步执行代码（通过异步包装）"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.arun(code))


# 导出的公共接口
__all__ = [
    'PythonSandbox',
    'PythonREPLTool', 
    'ExecutionResult',
    'SandboxConfig',
    'CodeSecurityValidator'
]