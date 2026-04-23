# LangGraph Studio 使用指南

## 问题背景

在使用 LangGraph Studio 调试时，之前会遇到状态字段缺失的问题（KeyError），原因是：

- **Main 运行路径**：通过 FastAPI API 层，使用 `StateFactory.create_global_state()` 创建完整状态
- **Studio 运行路径**：直接使用 UI 输入作为初始状态，缺少必需字段

## 解决方案

已为所有图添加**状态标准化包装器**，自动将简化输入转换为完整状态对象。

## 支持的输入格式

### 1. 主图 (main_graph)

#### 简化格式（推荐）
```json
{
  "code": "def bubble_sort(arr):\n    n = len(arr)\n    for i in range(n):\n        for j in range(0, n-i-1):\n            if arr[j] > arr[j+1]:\n                arr[j], arr[j+1] = arr[j+1], arr[j]\n    return arr",
  "language": "python",
  "optimization_level": "balanced"
}
```

#### 完整格式
```json
{
  "task_id": "custom_task_123",
  "user_id": "user_456",
  "original_code": "def bubble_sort(arr): ...",
  "language": "python",
  "optimization_level": "balanced",
  "status": "pending",
  "current_phase": "analysis",
  "progress": 0.0,
  "collaboration_mode": "master_expert",
  "active_agents": [],
  "code_versions": ["def bubble_sort(arr): ..."],
  "decision_history": [],
  "human_intervention_required": false,
  "shared_context": {},
  "created_at": "2026-04-23T10:00:00Z",
  "updated_at": "2026-04-23T10:00:00Z",
  "retry_count": 0
}
```

### 2. 算法拆解子图 (dissection_subgraph)

#### 简化格式（推荐）
```json
{
  "code": "def binary_search(arr, target):\n    left, right = 0, len(arr) - 1\n    while left <= right:\n        mid = (left + right) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            left = mid + 1\n        else:\n            right = mid - 1\n    return -1",
  "language": "python"
}
```

#### 带输入数据
```json
{
  "code": "def binary_search(arr, target): ...",
  "language": "python",
  "input_data": {
    "arr": [1, 3, 5, 7, 9, 11, 13],
    "target": 7
  }
}
```

### 3. 代码评审子图 (review_subgraph)

#### 简化格式（推荐）
```json
{
  "code": "def inefficient_sum(arr):\n    result = 0\n    for i in range(len(arr)):\n        result = result + arr[i]\n    return result",
  "language": "python",
  "optimization_level": "thorough"
}
```

#### 自定义质量阈值
```json
{
  "code": "def inefficient_sum(arr): ...",
  "language": "python",
  "optimization_level": "balanced",
  "quality_threshold": 8.0
}
```

## 字段说明

### 通用字段

| 字段 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `code` | string | ✓ | - | 要分析的代码 |
| `language` | string | ✓ | `"python"` | 编程语言 |
| `task_id` | string | ✗ | 自动生成 | 任务唯一标识 |

### 主图特有字段

| 字段 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `optimization_level` | string | ✗ | `"balanced"` | 优化级别：`"fast"`, `"balanced"`, `"thorough"` |
| `user_id` | string | ✗ | `"studio_user"` | 用户标识 |

### 算法拆解子图特有字段

| 字段 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `input_data` | object | ✗ | `null` | 算法输入数据（用于模拟执行） |

### 代码评审子图特有字段

| 字段 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `optimization_level` | string | ✗ | `"balanced"` | 优化级别 |
| `quality_threshold` | number | ✗ | `7.0` | 质量阈值（0-10） |

## 使用示例

### 场景 1：调试主图完整流程

1. 在 LangGraph Studio 中选择 `main_graph`
2. 输入简化格式：
```json
{
  "code": "def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)",
  "language": "python",
  "optimization_level": "thorough"
}
```
3. 点击运行，系统会自动补全所有必需字段

### 场景 2：单独测试算法拆解

1. 在 LangGraph Studio 中选择 `dissection_subgraph`
2. 输入带测试数据的格式：
```json
{
  "code": "def quick_sort(arr):\n    if len(arr) <= 1:\n        return arr\n    pivot = arr[len(arr) // 2]\n    left = [x for x in arr if x < pivot]\n    middle = [x for x in arr if x == pivot]\n    right = [x for x in arr if x > pivot]\n    return quick_sort(left) + middle + quick_sort(right)",
  "language": "python",
  "input_data": {
    "arr": [3, 6, 8, 10, 1, 2, 1]
  }
}
```

### 场景 3：单独测试代码评审

1. 在 LangGraph Studio 中选择 `review_subgraph`
2. 输入需要优化的代码：
```json
{
  "code": "def find_max(numbers):\n    max_num = numbers[0]\n    for i in range(len(numbers)):\n        if numbers[i] > max_num:\n            max_num = numbers[i]\n    return max_num",
  "language": "python",
  "optimization_level": "balanced"
}
```

## 技术实现

### 包装图架构

每个 Studio 工厂函数都返回一个包装图：

```
Studio 输入 → normalize_input (标准化) → 原始图执行 → 输出
```

### 状态转换逻辑

1. **检测输入类型**：判断是简化格式、完整状态还是部分状态
2. **字段补全**：使用 `StateFactory` 创建完整状态对象
3. **字段保留**：保留原始输入中的额外字段
4. **透明传递**：对于完整状态，直接透传不做修改

### 相关文件

- `app/graph/main_graph.py`: 主图包装器
  - `_normalize_studio_input()`: 主图输入标准化
  - `_create_studio_wrapper_graph()`: 主图包装器
  - `create_main_graph_for_studio()`: Studio 工厂函数

- `app/graph/subgraphs/dissection/builder.py`: 算法拆解子图包装器
  - `_normalize_dissection_studio_input()`: 子图输入标准化
  - `_create_dissection_studio_wrapper()`: 子图包装器
  - `create_dissection_subgraph_for_studio()`: Studio 工厂函数

- `app/graph/subgraphs/review/builder.py`: 代码评审子图包装器
  - `_normalize_review_studio_input()`: 子图输入标准化
  - `_create_review_studio_wrapper()`: 子图包装器
  - `create_review_subgraph_for_studio()`: Studio 工厂函数

## 常见问题

### Q: 为什么需要状态标准化？

A: LangGraph Studio 直接使用 UI 输入作为图的初始状态，而我们的节点代码假设状态包含所有必需字段。状态标准化确保无论输入格式如何，节点都能访问到所需的字段。

### Q: 简化格式和完整格式有什么区别？

A: 
- **简化格式**：只包含核心业务字段（code, language 等），适合快速测试
- **完整格式**：包含所有状态字段，适合精确控制执行流程

### Q: 如何知道我的输入是否正确？

A: 运行 `test_studio_state_fix.py` 测试文件，验证输入格式是否被正确处理。

### Q: 修复后是否影响 Main 运行？

A: 不影响。Main 运行仍然通过 FastAPI API 层，使用原有的状态创建逻辑。包装器只在 Studio 环境中生效。

## 测试验证

运行测试脚本验证修复：

```bash
# 激活虚拟环境
source .venv/Scripts/activate  # Windows Git Bash
# 或
source .venv/bin/activate       # Linux/Mac

# 运行测试
python test_studio_state_fix.py
```

预期输出：
```
============================================================
LangGraph Studio 状态初始化修复测试
============================================================
...
✓ 所有测试通过！
============================================================
```

## 总结

通过添加状态标准化包装器，LangGraph Studio 现在可以：

1. ✅ 接受简化的 API 请求体格式输入
2. ✅ 自动补全所有必需的状态字段
3. ✅ 避免节点访问缺失字段时的 KeyError
4. ✅ 保持与 Main 运行路径的行为一致性
5. ✅ 支持灵活的输入格式（简化/完整/部分）

现在可以在 LangGraph Studio 中愉快地调试了！🎉
