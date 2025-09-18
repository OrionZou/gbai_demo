# Agent v1.5 部署文档

## 📋 概述

Agent v1.5 是一个基于 Docker Compose 的微服务架构系统，提供智能代理运行时、Streamlit 前端界面和 Weaviate 向量数据库服务。

## 🏗️ 系统架构

### 架构图
```
┌─────────────────────────────────────────────────────────────┐
│                    Agent v1.5 System                       │
├─────────────────────────────────────────────────────────────┤
│  Frontend (Streamlit)     │  Backend (Agent Runtime)       │
│  Port: 8501              │  Port: 8011                     │
│  ┌─────────────────────┐  │  ┌─────────────────────────────┐ │
│  │   Web Interface     │  │  │    FastAPI Server           │ │
│  │   User Interaction  │  │  │    Agent Processing         │ │
│  │   Chat UI           │  │  │    API Endpoints            │ │
│  └─────────────────────┘  │  └─────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                Vector Database (Weaviate)                   │
│                Port: 8080, 50051                           │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │   Knowledge Storage    │   Vector Search                │ │
│  │   Text Embeddings      │   OpenAI Integration           │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 服务组件

#### 1. Agent Runtime Service
- **镜像**: `intelli-train/agent:1.2.0`
- **端口**: `8011`
- **功能**:
  - FastAPI 后端服务
  - 智能代理处理逻辑
  - RESTful API 接口
  - 健康检查端点
- **依赖**: Python 3.12, Poetry, uvicorn

#### 2. Streamlit Frontend
- **镜像**: `intelli-train/agent-streamlit:1.2.0`
- **端口**: `8501`
- **功能**:
  - 用户界面
  - 聊天交互
  - 可视化展示
- **依赖**: Agent Runtime Service

#### 3. Weaviate Vector Database
- **镜像**: `semitechnologies/weaviate:1.32.2`
- **端口**: `8080` (HTTP), `50051` (gRPC)
- **功能**:
  - 向量存储
  - 语义搜索
  - OpenAI 嵌入集成
- **配置**:
  - 启用 `text2vec-openai` 模块
  - 使用 `text-embedding-3-large` 模型
  - 3072 维向量维度

### 网络配置
- **网络名称**: `agent-network`
- **驱动**: `bridge`
- **服务通信**: 内部容器网络通信

## 🚀 部署指南

### 前置要求

#### 系统要求
- Docker Engine 20.10+
- Docker Compose 2.0+
- 最少 4GB RAM
- 最少 10GB 磁盘空间

#### API 密钥要求
- OpenAI API Key (用于 LLM 和 Embedding)
- 阿里云 DashScope API Key (可选)

### 环境配置

#### 1. 复制环境文件
```bash
cp .env_example .env
```

#### 2. 配置环境变量
编辑 `.env` 文件，配置以下关键参数：

```bash
# LLM 配置
LLM_API_KEY=your_openai_api_key
LLM_MODEL=qwen3-32b
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# Embedding 配置
EMBEDDING_API_KEY=your_openai_api_key
EMBEDDING_MODEL=text-embedding-v4
EMBEDDINGI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# Weaviate 配置
WEAVIATE_URL=http://weaviate:8080  # 容器内部访问
WEAVIATE_API_KEY=abc-abc
```

#### 3. 验证配置文件
确保 `agent-v1.5-compose.yaml` 文件格式正确：
```bash
docker-compose -f agent-v1.5-compose.yaml config
```

### 部署步骤

#### 1. 构建和启动服务
```bash
# 构建并启动所有服务
docker-compose -f agent-v1.5-compose.yaml up -d --build

# 查看服务状态
docker-compose -f agent-v1.5-compose.yaml ps

# 查看服务日志
docker-compose -f agent-v1.5-compose.yaml logs -f
```

#### 2. 验证部署
检查各服务健康状态：

```bash
# 检查 Weaviate 服务
curl http://localhost:8080/v1/meta

# 检查 Agent Runtime 服务
curl http://localhost:8011/agent/health

# 检查 Streamlit 前端
# 浏览器访问: http://localhost:8501
```

#### 3. 服务访问地址
- **Streamlit Frontend**: http://localhost:8501
- **Agent Runtime API**: http://localhost:8011
- **Weaviate Database**: http://localhost:8080
- **API 文档**: http://localhost:8011/docs

## 🔧 开发指南

### 开发环境搭建

#### 1. 本地开发环境
```bash
# 激活 Python 虚拟环境
source .venv/bin/activate

# 安装依赖
poetry install

# 设置环境变量
export PYTHONPATH=/path/to/gbai_demo/src
```

#### 2. 容器化开发
```bash
# 仅启动依赖服务 (Weaviate)
docker-compose -f agent-v1.5-compose.yaml up -d weaviate

# 本地运行 Agent Runtime
python -m uvicorn agent_runtime.main:app --reload --port 8011

# 本地运行 Streamlit (在另一个终端)
cd playground && streamlit run app.py --server.port 8501
```

### 代码修改和测试

#### 1. Agent Runtime 开发
```bash
# 修改代码后重新构建容器
docker-compose -f agent-v1.5-compose.yaml build agent
docker-compose -f agent-v1.5-compose.yaml up -d agent

# 查看日志
docker-compose -f agent-v1.5-compose.yaml logs -f agent
```

#### 2. Streamlit 前端开发
```bash
# 重新构建前端服务
docker-compose -f agent-v1.5-compose.yaml build streamlit
docker-compose -f agent-v1.5-compose.yaml up -d streamlit
```

#### 3. 配置文件修改
```bash
# 修改环境变量后重启服务
docker-compose -f agent-v1.5-compose.yaml down
docker-compose -f agent-v1.5-compose.yaml up -d
```

### 开发工作流

#### 1. 功能开发流程
1. 在本地环境进行代码开发
2. 编写和运行单元测试
3. 使用 demo 脚本验证功能
4. 构建容器镜像测试
5. 集成测试和部署验证

#### 2. 代码质量检查
```bash
# 格式化代码
black src/ playground/ tests/
isort src/ playground/ tests/

# 类型检查
mypy src/

# 运行测试
pytest tests/
```

## 🧪 测试指南

### 单元测试

#### 1. 运行单元测试
```bash
# 运行所有测试
pytest tests/

# 运行特定测试模块
pytest tests/test_agent_runtime.py

# 运行带覆盖率的测试
pytest tests/ --cov=src --cov-report=html
```

#### 2. 测试环境配置
```bash
# 设置测试环境变量
export TESTING=true
export WEAVIATE_URL=http://localhost:8080

# 使用测试配置文件
cp .env_example .env.test
```

### 集成测试

#### 1. 服务集成测试
```bash
# 启动完整服务栈
docker-compose -f agent-v1.5-compose.yaml up -d

# 等待服务就绪
sleep 30

# 运行集成测试
python -m pytest tests/integration/

# 运行 API 端点测试
curl -X POST http://localhost:8011/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, agent!"}'
```

#### 2. 端到端测试
```bash
# 使用 demo 脚本测试完整流程
python exps/test_chat_service_refactor_v2.py

# 测试 Streamlit 界面
# 手动访问 http://localhost:8501 进行交互测试
```

### 性能测试

#### 1. 负载测试
```bash
# 使用 Apache Bench 进行负载测试
ab -n 100 -c 10 http://localhost:8011/agent/health

# 使用 curl 进行并发测试
for i in {1..10}; do
  curl -X POST http://localhost:8011/api/chat \
    -H "Content-Type: application/json" \
    -d '{"message": "Test message '$i'"}' &
done
wait
```

#### 2. 内存和 CPU 监控
```bash
# 监控容器资源使用
docker stats

# 查看特定容器资源使用
docker stats agent weaviate agent-streamlit
```

## 🔍 故障排除

### 常见问题

#### 1. 容器启动失败
```bash
# 检查 Docker Compose 配置
docker-compose -f agent-v1.5-compose.yaml config

# 查看详细错误日志
docker-compose -f agent-v1.5-compose.yaml logs agent

# 检查端口占用
netstat -tulpn | grep -E ":(8011|8501|8080)"
```

#### 2. 服务无法连接
```bash
# 检查容器网络
docker network ls
docker network inspect gbai_demo_agent-network

# 检查服务健康状态
docker-compose -f agent-v1.5-compose.yaml ps
```

#### 3. API 调用失败
```bash
# 验证环境变量配置
docker-compose -f agent-v1.5-compose.yaml exec agent env | grep -E "(LLM|EMBEDDING|WEAVIATE)"

# 测试内部服务连接
docker-compose -f agent-v1.5-compose.yaml exec agent curl http://weaviate:8080/v1/meta
```

### 日志调试

#### 1. 查看服务日志
```bash
# 查看所有服务日志
docker-compose -f agent-v1.5-compose.yaml logs

# 查看特定服务日志
docker-compose -f agent-v1.5-compose.yaml logs -f agent

# 查看最近的日志
docker-compose -f agent-v1.5-compose.yaml logs --tail=100 agent
```

#### 2. 调整日志级别
编辑 Weaviate 环境变量：
```yaml
environment:
  - LOG_LEVEL=debug  # 或 info, warn, error
```

## 🔄 维护指南

### 服务管理

#### 1. 启动和停止服务
```bash
# 启动服务
docker-compose -f agent-v1.5-compose.yaml up -d

# 停止服务
docker-compose -f agent-v1.5-compose.yaml down

# 重启特定服务
docker-compose -f agent-v1.5-compose.yaml restart agent
```

#### 2. 数据备份
```bash
# 备份 Weaviate 数据
docker-compose -f agent-v1.5-compose.yaml exec weaviate \
  tar -czf /tmp/weaviate_backup.tar.gz /data

# 导出备份文件
docker cp weaviate:/tmp/weaviate_backup.tar.gz ./backup/
```

#### 3. 更新和升级
```bash
# 拉取最新镜像
docker-compose -f agent-v1.5-compose.yaml pull

# 重新构建和部署
docker-compose -f agent-v1.5-compose.yaml up -d --build

# 清理旧镜像
docker image prune -f
```

### 监控和告警

#### 1. 健康检查
```bash
# 检查服务健康状态
docker-compose -f agent-v1.5-compose.yaml ps

# 自定义健康检查脚本
#!/bin/bash
services=("agent" "weaviate" "streamlit")
for service in "${services[@]}"; do
  if ! curl -f http://localhost:8011/agent/health; then
    echo "Service $service is unhealthy"
    exit 1
  fi
done
```

#### 2. 性能监控
```bash
# 监控资源使用
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# 设置监控告警
# 可集成 Prometheus + Grafana 或其他监控系统
```

## 📚 参考资料

### API 文档
- Agent Runtime API: http://localhost:8011/docs
- Weaviate API: https://weaviate.io/developers/weaviate/api/rest
- OpenAI API: https://platform.openai.com/docs/api-reference

### 相关链接
- [Docker Compose 文档](https://docs.docker.com/compose/)
- [Weaviate 官方文档](https://weaviate.io/developers/weaviate)
- [Streamlit 文档](https://docs.streamlit.io/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)

### 版本信息
- Agent Runtime: v1.2.0
- Streamlit Frontend: v1.2.0
- Weaviate: v1.32.2
- Python: 3.12
- Docker Compose: v3.8

---

## 📝 更新日志

### v1.2.0 (当前版本)
- 修复 Docker Compose 网络配置问题
- 优化容器健康检查
- 更新 Weaviate 到 1.32.2 版本
- 改进环境变量配置

### v1.1.0
- 添加 Streamlit 前端服务
- 集成 Weaviate 向量数据库
- 实现微服务架构

### v1.0.0
- 初始版本发布
- 基础 Agent Runtime 服务
- Docker 容器化支持