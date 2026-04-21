"""
算法拆解子图 Agent 核心逻辑

本模块实现算法拆解子图中的 Agent 类，包括：
- StepSimulatorAgent: 算法步骤模拟智能体
- VisualGeneratorAgent: 可视化生成智能体
"""

import json
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

from langchain_core.messages import HumanMessage

from app.graph.state import DissectionState, ExecutionStep, AlgorithmExplanation
from app.graph.tools.python_repl import PythonSandbox
from app.graph.subgraphs.dissection.agents.prompts import (
    get_simulation_prompt,
    get_visualization_prompt,
    get_pseudocode_generation_prompt,
    get_complexity_analysis_prompt,
    get_teaching_notes_prompt
)
from app.core.logger import get_logger

logger = get_logger(__name__)


class StepType(str, Enum):
    """执行步骤类型枚举"""
    INITIALIZATION = "initialization"
    ITERATION = "iteration"
    CONDITION_CHECK = "condition_check"
    OPERATION = "operation"
    RETURN = "return"


class ComplexityType(str, Enum):
    """复杂度类型枚举"""
    TIME = "time"
    SPACE = "space"


@dataclass
class SimulationResult:
    """算法模拟结果"""
    steps: List[ExecutionStep]
    variables_trace: Dict[str, List[Any]]
    execution_flow: List[str]
    performance_metrics: Dict[str, Any]
    error_info: Optional[str] = None


@dataclass
class VisualizationOutput:
    """可视化输出结果"""
    pseudocode: str
    step_explanations: List[str]
    complexity_analysis: Dict[str, str]
    visual_diagrams: Optional[str] = None
    teaching_notes: List[str] = None


class StepSimulatorAgent:
    """
    算法步骤模拟智能体

    负责分析代码并模拟算法的逐步执行过程，追踪变量变化和执行流程。
    """

    def __init__(self, llm, sandbox: PythonSandbox):
        self.llm = llm
        self.sandbox = sandbox
        self.simulation_prompt = get_simulation_prompt()

    async def simulate_algorithm_execution(self, state: DissectionState) -> DissectionState:
        """
        模拟算法执行过程

        Args:
            state: 当前拆解状态

        Returns:
            更新后的拆解状态，包含模拟结果
        """
        try:
            logger.info(f"开始模拟算法执行，代码长度: {len(state['code'])} 字符")

            # 1. 静态代码分析
            static_analysis = await self._analyze_code_structure(state['code'])

            # 2. 动态执行模拟
            simulation_result = await self._simulate_execution(
                state['code'],
                state.get('input_data') or {}
            )

            # 3. 生成执行步骤
            execution_steps = await self._generate_execution_steps(
                state['code'],
                simulation_result,
                static_analysis
            )

            # 4. 更新状态
            state['execution_steps'] = execution_steps
            state['variables_trace'] = simulation_result.variables_trace
            state['execution_flow'] = simulation_result.execution_flow
            state['performance_metrics'] = simulation_result.performance_metrics

            logger.info(f"算法模拟完成，生成 {len(execution_steps)} 个执行步骤")
            return state

        except Exception as e:
            logger.error(f"算法模拟失败: {str(e)}")
            state['error_info'] = f"算法模拟失败: {str(e)}"
            return state

    async def _analyze_code_structure(self, code: str) -> Dict[str, Any]:
        """分析代码结构"""
        try:
            # 使用 AST 分析代码结构
            import ast

            tree = ast.parse(code)

            analysis = {
                "functions": [],
                "classes": [],
                "loops": [],
                "conditions": [],
                "variables": set(),
                "imports": []
            }

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    analysis["functions"].append({
                        "name": node.name,
                        "args": [arg.arg for arg in node.args.args],
                        "line": node.lineno
                    })
                elif isinstance(node, ast.ClassDef):
                    analysis["classes"].append({
                        "name": node.name,
                        "line": node.lineno
                    })
                elif isinstance(node, (ast.For, ast.While)):
                    analysis["loops"].append({
                        "type": type(node).__name__,
                        "line": node.lineno
                    })
                elif isinstance(node, ast.If):
                    analysis["conditions"].append({
                        "line": node.lineno
                    })
                elif isinstance(node, ast.Name):
                    analysis["variables"].add(node.id)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        analysis["imports"].append(alias.name)

            analysis["variables"] = list(analysis["variables"])
            return analysis

        except Exception as e:
            logger.warning(f"代码结构分析失败: {str(e)}")
            return {}

    async def _simulate_execution(self, code: str, input_data: Dict[str, Any]) -> SimulationResult:
        """模拟代码执行"""
        try:
            # 构建执行代码，添加追踪逻辑
            instrumented_code = self._instrument_code_for_tracing(code, input_data)

            # 在沙箱中执行
            execution_result = await self.sandbox.execute_code(instrumented_code)

            if execution_result.status == "success":
                # 解析追踪结果
                trace_data = self._parse_trace_output(execution_result.output)

                return SimulationResult(
                    steps=[],  # 将在后续步骤中生成
                    variables_trace=trace_data.get("variables", {}),
                    execution_flow=trace_data.get("flow", []),
                    performance_metrics=trace_data.get("metrics", {}),
                    error_info=None
                )
            else:
                return SimulationResult(
                    steps=[],
                    variables_trace={},
                    execution_flow=[],
                    performance_metrics={},
                    error_info=execution_result.output
                )

        except Exception as e:
            logger.error(f"执行模拟失败: {str(e)}")
            return SimulationResult(
                steps=[],
                variables_trace={},
                execution_flow=[],
                performance_metrics={},
                error_info=str(e)
            )

    def _instrument_code_for_tracing(self, code: str, input_data: Dict[str, Any]) -> str:
        """为代码添加追踪逻辑"""
        # 简化的追踪实现，实际项目中可以使用更复杂的 AST 转换
        instrumented = f"""
import json
import time
import sys
from typing import Any, Dict, List

# 追踪数据存储
_trace_data = {{
    "variables": {{}},
    "flow": [],
    "metrics": {{}}
}}

def _trace_variable(name: str, value: Any, line: int):
    \"\"\"追踪变量变化\"\"\"
    if name not in _trace_data["variables"]:
        _trace_data["variables"][name] = []
    _trace_data["variables"][name].append({{
        "value": str(value),
        "line": line,
        "type": type(value).__name__
    }})

def _trace_flow(description: str, line: int):
    \"\"\"追踪执行流程\"\"\"
    _trace_data["flow"].append({{
        "description": description,
        "line": line
    }})

# 输入数据
{self._generate_input_assignments(input_data)}

# 开始执行计时
_start_time = time.time()

# 原始代码（需要手动添加追踪调用）
{code}

# 结束计时
_end_time = time.time()
_trace_data["metrics"]["execution_time"] = _end_time - _start_time

# 输出追踪数据
print("=== TRACE_DATA_START ===")
print(json.dumps(_trace_data, ensure_ascii=False, indent=2))
print("=== TRACE_DATA_END ===")
"""
        return instrumented

    def _generate_input_assignments(self, input_data: Dict[str, Any]) -> str:
        """生成输入数据赋值语句"""
        assignments = []
        for key, value in input_data.items():
            if isinstance(value, str):
                assignments.append(f'{key} = "{value}"')
            else:
                assignments.append(f'{key} = {repr(value)}')
        return '\n'.join(assignments)

    def _parse_trace_output(self, output: str) -> Dict[str, Any]:
        """解析追踪输出"""
        try:
            start_marker = "=== TRACE_DATA_START ==="
            end_marker = "=== TRACE_DATA_END ==="

            start_idx = output.find(start_marker)
            end_idx = output.find(end_marker)

            if start_idx != -1 and end_idx != -1:
                trace_json = output[start_idx + len(start_marker):end_idx].strip()
                return json.loads(trace_json)
            else:
                logger.warning("未找到追踪数据标记")
                return {}

        except Exception as e:
            logger.error(f"解析追踪数据失败: {str(e)}")
            return {}

    async def _generate_execution_steps(
        self,
        code: str,
        simulation_result: SimulationResult,
        static_analysis: Dict[str, Any]
    ) -> List[ExecutionStep]:
        """生成执行步骤"""
        try:
            # 使用 LLM 生成详细的执行步骤
            prompt_input = {
                "code": code,
                "input_data": json.dumps(simulation_result.variables_trace, ensure_ascii=False)
            }

            response = await self.llm.ainvoke(
                self.simulation_prompt.format_messages(**prompt_input)
            )

            # 解析 LLM 响应并生成执行步骤
            steps = self._parse_llm_steps_response(response.content)

            return steps

        except Exception as e:
            logger.error(f"生成执行步骤失败: {str(e)}")
            return []

    def _parse_llm_steps_response(self, response: str) -> List[ExecutionStep]:
        """解析 LLM 生成的步骤响应"""
        # 简化的解析实现，实际项目中可以使用结构化输出
        steps = []

        # TODO 这里应该实现更复杂的解析逻辑
        # 暂时返回示例步骤
        steps.append(ExecutionStep(
            step_number=1,
            step_type=StepType.INITIALIZATION.value,
            description="算法初始化",
            code_line=1,
            variables_state={},
            explanation="开始执行算法"
        ))

        return steps


class VisualGeneratorAgent:
    """
    可视化生成智能体

    负责根据算法模拟结果生成可视化的伪代码讲解和教学材料。
    """

    def __init__(self, llm):
        self.llm = llm
        self.visualization_prompt = get_visualization_prompt()

    async def generate_algorithm_explanation(self, state: DissectionState) -> DissectionState:
        """
        生成算法讲解

        Args:
            state: 当前拆解状态

        Returns:
            更新后的拆解状态，包含可视化讲解
        """
        try:
            logger.info("开始生成算法可视化讲解")

            # 1. 生成伪代码
            pseudocode = await self._generate_pseudocode(state)

            # 2. 生成步骤解释
            step_explanations = await self._generate_step_explanations(state)

            # 3. 分析复杂度
            complexity_analysis = await self._analyze_complexity(state)

            # 4. 生成可视化图表（如果适用）
            visual_diagrams = await self._generate_visual_diagrams(state)

            # 5. 生成教学要点
            teaching_notes = await self._generate_teaching_notes(state)

            # 6. 组装算法讲解
            explanation = AlgorithmExplanation(
                steps=state.get('execution_steps') or [],
                pseudocode=pseudocode,
                time_complexity=complexity_analysis.get("time", "O(?)"),
                space_complexity=complexity_analysis.get("space", "O(?)"),
                visualization=visual_diagrams,
                step_explanations=step_explanations,
                teaching_notes=teaching_notes
            )

            state['algorithm_explanation'] = explanation
            state['analysis_phase'] = "completed"

            logger.info("算法可视化讲解生成完成")
            return state

        except Exception as e:
            logger.error(f"生成算法讲解失败: {str(e)}")
            state['error_info'] = f"生成算法讲解失败: {str(e)}"
            return state

    async def _generate_pseudocode(self, state: DissectionState) -> str:
        """生成伪代码"""
        try:
            # 使用 LLM 生成结构化伪代码
            prompt = get_pseudocode_generation_prompt().format(code=state['code'])

            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            return response.content.strip()

        except Exception as e:
            logger.error(f"生成伪代码失败: {str(e)}")
            return "# 伪代码生成失败"

    async def _generate_step_explanations(self, state: DissectionState) -> List[str]:
        """生成步骤解释"""
        try:
            explanations = []

            for i, step in enumerate(state.get('execution_steps') or [], 1):
                explanation = f"步骤 {i}: {step.description}"
                explanations.append(explanation)

            return explanations

        except Exception as e:
            logger.error(f"生成步骤解释失败: {str(e)}")
            return []

    async def _analyze_complexity(self, state: DissectionState) -> Dict[str, str]:
        """分析算法复杂度"""
        try:
            prompt = get_complexity_analysis_prompt().format(code=state['code'])

            response = await self.llm.ainvoke([HumanMessage(content=prompt)])

            # 简化的复杂度提取，实际项目中可以使用更复杂的解析
            content = response.content.lower()

            time_complexity = "O(?)"
            space_complexity = "O(?)"

            # 尝试提取复杂度信息
            import re
            time_match = re.search(r'时间复杂度.*?o\(([^)]+)\)', content)
            space_match = re.search(r'空间复杂度.*?o\(([^)]+)\)', content)

            if time_match:
                time_complexity = f"O({time_match.group(1)})"
            if space_match:
                space_complexity = f"O({space_match.group(1)})"

            return {
                "time": time_complexity,
                "space": space_complexity,
                "analysis": response.content
            }

        except Exception as e:
            logger.error(f"复杂度分析失败: {str(e)}")
            return {"time": "O(?)", "space": "O(?)"}

    async def _generate_visual_diagrams(self, state: DissectionState) -> Optional[str]:
        """生成可视化图表"""
        try:
            # 这里可以集成图表生成库，如 matplotlib, graphviz 等
            # 暂时返回文本描述

            execution_steps = state.get('execution_steps')
            if not execution_steps:
                return None

            diagram = "## 算法执行流程图\n\n"
            diagram += "```\n"

            for i, step in enumerate(execution_steps, 1):
                diagram += f"{i}. {step.description}\n"
                if i < len(execution_steps):
                    diagram += "   ↓\n"

            diagram += "```\n"

            return diagram

        except Exception as e:
            logger.error(f"生成可视化图表失败: {str(e)}")
            return None

    async def _generate_teaching_notes(self, state: DissectionState) -> List[str]:
        """生成教学要点"""
        try:
            prompt = get_teaching_notes_prompt().format(code=state['code'])

            response = await self.llm.ainvoke([HumanMessage(content=prompt)])

            # 简单解析教学要点
            notes = []
            lines = response.content.split('\n')

            for line in lines:
                line = line.strip()
                if line and (line.startswith('-') or line.startswith('•') or line[0].isdigit()):
                    # 清理格式标记
                    clean_line = re.sub(r'^[-•\d.\s]+', '', line).strip()
                    if clean_line:
                        notes.append(clean_line)

            return notes[:10]  # 限制数量

        except Exception as e:
            logger.error(f"生成教学要点失败: {str(e)}")
            return []
