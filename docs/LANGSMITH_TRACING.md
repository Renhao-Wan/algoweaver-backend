# LangSmith 与 LangGraph Studio 全链路追踪集成指南

## 概述

AlgoWeaver AI 系统已集成 LangSmith 全链路追踪功能，可以记录和追踪整个系统的执行过程，包括：

- 智能体执行追踪（Supervisor、Dissection、Review 等）
- 图节点执行追踪（主图和子图）
- 错误和异常追踪
- 性能指标统计（执行时间、状态变化等）

## 配置 LangSmith 追踪

### 1. 环境变量配置

在 `.env.dev` 文件中配置以下环境变量：

```bash
# LangSmith 追踪配置
LANGSMITH_API_KEY=your_langsmith_api_key_here
LANGSMITH_PROJECT=algoweaver-ai
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_TRACING=true
```

### 2. 获取 LangSmith API Key

1. 访问 [LangSmith](https://smith.langchain.com/)
2. 注册或登录账号
3. 在设置页面生成 API Key
4. 将 API Key 填入 `.env.dev` 文件

### 3. 启用追踪

追踪功能会在应用启动时自动启用（如果配置了 API Key）。启动日志会显示：

```
LangSmith 追踪已启用
```

## 追踪功能特性

### 1. 智能体执行追踪

系统会自动追踪所有智能体的执行过程，包括：

- **智能体名称**：supervisor、step_simulator、visual_generator 等
- **智能体类型**：supervisor、dissection、review
- **执行阶段**：analyze_task、simulate_steps、detect_mistakes 等
- **输入输出**：智能体的输入参数和输出结果
- **执行时间**：每个智能体的执行耗时（毫秒）
- **错误信息**：如果执行失败，记录详细的错误信息

示例日志：

```json
{
  "timestamp": "2026-04-22T10:30:45.123Z",
  "level": "INFO",
  "message": "智能体执行: supervisor (supervisor) - analyze_task",
  "agent_name": "supervisor",
  "agent_type": "supervisor",
  "phase": "analyze_task",
  "task_id": "task_123",
  "duration_ms": 150.5,
  "trace_id": "trace_abc",
  "span_id": "span_xyz"
}
```

### 2. 图节点执行追踪

系统会追踪 LangGraph 图的所有节点执行，包括：

- **图名称**：main_graph、dissection_subgraph、review_subgraph
- **节点名称**：supervisor_analyze_task、dissection_subgraph、review_subgraph 等
- **状态快照**：节点执行前后的状态变化
- **执行时间**：节点执行耗时
- **错误信息**：节点执行失败的详细信息

示例日志：

```json
{
  "timestamp": "2026-04-22T10:30:46.456Z",
  "level": "INFO",
  "message": "图节点执行: main_graph.dissection_subgraph",
  "graph_name": "main_graph",
  "node_name": "dissection_subgraph",
  "task_id": "task_123",
  "state_snapshot": {
    "phase": "dissection",
    "status": "analyzing",
    "progress": 0.3,
    "has_explanation": true
  },
  "duration_ms": 2500.0,
  "trace_id": "trace_abc",
  "span_id": "span_def"
}
```

### 3. 追踪上下文传播

系统支持追踪上下文的传播，包括：

- **trace_id**：全局追踪ID，标识一次完整的任务执行
- **span_id**：当前执行单元的ID
- **parent_span_id**：父执行单元的ID（用于构建调用链）

这些ID会在整个执行链路中传播，方便在 LangSmith 中查看完整的调用链。

### 4. 错误追踪

当系统发生错误时，追踪系统会记录：

- 错误发生的位置（智能体或节点）
- 错误消息和堆栈信息
- 错误发生时的状态快照
- 错误恢复策略

## 使用 LangSmith Web 界面

### 1. 访问 LangSmith

访问 [https://smith.langchain.com/](https://smith.langchain.com/) 并登录。

### 2. 查看项目

在项目列表中找到 `algoweaver-ai` 项目。

### 3. 查看追踪记录

在项目页面中，你可以看到所有的追踪记录，包括：

- **Runs**：所有的执行记录
- **Traces**：完整的调用链路
- **Feedback**：用户反馈和评分
- **Datasets**：测试数据集

### 4. 分析执行链路

点击任意一条追踪记录，可以看到：

- **调用树**：完整的调用链路树状图
- **时间线**：各个节点的执行时间线
- **输入输出**：每个节点的输入和输出数据
- **性能指标**：执行时间、Token 使用量等

### 5. 调试和优化

使用 LangSmith 可以：

- 识别性能瓶颈（哪个节点执行最慢）
- 分析错误原因（查看错误发生时的完整上下文）
- 优化提示词（查看 LLM 的输入输出）
- 对比不同版本的执行效果

## 使用 LangGraph Studio 调试

### 1. 安装 LangGraph Studio

```bash
pip install langgraph-studio
```

### 2. 启动 LangGraph Studio

```bash
cd algoweaver-backend
langgraph studio
```

### 3. 访问调试界面

打开浏览器访问 [http://localhost:8123](http://localhost:8123)

### 4. 选择图进行调试

在 LangGraph Studio 中，你可以选择以下图进行调试：

- **main_graph**：主图
- **dissection_subgraph**：算法拆解子图
- **review_subgraph**：代码评审子图

### 5. 可视化调试

LangGraph Studio 提供：

- **图可视化**：查看图的结构和节点连接
- **状态查看**：查看每个节点的状态变化
- **单步执行**：逐步执行图的每个节点
- **断点调试**：在特定节点设置断点
- **状态编辑**：手动修改状态进行测试

## 配置文件说明

### langgraph.json

```json
{
  "dependencies": ["."],
  "graphs": {
    "main_graph": "./app/graph/main_graph.py:create_main_graph",
    "dissection_subgraph": "./app/graph/subgraphs/dissection/builder.py:create_dissection_subgraph",
    "review_subgraph": "./app/graph/subgraphs/review/builder.py:create_review_subgraph"
  },
  "env": ".env.dev",
  "python_version": "3.11",
  "store": {
    "type": "memory"
  },
  "tracing": {
    "enabled": true,
    "langsmith": {
      "project": "algoweaver-ai",
      "api_key_env": "LANGSMITH_API_KEY",
      "endpoint_env": "LANGSMITH_ENDPOINT"
    }
  },
  "visualization": {
    "show_state": true,
    "show_inputs": true,
    "show_outputs": true,
    "max_depth": 10
  }
}
```

配置说明：

- **dependencies**：项目依赖路径
- **graphs**：可调试的图及其入口函数
- **env**：环境变量文件路径
- **python_version**：Python 版本
- **store**：状态存储类型（memory/redis）
- **tracing**：追踪配置
- **visualization**：可视化配置

## 编程接口

### 记录智能体执行

```python
from app.core.logger import log_agent_execution

log_agent_execution(
    agent_name="supervisor",
    agent_type="supervisor",
    phase="analyze_task",
    task_id="task_123",
    inputs={"code": "print('hello')"},
    outputs={"result": "success"},
    duration_ms=150.5,
    trace_id="trace_abc",
    span_id="span_xyz"
)
```

### 记录图节点执行

```python
from app.core.logger import log_graph_execution

log_graph_execution(
    graph_name="main_graph",
    node_name="dissection_subgraph",
    task_id="task_123",
    state_snapshot={"phase": "dissection", "progress": 0.3},
    duration_ms=2500.0,
    trace_id="trace_abc",
    span_id="span_def"
)
```

### 记录错误

```python
log_agent_execution(
    agent_name="step_simulator",
    agent_type="dissection",
    phase="simulate_steps",
    task_id="task_123",
    error="Simulation failed: invalid code",
    duration_ms=100.0,
    trace_id="trace_abc",
    span_id="span_xyz"
)
```

## 最佳实践

### 1. 使用有意义的 trace_id

使用任务ID作为 trace_id，方便关联同一任务的所有追踪记录：

```python
trace_id = state.get("task_id", str(uuid.uuid4()))
```

### 2. 记录关键状态变化

在状态快照中记录关键信息，方便后续分析：

```python
state_snapshot = {
    "phase": state["current_phase"].value,
    "status": state["status"].value,
    "progress": state.get("progress", 0.0),
    "has_explanation": bool(state.get("algorithm_explanation"))
}
```

### 3. 记录执行时间

使用 time.time() 记录执行时间，方便性能分析：

```python
start_time = time.time()
# ... 执行代码 ...
duration_ms = (time.time() - start_time) * 1000
```

### 4. 记录输入输出

记录智能体的输入输出，方便调试和优化：

```python
log_agent_execution(
    agent_name="step_simulator",
    agent_type="dissection",
    phase="simulate_steps",
    inputs={"code": code, "algorithm_type": algo_type},
    outputs={"steps": len(steps), "success": True}
)
```

### 5. 使用结构化日志

使用 extra_fields 记录额外信息：

```python
log_with_context(
    logger,
    logging.INFO,
    "任务执行完成",
    extra_fields={
        "task_id": task_id,
        "duration_ms": duration_ms,
        "success": True
    }
)
```

## 故障排查

### 1. 追踪未启用

**问题**：启动日志显示 "LangSmith 追踪未启用"

**解决**：
- 检查 `.env.dev` 文件中是否配置了 `LANGSMITH_API_KEY`
- 检查 `LANGSMITH_TRACING` 是否设置为 `true`

### 2. 追踪数据未上传

**问题**：LangSmith Web 界面看不到追踪数据

**解决**：
- 检查 API Key 是否正确
- 检查网络连接是否正常
- 检查 `LANGSMITH_ENDPOINT` 是否正确
- 查看应用日志是否有错误信息

### 3. LangGraph Studio 无法连接

**问题**：LangGraph Studio 启动失败或无法连接

**解决**：
- 检查 `langgraph.json` 配置是否正确
- 检查图的入口函数是否存在
- 检查 Python 版本是否匹配
- 查看 LangGraph Studio 的日志输出

## 相关资源

- [LangSmith 官方文档](https://docs.smith.langchain.com/)
- [LangGraph Studio 文档](https://langchain-ai.github.io/langgraph/concepts/langgraph_studio/)
- [LangChain 追踪指南](https://python.langchain.com/docs/guides/tracing/)

## 总结

通过集成 LangSmith 和 LangGraph Studio，AlgoWeaver AI 系统实现了完整的全链路追踪能力，可以：

1. **实时监控**：查看系统的实时执行状态
2. **性能分析**：识别性能瓶颈并优化
3. **错误调试**：快速定位和解决问题
4. **质量保证**：验证系统行为是否符合预期
5. **持续改进**：基于追踪数据优化系统设计

这些功能对于开发、测试和生产环境都非常有价值。
