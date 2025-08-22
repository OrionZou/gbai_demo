# AI知识库项目架构设计文档

## 1. 项目概述

本项目是一个基于DDD四层架构的AI知识库系统，严格按照需求实现以下4个核心功能：

1. **Weaviate Vector DB Client** (Infrastructure层) - 具有创建collection、导入数据、查询等功能
2. **Neo4j Graph DB Client** (Infrastructure层) - 具有创建collection、导入数据、查询等功能
3. **数据导入实体类** - 使用Pydantic实现，参考oss'pa案例，支持链式数据结构和历史追溯
4. **Docker部署环境** - Weaviate和Neo4j一键部署，数据目录挂载和gitignore配置

## 2. 架构设计

### 2.1 DDD四层架构

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

### 2.2 核心模块设计（简化版）

#### 2.2.1 Domain Layer (领域层)
- **核心实体类 (使用Pydantic)**
  - `ConversationRecord`: 对话记录实体（基于oss'pa案例结构）
  - `RecordChain`: 记录链条管理

#### 2.2.2 Application Layer (应用层)
- **核心服务**
  - `DataImportService`: 数据导入服务

#### 2.2.3 Infrastructure Layer (基础设施层)
- **数据库客户端（核心功能）**
  - `WeaviateClient`: Vector DB客户端 - 创建collection、导入数据、查询
  - `Neo4jClient`: Graph DB客户端 - 创建collection、导入数据、查询

#### 2.2.4 Interface Layer (接口层)
- **简化API**
  - `DataController`: 数据操作控制器

## 3. Pydantic实体类设计

### 3.1 ConversationRecord (对话记录实体)

基于oss'pa案例数据结构，使用Pydantic实现：

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Set
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum




class NodeType(str, Enum):
    CHAPTER = "chapter"
    STEP = "step"


class Node(BaseModel):
    node_id: UUID = Field(default_factory=uuid4, description="节点唯一标识")
    node_type: NodeType = Field(..., description="节点类型")
    node_name: str = Field(..., description="节点名称")
    node_description: str = Field("", description="节点描述")
    node_detail: str = Field("", description="节点详细信息")

    last_node_id: Optional[UUID] = Field(None, description="上一节点的 id")
    next_node_id: Optional[UUID] = Field(None, description="下一节点的 id")

    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    model_config = {
        "use_enum_values": True,  # JSON 序列化时输出枚举值
    }

    def link_previous(self, previous_record: 'ConversationRecord') -> None:
        """链接到上一条记录"""
        self.previous_record_id = previous_record.record_id
        previous_record.next_record_id = self.record_id
        



class Memory_State(BaseModel):
    """对话记录实体 关联的记忆状态"""
    state_content_set Set[Node] = Field(default_factory=set, description="记忆状态的 key 的集合")
    state_step: str = Field(description="记忆状态的当前 step")
    state_detail = Field(description="之前记忆状态 (s)")

class ActionType(str, Enum):
    OUTTER = "outter"
    INNER = "inner"
     = "end"

class EexcState(str, Enum):
    """动作执行状态"""
    PENDING = "pending"       # 待执行
    RUNNING = "running"       # 执行中
    SUCCESS = "success"       # 执行成功
    FAILED = "failed"         # 执行失败
    SKIPPED = "skipped"       # 跳过
    

class Action(BaseModel):
    action_type: ActionType = Field(..., description="动作类型，OUTTER表示AI对外动作，例如，与用户对话；INNER表示 AI 对内动作，例如，AI 执行工具")
    output: str = Field(..., description="INNER类型，表示工具执行结果；OUTTER类型，表示输出对话")
    exec_state: EexcState = Field(..., description="表示动作执行状态")
    exec_error: str = Field("", description="表示NNER类型下工具执行报错信息，OUTTER类型下为空")



class ConversationRecord(BaseModel):
    """对话记录实体 - 基于oss'pa案例结构"""
    record_id: UUID = Field(default_factory=uuid4, description="记录唯一标识")
    sequence_number: int = Field(description="序号 (No.)")
    user_profile: Optional[str] = Field(description="用户信息")
    user_input: str = Field(description="用户输入")
    last_mem_state: Optional[Memory_State] = Field(description="之前记忆状态 (s)")
    current_mem_state: Optional[Memory_State] = Field(default=None, description="当前记忆状态 (s')")
    action: Action = Field(..., description="AI的输出")
    
    # 链式结构支持
    previous_record_id: Optional[UUID] = Field(default=None, description="上一条记录ID")
    next_record_id: Optional[UUID] = Field(default=None, description="下一条记录ID")
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }
    
    def link_previous(self, previous_record: 'ConversationRecord') -> None:
        """链接到上一条记录"""
        self.previous_record_id = previous_record.record_id
        previous_record.next_record_id = self.record_id
    
    def link_next(self, next_record: 'ConversationRecord') -> None:
        """链接到下一条记录"""
        self.next_record_id = next_record.record_id
        next_record.previous_record_id = self.record_id

class RecordChain(BaseModel):
    """记录链条管理"""
    chain_id: UUID = Field(default_factory=uuid4)
    records: List[ConversationRecord] = Field(default_factory=list)
    
    def add_record(self, record: ConversationRecord) -> None:
        """添加记录到链条"""
        if self.records:
            self.records[-1].link_next(record)
        self.records.append(record)
    
    def get_history_from(self, record_id: UUID) -> List[ConversationRecord]:
        """从指定记录获取历史链条"""
        history = []
        for record in self.records:
            if record.record_id == record_id:
                # 向前追溯历史
                current = record
                while current and current.previous_record_id:
                    prev_record = next((r for r in self.records if r.record_id == current.previous_record_id), None)
                    if prev_record:
                        history.insert(0, prev_record)
                        current = prev_record
                    else:
                        break
                history.append(record)
                break
        return history
```

## 4. Docker部署配置

### 4.1 docker-compose.yml

```yaml
version: '3.8'

services:
  weaviate:
    image: semitechnologies/weaviate:1.32.2
    ports:
      - "8855:8080"
    environment:
      QUERY_DEFAULTS_LIMIT: 25
      AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: 'true'
      PERSISTENCE_DATA_PATH: '/var/lib/weaviate'
      DEFAULT_VECTORIZER_MODULE: 'none'
      ENABLE_MODULES: 'text2vec-openai,generative-openai'
      CLUSTER_HOSTNAME: 'node1'
    volumes:
      - ./weaviate_db_data:/var/lib/weaviate
    restart: on-failure:0

  neo4j:
    image: neo4j:5.26.10
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      NEO4J_AUTH: neo4j/password
      NEO4J_PLUGINS: '["apoc"]'
      NEO4J_dbms_security_procedures_unrestricted: 'apoc.*'
    volumes:
      - ./neo4j_db_data:/data
      - ./neo4j_db_data/logs:/logs
      - ./neo4j_db_data/import:/var/lib/neo4j/import
      - ./neo4j_db_data/plugins:/plugins
    restart: unless-stopped
```

### 4.2 .gitignore配置

```gitignore
# 数据库数据目录
weaviate_db_data/
neo4j_db_data/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# 环境
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# IDE
.vscode/
.idea/
*.swp
*.swo

# 测试
.coverage
.pytest_cache/
htmlcov/

# uv
.uv/
```

## 5. 核心功能时序图

### 5.1 数据导入流程

```mermaid
sequenceDiagram
    participant Client
    participant DataController
    participant DataImportService
    participant WeaviateClient
    participant Neo4jClient

    Client->>DataController: POST /import/conversations
    DataController->>DataImportService: import_conversation_data
    DataImportService->>WeaviateClient: create_collection
    DataImportService->>WeaviateClient: import_vectors
    DataImportService->>Neo4jClient: create_collection
    DataImportService->>Neo4jClient: import_relationships
    DataImportService-->>DataController: ImportResult
    DataController-->>Client: HTTP 200 OK
```

### 5.2 数据查询流程

```mermaid
sequenceDiagram
    participant Client
    participant DataController
    participant WeaviateClient
    participant Neo4jClient

    Client->>DataController: GET /query/vector
    DataController->>WeaviateClient: vector_search
    WeaviateClient-->>DataController: search_results
    DataController-->>Client: HTTP 200 OK

    Client->>DataController: GET /query/graph
    DataController->>Neo4jClient: graph_query
    Neo4jClient-->>DataController: query_results
    DataController-->>Client: HTTP 200 OK
```

## 6. 数据库设计

### 6.1 Weaviate Schema

```python
WEAVIATE_SCHEMA = {
    "class": "ConversationRecord",
    "description": "对话记录向量存储",
    "properties": [
        {
            "name": "recordId",
            "dataType": ["string"],
            "description": "记录ID"
        },
        {
            "name": "userInput",
            "dataType": ["text"],
            "description": "用户输入"
        },
        {
            "name": "agentOutput", 
            "dataType": ["text"],
            "description": "代理输出"
        },
        {
            "name": "currentState",
            "dataType": ["string"],
            "description": "当前状态"
        },
        {
            "name": "nextState",
            "dataType": ["string"],
            "description": "下一状态"
        }
    ],
    "vectorizer": "text2vec-openai"
}
```

### 6.2 Neo4j Graph Schema

```cypher
// 对话记录节点
CREATE CONSTRAINT conversation_record_id IF NOT EXISTS FOR (c:ConversationRecord) REQUIRE c.recordId IS UNIQUE;

// 状态节点
CREATE CONSTRAINT state_name IF NOT EXISTS FOR (s:State) REQUIRE s.name IS UNIQUE;

// 关系定义
(:ConversationRecord)-[:NEXT_RECORD]->(:ConversationRecord)
(:ConversationRecord)-[:PREVIOUS_RECORD]->(:ConversationRecord)
(:ConversationRecord)-[:IN_STATE]->(:State)
(:State)-[:TRANSITIONS_TO]->(:State)
```

## 7. 技术栈

- **语言**: Python 3.12
- **包管理**: Poetry
- **环境管理**: uv
- **向量数据库**: Weaviate
- **图数据库**: Neo4j
- **数据验证**: Pydantic
- **测试框架**: pytest
- **类型检查**: mypy

## 8. 项目结构

```
ai_knowledge_base/
├── src/
│   ├── ai_knowledge_base/
│   │   ├── domain/
│   │   │   ├── entities/
│   │   │   ├── value_objects/
│   │   │   ├── repositories/
│   │   │   └── services/
│   │   ├── application/
│   │   │   ├── services/
│   │   │   └── use_cases/
│   │   ├── infrastructure/
│   │   │   ├── database/
│   │   │   ├── repositories/
│   │   │   └── clients/
│   │   └── interface/
│   │       ├── api/
│   │       ├── controllers/
│   │       └── dto/
├── tests/
├── docs/
├── pyproject.toml
├── uv.lock
└── README.md
```

## 9. 开发计划

1. **第一阶段**: 搭建基础架构和实体类
2. **第二阶段**: 实现数据库客户端
3. **第三阶段**: 实现应用服务和用例
4. **第四阶段**: 实现API接口
5. **第五阶段**: 编写测试和文档

## 10. 质量保证

- **测试覆盖率**: 100%
- **代码质量**: 使用mypy进行类型检查
- **文档**: 完整的API文档和架构文档
- **性能**: 向量检索和图查询性能优化