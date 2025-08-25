## 快速开始

### 1. 环境准备

确保已安装以下工具：
- Python 3.12+
- uv (Python环境管理)
- Poetry (包依赖管理)
- Docker & Docker Compose

### 2. 安装依赖

```bash
# 使用uv创建Python环境
uv venv -p 3.12.8

# 激活虚拟环境
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate     # Windows

# 使用Poetry安装依赖
poetry install
```

### 3. 启动数据库服务

```bash
# 启动Weaviate和Neo4j服务
docker compose up -d

# 查看服务状态
docker compose ps
```

服务启动后可访问：
- Weaviate: http://localhost:8855
- Neo4j Browser: http://localhost:7473 (用户名: neo4j, 密码: password)

### 4. 运行API服务

```bash
# 启动FastAPI服务
# python -m uvicorn ai_knowledge_base.interface.api:app --reload --host 0.0.0.0 --port 8000
python -m uvicorn agent_runtime.main:app --reload --host 0.0.0.0 --port 8011
```

Agent runtime API文档访问地址：
- Fastapi docs: http://localhost:8011/docs


### 日志查看

```bash
# 查看API服务日志
docker compose logs -f api

# 查看Weaviate日志
docker compose logs -f weaviate

# 查看Neo4j日志
docker compose logs -f neo4j
```

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。
