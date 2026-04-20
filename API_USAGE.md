# AlgoWeaver AI API 使用指南

## 概述

AlgoWeaver AI 提供了 RESTful API 和 WebSocket 接口，用于代码分析、算法讲解和优化建议生成。

## 基础信息

- **基础URL**: `http://localhost:8000`
- **API文档**: `http://localhost:8000/docs` (Swagger UI)
- **ReDoc文档**: `http://localhost:8000/redoc`

## 核心 API 接口

### 1. 创建代码分析任务

**端点**: `POST /api/weave-algorithm`

**请求体**:
```json
{
  "code": "def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)",
  "language": "python",
  "optimization_level": "balanced",
  "include_explanation": true,
  "include_performance_test": false,
  "custom_requirements": "请重点关注时间复杂度优化"
}
```

**响应**:
```json
{
  "success": true,
  "message": "任务创建成功",
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "created",
  "estimated_duration_seconds": 60,
  "websocket_url": "ws://localhost:8000/ws/chat/550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-04-20T10:30:00Z"
}
```

### 2. 查询任务状态

**端点**: `GET /api/task/{task_id}/status`

**查询参数**:
- `include_details`: 是否包含详细信息 (默认: true)
- `include_logs`: 是否包含执行日志 (默认: false)

**响应**:
```json
{
  "success": true,
  "message": "查询成功",
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "analyzing",
  "progress_percent": 45,
  "current_phase": "dissection",
  "created_at": "2026-04-20T10:30:00Z",
  "updated_at": "2026-04-20T10:30:30Z",
  "result": null,
  "logs": []
}
```

### 3. 获取分析结果

**端点**: `GET /api/task/{task_id}/result`

**响应**:
```json
{
  "success": true,
  "message": "分析完成",
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "original_code": "def fibonacci(n): ...",
  "optimized_code": "def fibonacci(n, memo=None): ...",
  "explanation": {
    "algorithm_name": "斐波那契数列",
    "steps": [...],
    "pseudocode": "...",
    "time_complexity": "O(2^n)",
    "space_complexity": "O(n)",
    "visualization": "...",
    "key_insights": [...]
  },
  "issues": [...],
  "suggestions": [...],
  "validation_result": {...},
  "performance_metrics": {...},
  "optimization_history": []
}
```

### 4. 恢复暂停的任务

**端点**: `POST /api/task/{task_id}/resume`

**请求体**:
```json
{
  "intervention_id": "intervention_001",
  "decision_type": "optimization_suggestions",
  "accepted_suggestions": ["suggestion_001", "suggestion_002"],
  "rejected_suggestions": ["suggestion_003"],
  "custom_input": "请使用动态规划方法优化",
  "timeout_seconds": 300
}
```

### 5. 取消任务

**端点**: `DELETE /api/task/{task_id}`

**响应**:
```json
{
  "success": true,
  "message": "任务已取消",
  "task_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### 6. 健康检查

**端点**: `GET /api/health`

**响应**:
```json
{
  "status": "healthy",
  "service": "AlgoWeaver AI",
  "version": "1.0.0"
}
```

## WebSocket 接口

### 连接

**端点**: `ws://localhost:8000/ws/chat/{task_id}`

### 消息类型

#### 1. 启动任务

**客户端发送**:
```json
{
  "type": "start_task",
  "data": {
    "code": "def fibonacci(n): ...",
    "language": "python",
    "optimization_level": "balanced",
    "custom_requirements": "..."
  }
}
```

#### 2. 状态更新

**服务端推送**:
```json
{
  "type": "status_update",
  "data": {
    "node": "dissection_subgraph",
    "status": "analyzing",
    "phase": "dissection",
    "progress": 0.3,
    "message": "分析算法执行步骤..."
  }
}
```

#### 3. 人工干预请求

**服务端推送**:
```json
{
  "type": "human_intervention_required",
  "data": {
    "intervention_id": "intervention_001",
    "prompt": "请确认是否接受以下优化建议",
    "options": [
      {
        "id": "accept",
        "label": "接受",
        "description": "接受所有优化建议"
      },
      {
        "id": "reject",
        "label": "拒绝",
        "description": "拒绝优化建议"
      }
    ],
    "timeout_seconds": 300,
    "default_action": "accept"
  }
}
```

#### 4. 人工决策

**客户端发送**:
```json
{
  "type": "human_decision",
  "data": {
    "action": "continue",
    "accepted_suggestions": ["suggestion_001"],
    "rejected_suggestions": ["suggestion_002"],
    "custom_input": "请使用动态规划"
  }
}
```

#### 5. 任务完成

**服务端推送**:
```json
{
  "type": "task_completed",
  "data": {
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "completed"
  }
}
```

#### 6. 错误消息

**服务端推送**:
```json
{
  "type": "error",
  "data": {
    "error_message": "执行失败: ..."
  }
}
```

#### 7. 心跳检测

**客户端发送**:
```json
{
  "type": "ping"
}
```

**服务端响应**:
```json
{
  "type": "pong",
  "data": {
    "timestamp": "2026-04-20T10:30:00Z"
  }
}
```

## 使用示例

### Python 示例

```python
import requests
import websocket
import json

# 1. 创建任务
response = requests.post(
    "http://localhost:8000/api/weave-algorithm",
    json={
        "code": "def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)",
        "language": "python",
        "optimization_level": "balanced"
    }
)
task_data = response.json()
task_id = task_data["task_id"]
ws_url = task_data["websocket_url"]

# 2. 连接 WebSocket
ws = websocket.create_connection(ws_url)

# 3. 启动任务
ws.send(json.dumps({
    "type": "start_task",
    "data": {
        "code": "def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)",
        "language": "python",
        "optimization_level": "balanced"
    }
}))

# 4. 接收消息
while True:
    message = json.loads(ws.recv())
    print(f"收到消息: {message['type']}")
    
    if message["type"] == "human_intervention_required":
        # 处理人工干预
        ws.send(json.dumps({
            "type": "human_decision",
            "data": {
                "action": "continue",
                "accepted_suggestions": [],
                "rejected_suggestions": []
            }
        }))
    
    if message["type"] == "task_completed":
        break

ws.close()

# 5. 获取结果
result = requests.get(f"http://localhost:8000/api/task/{task_id}/result")
print(result.json())
```

### JavaScript 示例

```javascript
// 1. 创建任务
const response = await fetch('http://localhost:8000/api/weave-algorithm', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    code: 'def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)',
    language: 'python',
    optimization_level: 'balanced'
  })
});

const taskData = await response.json();
const taskId = taskData.task_id;
const wsUrl = taskData.websocket_url;

// 2. 连接 WebSocket
const ws = new WebSocket(wsUrl);

ws.onopen = () => {
  // 3. 启动任务
  ws.send(JSON.stringify({
    type: 'start_task',
    data: {
      code: 'def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)',
      language: 'python',
      optimization_level: 'balanced'
    }
  }));
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('收到消息:', message.type);
  
  if (message.type === 'human_intervention_required') {
    // 处理人工干预
    ws.send(JSON.stringify({
      type: 'human_decision',
      data: {
        action: 'continue',
        accepted_suggestions: [],
        rejected_suggestions: []
      }
    }));
  }
  
  if (message.type === 'task_completed') {
    ws.close();
    // 5. 获取结果
    fetch(`http://localhost:8000/api/task/${taskId}/result`)
      .then(res => res.json())
      .then(result => console.log(result));
  }
};
```

## 错误处理

### HTTP 状态码

- `200 OK`: 请求成功
- `400 Bad Request`: 请求参数错误
- `404 Not Found`: 任务不存在
- `500 Internal Server Error`: 服务器内部错误

### 错误响应格式

```json
{
  "detail": "错误描述信息"
}
```

## 注意事项

1. **任务ID**: 每个任务都有唯一的UUID，用于追踪和查询
2. **WebSocket连接**: 建议使用WebSocket进行实时通信，获取流式更新
3. **Human-in-the-loop**: 某些关键决策需要人工确认，系统会暂停等待
4. **超时设置**: 任务执行有超时限制，默认300秒
5. **并发限制**: 系统有并发任务数限制，请合理安排任务提交

## 支持的编程语言

- Python
- Java
- JavaScript
- C++

## 优化级别

- `basic`: 基础优化（30秒）
- `balanced`: 平衡优化（60秒）
- `aggressive`: 激进优化（120秒）
- `production`: 生产级优化（180秒）
