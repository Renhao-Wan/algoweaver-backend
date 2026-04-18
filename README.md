# AlgoWeaver AI 智能代码推演系统

基于 LangGraph + FastAPI 的多智能体系统，专注于智能算法教学与代码质量精炼。

## 项目概述

AlgoWeaver AI 通过多智能体协作，实现从"原始代码输入"到"教学级讲解 + 生产级优化代码"的全自动、可控转化。系统采用主图与子图嵌套架构，融合主控-专家模式和协商/对抗模式，通过强制 Human-in-the-loop 机制确保用户掌握最终决策权。

### 核心功能

- **智能算法拆解**: 一步一步分析算法执行过程，生成可视化伪代码讲解
- **自动质量优化**: 发现代码中的逻辑错误、边界条件、性能瓶颈和安全隐患
- **多轮迭代精炼**: 支持多轮优化直到达到教学级清晰度和生产级高质量
- **人机协作决策**: 强制 Human-in-the-loop 确保用户掌握最终决策权
- **全链路可观测**: LangSmith 全链路追踪，完整记录分析和优化过程

### 技术栈

- **后端框架**: Python 3.11+ + FastAPI
- **多智能体**: LangGraph + LangChain + LangSmith
- **缓存**: Redis
- **执行环境**: Python REPL 沙箱 + Docker
- **容器化**: Docker + Docker Compose
- **监控**: LangSmith 全链路追踪 + 结构化日志
- **测试**: pytest + Hypothesis (属性测试) + 集成测试
- **API 文档**: FastAPI 自动生成 OpenAPI 规范
- **调试工具**: LangGraph Studio 可视化调试界面

## 快速开始

### 环境要求

- Python 3.11+
- Docker & Docker Compose
- Redis (可选，用于缓存)

### 安装步骤

1. **克隆项目**
   ```bash
   git clone <repository-url>
   cd algoweaver-backend
   ```

2. **创建虚拟环境**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # 或
   .venv\Scripts\activate     # Windows
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

4. **配置环境变量**
   ```bash
   cp .env.example .env
   # 编辑 .env 文件，填入必要的配置信息
   ```

5. **启动服务**
   ```bash
   python -m app.main
   ```

### 使用 LangGraph Studio 调试

1. **安装 LangGraph Studio**
   ```bash
   pip install langgraph-studio
   ```

2. **启动调试界面**
   ```bash
   langgraph studio
   ```

3. **访问调试界面**
   打开浏览器访问 `http://localhost:8123`

## 项目结构

```
algoweaver-backend/
├── app/
│   ├── main.py                     # FastAPI 应用入口
│   ├── core/                       # 基础设施层
│   │   ├── config.py               # 全局配置管理
│   │   ├── logger.py               # 日志系统
│   │   └── security.py             # 安全认证 (可选)
│   ├── api/                        # API 路由层
│   │   ├── deps.py                 # 依赖注入
│   │   └── routes/                 # 路由定义
│   ├── schemas/                    # 数据模型层 (Pydantic)
│   ├── services/                   # 业务逻辑层
│   ├── graph/                      # LangGraph 多智能体编排层
│   │   ├── state.py                # 状态机定义
│   │   ├── tools/                  # LangChain 工具链
│   │   ├── subgraphs/              # 子图模块
│   │   ├── supervisor/             # 主控调度
│   │   └── main_graph.py           # 主图构建
│   └── utils/                      # 通用工具
├── .env                            # 环境变量配置
├── requirements.txt                # Python 依赖
├── langgraph.json                  # LangGraph Studio 配置
├── Dockerfile                      # Docker 配置
├── docker-compose.yml              # Docker Compose 配置
└── README.md                       # 项目说明
```

## API 文档

启动服务后，访问以下地址查看 API 文档：

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 开发指南

### 代码规范

- 使用 Black 进行代码格式化
- 使用 isort 进行导入排序
- 使用 flake8 进行代码检查
- 使用 mypy 进行类型检查

### 测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_sandbox.py

# 运行属性测试
pytest tests/property_tests/
```

### 调试

使用 LangGraph Studio 进行可视化调试：

1. 确保 `langgraph.json` 配置正确
2. 启动 LangGraph Studio
3. 在界面中选择要调试的图
4. 设置断点和输入数据
5. 逐步执行和观察状态变化

## 部署

### Docker 部署

```bash
# 构建镜像
docker build -t algoweaver-backend .

# 运行容器
docker run -p 8000:8000 --env-file .env algoweaver-backend
```

### Docker Compose 部署

```bash
# 启动所有服务 (包括 Redis)
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

## 监控与日志

- **应用日志**: 结构化 JSON 日志输出到 stdout
- **LangSmith 追踪**: 完整的智能体执行链路追踪
- **健康检查**: `GET /health` 端点
- **指标监控**: Prometheus 格式指标 (端口 9090)

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 联系方式

- 项目主页: [GitHub Repository]
- 问题反馈: [GitHub Issues]
- 邮箱: [team@algoweaver.ai]