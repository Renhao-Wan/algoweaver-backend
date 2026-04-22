# LangGraph Studio 配置说明

## 工厂函数要求

LangGraph Studio 要求图的工厂函数**只能接受以下参数**：
- `checkpointer` (可选)
- `ServerRuntime` (可选)
- `RunnableConfig` (可选)

**不能有其他参数**，否则会报错：
```
ValueError: Graph factory <function> can only accept arguments of type ServerRuntime and/or RunnableConfig, got [...]
```

## Checkpointer 参数处理

### 重要：LangGraph Studio 传入的是 dict

LangGraph Studio 调用工厂函数时，传入的 `checkpointer` 参数是一个 **dict 配置对象**，而不是 `BaseCheckpointSaver` 实例。

例如：
```python
checkpointer = {'type': 'memory'}  # LangGraph Studio 传入的
```

如果直接将这个 dict 传给 `graph.compile(checkpointer=...)`，会报错：
```
Invalid checkpointer provided
```

### 解决方案

在工厂函数中检查 `checkpointer` 的类型，如果是 dict 则忽略它：

```python
def create_main_graph_for_studio(checkpointer=None):
    # LangGraph Studio 传入的是 dict 配置，我们需要忽略它
    if checkpointer is None or isinstance(checkpointer, dict):
        checkpointer = None  # 使用我们自己的 create_checkpointer()
    
    builder = MainGraphBuilder(checkpointer=checkpointer)
    return builder.compile()
```

这样做的原因：
1. LangGraph Studio 的 dict 配置格式可能与我们的不兼容
2. 我们有自己的 checkpointer 创建逻辑（`create_checkpointer()`）
3. 确保 LangGraph Studio 和应用使用相同的配置

## 当前配置

### 主图工厂函数
```python
def create_main_graph_for_studio(checkpointer=None):
    """创建主图（用于 LangGraph Studio）"""
    builder = MainGraphBuilder(checkpointer=checkpointer)
    return builder.compile()
```

### 算法拆解子图工厂函数
```python
def create_dissection_subgraph_for_studio(checkpointer=None):
    """创建算法拆解子图（用于 LangGraph Studio）"""
    manager = DissectionSubgraphManager()
    return manager.initialize_subgraph(checkpointer)
```

### 代码评审子图工厂函数
```python
def create_review_subgraph_for_studio(checkpointer=None):
    """创建代码评审子图（用于 LangGraph Studio）"""
    manager = ReviewSubgraphManager(max_review_rounds=3)  # 使用默认值
    return manager.initialize_subgraph(checkpointer)
```

## 配置文件

`langgraph.json`:
```json
{
  "dependencies": ["."],
  "graphs": {
    "main_graph": "./app/graph/main_graph.py:create_main_graph_for_studio",
    "dissection_subgraph": "./app/graph/subgraphs/dissection/builder.py:create_dissection_subgraph_for_studio",
    "review_subgraph": "./app/graph/subgraphs/review/builder.py:create_review_subgraph_for_studio"
  },
  "env": ".env.dev",
  "python_version": "3.11"
}
```

## 配置限制说明

### 为什么不能有额外参数？

LangGraph Studio 需要能够自动调用工厂函数创建图实例。如果工厂函数有额外的必需参数（如 `max_review_rounds`），LangGraph Studio 无法知道应该传入什么值。

### 如何处理配置参数？

如果子图需要配置参数（如 `max_review_rounds`），有两种方案：

**方案1：使用默认值（当前采用）**
```python
def create_review_subgraph_for_studio(checkpointer=None):
    manager = ReviewSubgraphManager(max_review_rounds=3)  # 硬编码默认值
    return manager.initialize_subgraph(checkpointer)
```

优点：简单直接
缺点：无法在 LangGraph Studio 中调整参数

**方案2：从环境变量读取**
```python
def create_review_subgraph_for_studio(checkpointer=None):
    from app.core.config import get_settings
    settings = get_settings()
    max_rounds = getattr(settings, 'max_review_rounds', 3)
    manager = ReviewSubgraphManager(max_review_rounds=max_rounds)
    return manager.initialize_subgraph(checkpointer)
```

优点：可以通过 `.env.dev` 配置
缺点：需要在配置文件中添加新字段

### 应用运行时 vs LangGraph Studio

**应用运行时**：
- 使用 `ReviewSubgraphBuilder` 类
- 可以传入任意参数
- 通过 `MainGraphManager` 管理

**LangGraph Studio**：
- 使用 `create_review_subgraph_for_studio` 工厂函数
- 只能接受 `checkpointer` 参数
- 配置参数使用默认值或从环境变量读取

## 启动 LangGraph Studio

```bash
cd algoweaver-backend
langgraph dev
```

访问：http://localhost:2024

或在 LangSmith Studio 中访问：
https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024

## 常见问题

### Q: 为什么 review_subgraph 的 max_review_rounds 固定为 3？

A: 因为 LangGraph Studio 的工厂函数不能有额外参数。如果需要调整，可以：
1. 修改 `create_review_subgraph_for_studio` 中的默认值
2. 或者在 `.env.dev` 中添加 `MAX_REVIEW_ROUNDS` 配置，然后从环境变量读取

### Q: 应用运行时是否也受此限制？

A: 不受限制。应用运行时使用 `ReviewSubgraphBuilder` 类，可以传入任意参数：
```python
builder = ReviewSubgraphBuilder()
builder.max_review_rounds = 5  # 可以自定义
```

### Q: 如何确保 LangGraph Studio 和应用使用相同的配置？

A: 通过统一的配置管理：
1. Checkpointer：通过 `app/core/checkpointer.py` 统一管理
2. LLM：通过 `app/core/llm.py` 统一管理
3. 环境变量：都从 `.env.dev` 读取

## 总结

LangGraph Studio 的工厂函数必须遵守严格的签名要求，只能接受 `checkpointer` 等特定参数。配置参数需要通过默认值或环境变量处理，不能作为函数参数传入。
