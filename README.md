# AI知识库项目

基于DDD四层架构的AI知识库系统，支持对话数据的导入、存储和查询。

## 项目概述

本项目实现了以下4个核心功能：

1. **Weaviate Vector DB Client** - 向量数据库客户端，支持创建collection、导入数据、查询等功能
2. **Neo4j Graph DB Client** - 图数据库客户端，支持创建collection、导入数据、查询等功能  
3. **数据导入实体类** - 使用Pydantic实现，支持链式数据结构和历史追溯
4. **Docker部署环境** - Weaviate和Neo4j一键部署，数据目录挂载

## 技术栈

- **语言**: Python 3.12
- **环境管理**: uv
- **包管理**: Poetry
- **数据验证**: Pydantic
- **向量数据库**: Weaviate
- **图数据库**: Neo4j
- **API框架**: FastAPI
- **容器化**: Docker & Docker Compose
- **测试框架**: pytest

## 项目结构

```
ai_knowledge_base/
├── src/
│   └── ai_knowledge_base/
│       ├── domain/
│       │   └── entities.py          # Pydantic实体类
│       ├── infrastructure/
│       │   ├── weaviate_client.py   # Weaviate客户端
│       │   └── neo4j_client.py      # Neo4j客户端
│       ├── application/
│       │   └── services.py          # 应用服务
│       └── interface/
│           └── api.py               # API接口
├── tests/                           # 单元测试
├── docs/                           # 文档
├── docker-compose.yml              # Docker部署配置
├── pyproject.toml                  # Poetry配置
└── README.md
```

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
- Neo4j Browser: http://localhost:7474 (用户名: neo4j, 密码: password)

### 4. 运行API服务

```bash
# 启动FastAPI服务
python -m uvicorn ai_knowledge_base.interface.api:app --reload --host 0.0.0.0 --port 8000
# python -m uvicorn agent_runtime/main.py
python -m uvicorn agent_runtime.main:app --reload --host 0.0.0.0 --port 8011

bash



```

API文档访问地址：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 使用示例

### 1. 导入CSV数据

```python
import requests

# 准备CSV数据
csv_content = """No.,User input,s,s',prompt,Agent output
1,你好,/,1.用户发起闲聊,测试提示词,您好！请问有什么关于爱车的问题需要咨询吗？
2,没啥问题,1.用户发起闲聊,1.1引导用户询问业务问题,测试提示词2,那您最近车辆使用上有没有什么让您感到不太满意的地方？"""

# 调用导入API
response = requests.post(
    "http://localhost:8000/import/csv",
    json={"csv_content": csv_content}
)

result = response.json()
print(f"导入结果: {result}")
```

### 2. 查询相似对话

```python
import requests

# 查询相似对话
response = requests.post(
    "http://localhost:8000/query/similar",
    json={
        "query_text": "你好",
        "limit": 5
    }
)

results = response.json()
print(f"查询结果: {results}")
```

### 3. 获取对话历史

```python
import requests

# 获取对话历史
response = requests.post(
    "http://localhost:8000/query/history",
    json={"record_id": "your-record-id"}
)

history = response.json()
print(f"对话历史: {history}")
```

## API接口

### 数据导入

- `POST /import/csv` - 导入CSV格式数据
- `POST /import/csv/file` - 上传CSV文件导入

### 数据查询

- `POST /query/similar` - 查询相似对话
- `POST /query/history` - 获取对话历史
- `GET /records/{record_id}` - 获取单条记录

### 系统状态

- `GET /` - 根路径
- `GET /health` - 健康检查
- `GET /stats/database` - 数据库统计信息

## 数据格式

### CSV导入格式

CSV文件应包含以下列：

| 列名 | 描述 | 示例 |
|------|------|------|
| No. | 序号 | 1 |
| User input | 用户输入 | 你好 |
| s | 当前状态 | / |
| s' | 下一状态 | 1.用户发起闲聊 |
| prompt | 提示词 | 测试提示词 |
| Agent output | 代理输出 | 您好！请问有什么问题？ |

### 实体类结构

```python
class ConversationRecord(BaseModel):
    record_id: UUID
    sequence_number: int
    user_input: str
    current_state: str
    next_state: Optional[str]
    prompt: str
    agent_output: str
    previous_record_id: Optional[UUID]
    next_record_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime
```

## 开发指南

### 运行测试

```bash
# 运行所有测试
pytest

# 运行测试并生成覆盖率报告
pytest --cov=src/ai_knowledge_base --cov-report=html

# 查看覆盖率报告
open htmlcov/index.html
```

### 代码质量检查

```bash
# 类型检查
mypy src/

# 代码格式化
black src/ tests/

# 导入排序
isort src/ tests/
```

### 添加新功能

1. 在相应的DDD层添加代码
2. 编写单元测试
3. 更新API接口（如需要）
4. 更新文档

## 架构设计

本项目采用DDD（领域驱动设计）四层架构：

```
┌─────────────────────────────────────────┐
│              Interface Layer            │  
│  (API接口、控制器、DTO转换)                │
├─────────────────────────────────────────┤
│            Application Layer            │
│  (应用服务、用例编排、事务管理)              │
├─────────────────────────────────────────┤
│              Domain Layer               │
│  (实体、值对象、领域服务、仓储接口)          │
├─────────────────────────────────────────┤
│           Infrastructure Layer          │
│  (数据库客户端、外部服务、仓储实现)          │
└─────────────────────────────────────────┘
```

详细架构设计请参考：[docs/architecture_design.md](docs/architecture_design.md)

## 故障排除

### 常见问题

1. **数据库连接失败**
   ```bash
   # 检查Docker服务状态
   docker-compose ps
   
   # 重启服务
   docker-compose restart
   ```

2. **依赖安装失败**
   ```bash
   # 清理缓存
   poetry cache clear --all pypi
   
   # 重新安装
   poetry install
   ```

3. **测试失败**
   ```bash
   # 检查Python版本
   python --version
   
   # 确保在虚拟环境中
   which python
   ```

### 日志查看

```bash
# 查看API服务日志
docker-compose logs -f api

# 查看Weaviate日志
docker-compose logs -f weaviate

# 查看Neo4j日志
docker-compose logs -f neo4j
```

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 联系方式

如有问题或建议，请通过以下方式联系：

- 项目Issues: [GitHub Issues](https://github.com/your-repo/ai-knowledge-base/issues)
- 邮箱: your.email@example.com

## 更新日志

### v1.0.0 (2024-01-01)
- 初始版本发布
- 实现DDD四层架构
- 支持Weaviate和Neo4j数据库
- 提供REST API接口
- 完整的单元测试覆盖