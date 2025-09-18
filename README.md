# GBAI Demo

AI Agent Runtime System - 一个基于Python的智能代理运行时系统，提供多模态对话、工具执行和状态管理功能。

## 📋 目录

- [项目架构](#项目架构)
- [快速开始](#快速开始)
- [部署指南](#部署指南)
- [开发指南](#开发指南)
- [测试指南](#测试指南)
- [API文档](#api文档)
- [贡献指南](#贡献指南)

## 🏗️ 项目架构

### 核心模块

```
src/agent_runtime/
├── agents/                 # AI代理实现
│   ├── base.py            # 基础代理类
│   ├── bqa_agent.py       # 问答代理
│   ├── chapter_*.py       # 章节处理代理
│   ├── reward_agent.py    # 奖励评估代理
│   └── select_actions_agent.py # 动作选择代理
├── services/              # 业务服务层
│   ├── chat_v1_5_service.py    # 聊天服务 (主要API)
│   ├── feedback_service.py     # 反馈处理服务
│   ├── bqa_extract_service.py  # 问答提取服务
│   └── backward_service.py     # 反向推理服务
├── data_format/           # 数据格式定义
│   ├── message.py         # 消息格式
│   ├── case.py           # 案例格式
│   ├── context.py        # 上下文格式
│   ├── fsm.py            # 状态机格式
│   └── tool/             # 工具相关格式
├── clients/               # 外部客户端
│   ├── llm/              # LLM客户端
│   └── weaviate_client.py # 向量数据库客户端
├── config/                # 配置管理
├── interface/             # API接口定义
├── logging/               # 日志系统
└── utils/                 # 工具函数
```

### 前端界面

```
playground/                # Streamlit Web界面
├── pages/                # 页面组件
│   ├── agent_page.py     # 代理交互页面
│   ├── ospa_page.py      # OSPA模型页面
│   ├── bqa_extract_page.py # 问答提取页面
│   └── config_page.py    # 配置页面
├── components/           # 通用组件
├── config/              # 前端配置
└── app.py               # 主应用入口
```

### 技术栈

- **后端**: Python 3.12+, FastAPI, Pydantic
- **前端**: Streamlit
- **数据库**: Weaviate (向量数据库), Neo4j (图数据库)
- **LLM**: OpenAI API
- **部署**: Docker, Docker Compose
- **开发工具**: Poetry, UV

## 🚀 快速开始

### 1. 环境准备

确保已安装以下工具：
- Python 3.12+
- uv (Python环境管理)
- Poetry (包依赖管理)
- Docker & Docker Compose

### 2. 项目设置

```bash
# 克隆项目
git clone <repository-url>
cd gbai_demo

# 创建Python环境
uv venv -p 3.12.8

# 激活虚拟环境
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate     # Windows

# 安装依赖
poetry install
```

### 3. 环境配置

```bash
# 复制环境配置文件
cp .env.example .env

# 编辑配置文件，设置必要的API密钥
# OPENAI_API_KEY=your_openai_api_key
# WEAVIATE_URL=http://localhost:8855
# NEO4J_URI=bolt://localhost:7687
```

### 4. 启动服务

```bash
# 启动数据库服务
docker compose up -d

# 验证服务状态
docker compose ps

# 启动后端API服务
python -m uvicorn agent_runtime.main:app --reload --host 0.0.0.0 --port 8011

# 启动前端界面 (新终端)
cd playground
streamlit run app.py
```

### 5. 访问服务

- **API文档**: http://localhost:8011/docs
- **前端界面**: http://localhost:8501
- **Weaviate**: http://localhost:8855
- **Neo4j Browser**: http://localhost:7473 (用户名: neo4j, 密码: password)

## 🚀 部署指南

### Docker部署

1. **构建镜像**
```bash
# 构建后端镜像
docker build -t gbai-demo-backend .

# 构建前端镜像
cd playground
docker build -t gbai-demo-frontend .
```

2. **使用Docker Compose**
```bash
# 生产环境部署
docker compose -f docker-compose.prod.yml up -d

# 检查服务状态
docker compose ps
```

### 生产环境配置

1. **环境变量**
```bash
# 生产环境变量
ENVIRONMENT=production
LOG_LEVEL=INFO
OPENAI_API_KEY=your_production_api_key
WEAVIATE_URL=your_weaviate_url
NEO4J_URI=your_neo4j_uri
```

2. **反向代理**
```nginx
# Nginx配置示例
upstream backend {
    server localhost:8011;
}

upstream frontend {
    server localhost:8501;
}

server {
    listen 80;
    server_name your-domain.com;

    location /api/ {
        proxy_pass http://backend/;
    }

    location / {
        proxy_pass http://frontend/;
    }
}
```

## 💻 开发指南

### 代码规范

1. **代码风格**
```bash
# 格式化代码
black src/
isort src/

# 类型检查
mypy src/
```

2. **提交前检查**
```bash
# 运行所有检查
poetry run black --check src/
poetry run isort --check-only src/
poetry run mypy src/
poetry run pytest
```

### 新增Agent

1. **继承基类**
```python
from agent_runtime.agents.base import BaseAgent

class MyAgent(BaseAgent):
    async def step(self, context):
        # 实现你的逻辑
        pass
```

2. **注册Agent**
```python
# 在services中使用
from agent_runtime.agents.my_agent import MyAgent

agent = MyAgent()
result = await agent.step(context)
```

### 新增Service

1. **创建服务类**
```python
from pydantic import BaseModel
from agent_runtime.data_format.message import Message

class MyService:
    async def process(self, input_data: BaseModel) -> Message:
        # 实现业务逻辑
        pass
```

2. **添加API端点**
```python
# 在interface/api.py中添加
@app.post("/my-endpoint")
async def my_endpoint(request: MyRequest):
    service = MyService()
    return await service.process(request)
```

### 数据格式

使用Pydantic模型定义所有数据结构：
```python
from pydantic import BaseModel
from typing import List, Optional

class MyDataFormat(BaseModel):
    field1: str
    field2: Optional[int] = None
    field3: List[str] = []
```

## 🧪 测试指南

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_specific.py

# 运行带覆盖率报告
pytest --cov=src/agent_runtime --cov-report=html

# 查看覆盖率报告
open htmlcov/index.html
```

### 测试结构

```
tests/
├── test_agents/          # Agent测试
├── test_services/        # Service测试
├── test_data_format/     # 数据格式测试
├── conftest.py          # 测试配置
└── fixtures/            # 测试数据
```

### 编写测试

```python
import pytest
from agent_runtime.services.chat_v1_5_service import ChatService

@pytest.mark.asyncio
async def test_chat_service():
    service = ChatService()
    response = await service.process_message("Hello")
    assert response.content is not None
```

### Demo测试

```bash
# 运行演示脚本
cd exps
python your_demo.py

# 注意：完成功能验证后请删除demo文件
```

## 📚 API文档

### 主要端点

1. **聊天接口**
   - `POST /chat/v1.5/completions` - 多模态聊天
   - `POST /chat/completions` - 标准聊天

2. **工具接口**
   - `POST /tools/execute` - 工具执行
   - `GET /tools/list` - 工具列表

3. **状态管理**
   - `GET /state/current` - 当前状态
   - `POST /state/update` - 更新状态

### 请求示例

```python
import httpx

# 聊天请求
response = httpx.post("http://localhost:8011/chat/v1.5/completions", json={
    "messages": [
        {"role": "user", "content": "Hello, how are you?"}
    ],
    "model": "gpt-4",
    "stream": False
})
```

## 🤝 贡献指南

### 贡献流程

1. **Fork项目** - 在GitHub上fork这个仓库
2. **创建分支** - `git checkout -b feature/amazing-feature`
3. **开发功能** - 遵循代码规范和架构设计
4. **运行测试** - 确保所有测试通过
5. **提交代码** - `git commit -m 'Add amazing feature'`
6. **推送分支** - `git push origin feature/amazing-feature`
7. **创建PR** - 在GitHub上创建Pull Request

### 代码审查

- 所有PR需要至少一人审查
- 确保测试覆盖率不低于80%
- 遵循项目的代码风格
- 更新相关文档

### 问题报告

如果发现bug或有功能建议：
1. 检查是否已有相关issue
2. 创建新issue，提供详细描述
3. 标明bug复现步骤或功能需求

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 联系方式

- 项目维护者: Orion Zou <orionzou@clonebot.ai>
- 项目地址: [GitHub Repository](repository-url)
- 文档地址: [Documentation](docs-url)