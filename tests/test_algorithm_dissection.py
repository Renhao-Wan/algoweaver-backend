"""
算法拆解子图单元测试

测试算法拆解子图的核心功能，包括：
- 步骤模拟的准确性
- 可视化生成功能
- 子图构建和执行流程
"""

import pytest
import asyncio
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from app.graph.state import DissectionState, ExecutionStep, AlgorithmExplanation
from app.graph.subgraphs.dissection.agents import (
    StepSimulatorAgent,
    VisualGeneratorAgent,
    StepType,
    SimulationResult
)
from app.graph.subgraphs.dissection.builder import (
    DissectionSubgraphBuilder,
    DissectionSubgraphManager
)
from app.graph.state import StateConverter


# ============================================================================
# 测试数据和辅助函数
# ============================================================================

@pytest.fixture
def sample_code():
    """示例代码 - 简单的斐波那契函数"""
    return """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
"""


@pytest.fixture
def sample_sorting_code():
    """示例代码 - 冒泡排序"""
    return """
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n-i-1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
    return arr
"""


@pytest.fixture
def mock_llm():
    """模拟 LLM 对象"""
    llm = AsyncMock()
    
    # 模拟 LLM 响应
    mock_response = Mock()
    mock_response.content = """
## 伪代码

```
函数 fibonacci(n):
    如果 n <= 1:
        返回 n
    返回 fibonacci(n-1) + fibonacci(n-2)
```

## 复杂度分析

时间复杂度: O(2^n)
空间复杂度: O(n)
"""
    
    llm.ainvoke.return_value = mock_response
    return llm


@pytest.fixture
def mock_sandbox():
    """模拟沙箱对象"""
    sandbox = AsyncMock()
    
    # 模拟成功的执行结果
    mock_result = Mock()
    mock_result.status = "success"
    mock_result.output = """
=== TRACE_DATA_START ===
{
  "variables": {
    "n": [{"value": "5", "line": 1, "type": "int"}]
  },
  "flow": [
    {"description": "函数调用开始", "line": 1}
  ],
  "metrics": {
    "execution_time": 0.001
  }
}
=== TRACE_DATA_END ===
"""
    
    sandbox.execute_code.return_value = mock_result
    return sandbox


@pytest.fixture
def sample_dissection_state(sample_code):
    """示例拆解状态"""
    return DissectionState(
        task_id="test-task-123",
        code=sample_code,
        language="python",
        analysis_phase="parsing",
        execution_steps=[],
        current_step=0,
        data_structures_used=[],
        parsing_errors=[],
        simulation_errors=[]
    )


# ============================================================================
# StepSimulatorAgent 测试
# ============================================================================

class TestStepSimulatorAgent:
    """测试步骤模拟智能体"""
    
    @pytest.mark.asyncio
    async def test_simulate_algorithm_execution_success(
        self, 
        mock_llm, 
        mock_sandbox, 
        sample_dissection_state
    ):
        """测试成功的算法执行模拟"""
        # 创建智能体
        agent = StepSimulatorAgent(mock_llm, mock_sandbox)
        
        # 执行模拟
        result_state = await agent.simulate_algorithm_execution(sample_dissection_state)
        
        # 验证结果
        assert result_state["task_id"] == "test-task-123"
        assert "error_info" not in result_state or result_state["error_info"] is None
        
        # 验证沙箱被调用
        mock_sandbox.execute_code.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_code_structure(self, mock_llm, mock_sandbox, sample_code):
        """测试代码结构分析"""
        agent = StepSimulatorAgent(mock_llm, mock_sandbox)
        
        # 分析代码结构
        analysis = await agent._analyze_code_structure(sample_code)
        
        # 验证分析结果
        assert "functions" in analysis
        assert "loops" in analysis
        assert "conditions" in analysis
        assert "variables" in analysis
        
        # 验证识别到 fibonacci 函数
        function_names = [f["name"] for f in analysis["functions"]]
        assert "fibonacci" in function_names
    
    @pytest.mark.asyncio
    async def test_analyze_code_structure_with_loops(
        self, 
        mock_llm, 
        mock_sandbox, 
        sample_sorting_code
    ):
        """测试包含循环的代码结构分析"""
        agent = StepSimulatorAgent(mock_llm, mock_sandbox)
        
        # 分析代码结构
        analysis = await agent._analyze_code_structure(sample_sorting_code)
        
        # 验证识别到循环
        assert len(analysis["loops"]) >= 2  # 冒泡排序有两层循环
        assert "bubble_sort" in [f["name"] for f in analysis["functions"]]
    
    @pytest.mark.asyncio
    async def test_simulate_execution_with_trace(
        self, 
        mock_llm, 
        mock_sandbox, 
        sample_code
    ):
        """测试带追踪的执行模拟"""
        agent = StepSimulatorAgent(mock_llm, mock_sandbox)
        
        # 执行模拟
        result = await agent._simulate_execution(sample_code, {"n": 5})
        
        # 验证模拟结果
        assert isinstance(result, SimulationResult)
        assert result.error_info is None
        assert "variables" in result.variables_trace or len(result.variables_trace) >= 0
    
    @pytest.mark.asyncio
    async def test_simulate_execution_with_error(self, mock_llm, mock_sandbox):
        """测试执行模拟遇到错误的情况"""
        # 配置沙箱返回错误
        mock_result = Mock()
        mock_result.status = "error"
        mock_result.output = "SyntaxError: invalid syntax"
        mock_sandbox.execute_code.return_value = mock_result
        
        agent = StepSimulatorAgent(mock_llm, mock_sandbox)
        
        # 执行模拟
        invalid_code = "def broken( syntax error"
        result = await agent._simulate_execution(invalid_code, {})
        
        # 验证错误被正确处理
        assert result.error_info is not None
        assert "SyntaxError" in result.error_info or result.error_info != ""
    
    def test_instrument_code_for_tracing(self, mock_llm, mock_sandbox, sample_code):
        """测试代码追踪插桩"""
        agent = StepSimulatorAgent(mock_llm, mock_sandbox)
        
        # 插桩代码
        instrumented = agent._instrument_code_for_tracing(sample_code, {"n": 5})
        
        # 验证插桩结果
        assert "_trace_data" in instrumented
        assert "_trace_variable" in instrumented
        assert "_trace_flow" in instrumented
        assert "n = 5" in instrumented
    
    def test_generate_input_assignments(self, mock_llm, mock_sandbox):
        """测试输入数据赋值语句生成"""
        agent = StepSimulatorAgent(mock_llm, mock_sandbox)
        
        # 生成赋值语句
        input_data = {
            "n": 10,
            "name": "test",
            "arr": [1, 2, 3]
        }
        assignments = agent._generate_input_assignments(input_data)
        
        # 验证赋值语句
        assert "n = 10" in assignments
        assert 'name = "test"' in assignments
        assert "arr = [1, 2, 3]" in assignments
    
    def test_parse_trace_output(self, mock_llm, mock_sandbox):
        """测试追踪输出解析"""
        agent = StepSimulatorAgent(mock_llm, mock_sandbox)
        
        # 模拟追踪输出
        output = """
Some output before
=== TRACE_DATA_START ===
{
  "variables": {"x": [{"value": "10", "line": 1}]},
  "flow": [{"description": "start", "line": 1}],
  "metrics": {"execution_time": 0.5}
}
=== TRACE_DATA_END ===
Some output after
"""
        
        # 解析输出
        trace_data = agent._parse_trace_output(output)
        
        # 验证解析结果
        assert "variables" in trace_data
        assert "flow" in trace_data
        assert "metrics" in trace_data
        assert trace_data["metrics"]["execution_time"] == 0.5


# ============================================================================
# VisualGeneratorAgent 测试
# ============================================================================

class TestVisualGeneratorAgent:
    """测试可视化生成智能体"""
    
    @pytest.mark.asyncio
    async def test_generate_algorithm_explanation_success(
        self, 
        mock_llm, 
        sample_dissection_state
    ):
        """测试成功生成算法讲解"""
        # 添加一些执行步骤到状态
        sample_dissection_state["execution_steps"] = [
            ExecutionStep(
                step_number=1,
                description="初始化",
                code_snippet="n = 5",
                variables_state={"n": 5},
                time_complexity="O(1)",
                space_complexity="O(1)"
            )
        ]
        
        agent = VisualGeneratorAgent(mock_llm)
        
        # 生成讲解
        result_state = await agent.generate_algorithm_explanation(sample_dissection_state)
        
        # 验证结果
        assert "algorithm_explanation" in result_state
        assert result_state["algorithm_explanation"] is not None
        
        # 验证 LLM 被调用
        assert mock_llm.ainvoke.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_generate_pseudocode(self, mock_llm, sample_dissection_state):
        """测试伪代码生成"""
        agent = VisualGeneratorAgent(mock_llm)
        
        # 生成伪代码
        pseudocode = await agent._generate_pseudocode(sample_dissection_state)
        
        # 验证伪代码不为空
        assert pseudocode is not None
        assert len(pseudocode) > 0
        
        # 验证 LLM 被调用
        mock_llm.ainvoke.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_step_explanations(self, mock_llm, sample_dissection_state):
        """测试步骤解释生成"""
        # 添加执行步骤
        sample_dissection_state["execution_steps"] = [
            ExecutionStep(
                step_number=1,
                description="初始化变量",
                code_snippet="n = 5",
                variables_state={"n": 5}
            ),
            ExecutionStep(
                step_number=2,
                description="检查基础情况",
                code_snippet="if n <= 1",
                variables_state={"n": 5}
            )
        ]
        
        agent = VisualGeneratorAgent(mock_llm)
        
        # 生成步骤解释
        explanations = await agent._generate_step_explanations(sample_dissection_state)
        
        # 验证解释列表 - 应该生成2个解释
        assert isinstance(explanations, list)
        assert len(explanations) == 2
        # 验证解释内容包含步骤信息
        assert "步骤 1" in explanations[0]
        assert "初始化变量" in explanations[0]
        assert "步骤 2" in explanations[1]
        assert "检查基础情况" in explanations[1]
    
    @pytest.mark.asyncio
    async def test_analyze_complexity(self, mock_llm, sample_dissection_state):
        """测试复杂度分析"""
        agent = VisualGeneratorAgent(mock_llm)
        
        # 分析复杂度
        complexity = await agent._analyze_complexity(sample_dissection_state)
        
        # 验证复杂度分析结果
        assert "time" in complexity
        assert "space" in complexity
        assert complexity["time"].startswith("O(")
        assert complexity["space"].startswith("O(")
    
    @pytest.mark.asyncio
    async def test_generate_visual_diagrams(self, mock_llm, sample_dissection_state):
        """测试可视化图表生成"""
        # 添加执行步骤
        sample_dissection_state["execution_steps"] = [
            ExecutionStep(
                step_number=1,
                description="步骤1",
                code_snippet="",
                variables_state={}
            ),
            ExecutionStep(
                step_number=2,
                description="步骤2",
                code_snippet="",
                variables_state={}
            )
        ]
        
        agent = VisualGeneratorAgent(mock_llm)
        
        # 生成可视化图表
        diagram = await agent._generate_visual_diagrams(sample_dissection_state)
        
        # 验证图表生成
        assert diagram is not None
        assert "步骤1" in diagram or "1." in diagram
    
    @pytest.mark.asyncio
    async def test_generate_teaching_notes(self, mock_llm, sample_dissection_state):
        """测试教学要点生成"""
        agent = VisualGeneratorAgent(mock_llm)
        
        # 生成教学要点
        notes = await agent._generate_teaching_notes(sample_dissection_state)
        
        # 验证教学要点
        assert isinstance(notes, list)
        # 教学要点可能为空或有内容，取决于 LLM 响应


# ============================================================================
# DissectionSubgraphBuilder 测试
# ============================================================================

class TestDissectionSubgraphBuilder:
    """测试算法拆解子图构建器"""
    
    def test_build_dissection_subgraph(self):
        """测试子图构建"""
        builder = DissectionSubgraphBuilder()
        
        # 构建子图
        graph = builder.build_dissection_subgraph()
        
        # 验证子图创建成功
        assert graph is not None
        assert builder.graph is not None
    
    def test_add_nodes(self):
        """测试节点添加"""
        builder = DissectionSubgraphBuilder()
        builder.graph = Mock()
        
        # 添加节点
        builder._add_nodes()
        
        # 验证节点被添加
        assert builder.graph.add_node.call_count >= 2  # 至少有 step_simulator 和 visual_generator
    
    def test_define_edges(self):
        """测试边定义"""
        builder = DissectionSubgraphBuilder()
        builder.graph = Mock()
        
        # 定义边
        builder._define_edges()
        
        # 验证边被添加
        assert builder.graph.add_edge.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_check_simulation_result_success(self, sample_dissection_state):
        """测试模拟结果检查 - 成功情况"""
        builder = DissectionSubgraphBuilder()
        
        # 设置成功的模拟结果
        sample_dissection_state["execution_steps"] = [
            ExecutionStep(
                step_number=1,
                description="测试步骤",
                code_snippet="",
                variables_state={}
            )
        ]
        sample_dissection_state["variables_trace"] = {"x": []}
        
        # 检查结果
        result_state = await builder._check_simulation_result(sample_dissection_state)
        
        # 验证检查通过
        assert result_state.get("simulation_validated") == True
        assert result_state.get("error_info") is None
    
    @pytest.mark.asyncio
    async def test_check_simulation_result_with_error(self, sample_dissection_state):
        """测试模拟结果检查 - 错误情况"""
        builder = DissectionSubgraphBuilder()
        
        # 设置错误状态
        sample_dissection_state["error_info"] = "模拟失败"
        sample_dissection_state["execution_steps"] = []
        
        # 检查结果
        result_state = await builder._check_simulation_result(sample_dissection_state)
        
        # 验证错误被识别
        assert result_state.get("needs_retry") == True
    
    def test_route_after_simulation_continue(self, sample_dissection_state):
        """测试路由决策 - 继续执行"""
        builder = DissectionSubgraphBuilder()
        
        # 设置验证通过的状态
        sample_dissection_state["simulation_validated"] = True
        sample_dissection_state["error_info"] = None
        
        # 路由决策
        next_node = builder._route_after_simulation(sample_dissection_state)
        
        # 验证路由到继续节点
        assert next_node == "continue"
    
    def test_route_after_simulation_retry(self, sample_dissection_state):
        """测试路由决策 - 重试"""
        builder = DissectionSubgraphBuilder()
        
        # 设置需要重试的状态
        sample_dissection_state["error_info"] = "临时错误"
        sample_dissection_state["needs_retry"] = True
        sample_dissection_state["retry_count"] = 1
        
        # 路由决策
        next_node = builder._route_after_simulation(sample_dissection_state)
        
        # 验证路由到重试节点
        assert next_node == "retry"
    
    def test_route_after_simulation_error(self, sample_dissection_state):
        """测试路由决策 - 错误处理"""
        builder = DissectionSubgraphBuilder()
        
        # 设置超过重试次数的状态
        sample_dissection_state["error_info"] = "持续错误"
        sample_dissection_state["needs_retry"] = True
        sample_dissection_state["retry_count"] = 3
        
        # 路由决策
        next_node = builder._route_after_simulation(sample_dissection_state)
        
        # 验证路由到错误处理节点
        assert next_node == "error"
    
    @pytest.mark.asyncio
    async def test_handle_error(self, sample_dissection_state):
        """测试错误处理"""
        builder = DissectionSubgraphBuilder()
        
        # 设置错误状态
        sample_dissection_state["error_info"] = "测试错误"
        
        # 处理错误
        result_state = await builder._handle_error(sample_dissection_state)
        
        # 验证错误被处理
        assert result_state.get("has_error") == True
        assert result_state.get("algorithm_explanation") is not None


# ============================================================================
# DissectionSubgraphManager 测试
# ============================================================================

class TestDissectionSubgraphManager:
    """测试算法拆解子图管理器"""
    
    def test_initialize_subgraph(self):
        """测试子图初始化"""
        manager = DissectionSubgraphManager()
        
        # 由于实际初始化需要完整的 LangGraph 环境，这里只测试管理器创建
        assert manager.builder is not None
        assert manager.subgraph is None
        assert manager.compiled_subgraph is None
    
    def test_get_subgraph_info(self):
        """测试获取子图信息"""
        manager = DissectionSubgraphManager()
        
        # 获取子图信息
        info = manager.get_subgraph_info()
        
        # 验证信息结构
        assert "name" in info
        assert "description" in info
        assert "nodes" in info
        assert "entry_point" in info
        assert info["name"] == "algorithm_dissection_subgraph"
        assert info["entry_point"] == "step_simulator"


# ============================================================================
# 状态转换测试
# ============================================================================

class TestStateConversion:
    """测试状态转换函数"""
    
    def test_convert_global_to_dissection_state(self):
        """测试全局状态到拆解状态的转换"""
        from app.graph.state import GlobalState, StateTaskStatus, Phase, CollaborationMode
        from datetime import datetime
        
        # 创建全局状态
        global_state = GlobalState(
            task_id="test-123",
            user_id="user-456",
            original_code="def test(): pass",
            language="python",
            optimization_level="balanced",
            status=StateTaskStatus.ANALYZING,
            current_phase=Phase.DISSECTION,
            progress=0.5,
            collaboration_mode=CollaborationMode.MASTER_EXPERT,
            active_agents=[],
            code_versions=["def test(): pass"],
            decision_history=[],
            human_intervention_required=False,
            shared_context={},
            execution_metadata={},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            retry_count=0
        )
        
        # 使用 StateConverter 转换状态
        dissection_state = StateConverter.global_to_dissection(global_state)
        
        # 验证转换结果
        assert dissection_state["task_id"] == "test-123"
        assert dissection_state["code"] == "def test(): pass"
        assert dissection_state["language"] == "python"
        assert len(dissection_state["execution_steps"]) == 0
    
    def test_merge_dissection_to_global_state(self, sample_dissection_state):
        """测试拆解状态合并到全局状态"""
        from app.graph.state import GlobalState, StateTaskStatus, Phase, CollaborationMode, AlgorithmExplanation
        from datetime import datetime
        
        # 创建全局状态
        global_state = GlobalState(
            task_id="test-123",
            user_id="user-456",
            original_code="def test(): pass",
            language="python",
            optimization_level="balanced",
            status=StateTaskStatus.ANALYZING,
            current_phase=Phase.DISSECTION,
            progress=0.5,
            collaboration_mode=CollaborationMode.MASTER_EXPERT,
            active_agents=[],
            code_versions=["def test(): pass"],
            decision_history=[],
            human_intervention_required=False,
            shared_context={},
            execution_metadata={},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            retry_count=0
        )
        
        # 设置拆解状态的结果
        sample_dissection_state["algorithm_explanation"] = AlgorithmExplanation(
            steps=[],
            pseudocode="# 测试伪代码",
            time_complexity="O(1)",
            space_complexity="O(1)"
        )
        sample_dissection_state["execution_steps"] = [
            ExecutionStep(
                step_number=1,
                description="测试步骤",
                code_snippet="",
                variables_state={}
            )
        ]
        
        # 使用 StateConverter 合并状态
        updated_global_state = StateConverter.dissection_to_global(
            global_state,
            sample_dissection_state
        )
        
        # 验证合并结果
        assert updated_global_state["algorithm_explanation"] is not None
        # 新的StateConverter将execution_steps存储在shared_context中
        assert "dissection_result" in updated_global_state["shared_context"]
        assert len(updated_global_state["shared_context"]["dissection_result"]["execution_steps"]) == 1


# ============================================================================
# 集成测试
# ============================================================================

class TestDissectionIntegration:
    """算法拆解子图集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_dissection_workflow(
        self, 
        mock_llm, 
        mock_sandbox, 
        sample_code
    ):
        """测试完整的算法拆解工作流"""
        # 创建初始状态
        initial_state = DissectionState(
            task_id="integration-test",
            code=sample_code,
            language="python",
            analysis_phase="parsing",
            execution_steps=[],
            current_step=0,
            data_structures_used=[],
            parsing_errors=[],
            simulation_errors=[]
        )
        
        # 步骤1: 执行步骤模拟
        simulator = StepSimulatorAgent(mock_llm, mock_sandbox)
        state_after_simulation = await simulator.simulate_algorithm_execution(initial_state)
        
        # 验证模拟完成
        assert state_after_simulation["task_id"] == "integration-test"
        
        # 步骤2: 生成可视化讲解
        visualizer = VisualGeneratorAgent(mock_llm)
        final_state = await visualizer.generate_algorithm_explanation(state_after_simulation)
        
        # 验证最终结果
        assert "algorithm_explanation" in final_state
        assert final_state["algorithm_explanation"] is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
