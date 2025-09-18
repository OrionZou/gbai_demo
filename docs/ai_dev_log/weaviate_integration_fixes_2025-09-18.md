# Weaviate集成问题修复 - 2025-09-18

## 任务概述

修复了一系列与 Weaviate 集成相关的问题，包括维度配置、ID 生成、API 接口优化等。

## 1. 向量维度配置问题

### 1.1 问题描述
```
new node has a vector with length 1024. Existing nodes have vectors with length 384
```

**根本原因**:
- 历史数据使用 384 维向量
- 新配置默认使用 1024 维向量
- Weaviate 要求同一集合中所有向量维度必须一致

### 1.2 解决方案
统一使用 1024 维作为标准：

**修改文件**:
- `src/agent_runtime/interface/api_models.py`: `embedding_vector_dim` 默认值设为 1024
- `src/agent_runtime/interface/chat_api.py`: 硬编码维度值改为 1024
- `src/agent_runtime/services/feedback_service.py`: 集合创建时指定正确维度

**配置更新**:
```python
# 集合创建时明确指定维度
vector_config = {
    "default": {
        "vectorizer": {
            "none": {}  # 使用手动向量
        },
        "vectorIndexType": "hnsw",
        "vectorIndexConfig": {
            "efConstruction": 128,
            "maxConnections": 64,
            "distance": "cosine",
        },
    }
}
```

## 2. Weaviate集合创建配置问题

### 2.1 问题描述
```
class.VectorConfig.Vectorizer must consist only 1 configuration, got: 0
```

**原因**: `"vectorizer": {}` 空配置导致 Weaviate 验证失败

### 2.2 解决方案
使用正确的 vectorizer 配置：
```python
"vectorizer": {
    "none": {}  # 明确指定使用手动向量
}
```

## 3. UUID生成重复问题

### 3.1 问题描述
```
id 'c9d7a8c4-079a-49f5-88f9-2f3d0997959c' already exists
```

**根本原因**: Python 默认参数陷阱
```python
# 错误的写法 - 在函数定义时执行一次
def create_object(object_id: str = str(uuid.uuid4())):
    # 每次调用都使用相同的 UUID
```

### 3.2 解决方案
**修改前**:
```python
object_id: str = str(uuid.uuid4()),  # ❌ 每次都是同一个ID
```

**修改后**:
```python
object_id: Optional[str] = None,  # ✅ 正确
if object_id is None:
    object_id = str(uuid.uuid4())  # ✅ 每次生成新ID
```

**效果**: 每个 feedback 现在都获得唯一的 UUID，不会再有 ID 冲突。

## 4. API接口增强

### 4.1 Learn接口示例完善
为 `/v1.5/learn` 接口的示例添加了完整的配置字段：

```json
{
  "settings": {
    "vector_db_url": "http://weaviate:8080",
    "agent_name": "TestAgent",
    "embedding_api_key": "your-openai-api-key-here",
    "embedding_model": "text-embedding-3-small",
    "embedding_base_url": "https://api.openai.com/v1/"
  }
}
```

### 4.2 新增删除集合接口
添加了 `DELETE /v1.5/collections/{agent_name}` 接口：

**功能**: 完全删除指定 agent 的整个 Weaviate 集合
**用法**:
```bash
curl -X 'DELETE' \
  'http://localhost:8011/v1.5/collections/SalesHelper?vector_db_url=http://117.50.48.254:80/weaviate'
```

**优化**: 移除了不必要的 `embedding_api_key` 参数，因为删除操作不需要 embedding API。

### 4.3 健康检查接口
在 `main.py` 中添加了根路径健康检查：

```python
@app.get("/", tags=["Health"])
async def health_check():
    return {"status": "ok"}
```

## 5. 类型安全改进

### 5.1 修复空指针访问
**问题**: `self.embedding_client.dimensions` 可能为 None
**解决**: 使用 `getattr(self.embedding_client, 'dimensions', None) or 1024`

### 5.2 修复Weaviate查询限制
将查询限制从 20000 调整为 10000，避免 "query maximum results exceeded" 错误。

## 6. 技术收益

### 6.1 稳定性提升
- 消除了 UUID 重复导致的插入失败
- 解决了向量维度不匹配问题
- 修复了集合创建配置错误

### 6.2 API完善
- 提供了完整的集合管理能力（创建、删除）
- 改进了接口文档和示例
- 添加了健康检查端点

### 6.3 开发体验
- 更清晰的错误处理和日志
- 统一的维度配置管理
- 类型安全的代码实现

## 7. 验证结果

**成功删除测试**:
```
2025-09-18 00:12:04 | INFO | All feedbacks deleted from SalesHelper
HTTP/1.1 204 No Content
```

**新的数据插入**:
- 现在使用 1024 维向量
- 每个 feedback 获得唯一 UUID
- 集合配置正确，支持手动向量

## 8. 后续建议

1. **数据迁移**: 如果有重要的历史数据，考虑先导出再重新导入
2. **监控**: 添加向量维度的运行时验证
3. **配置管理**: 考虑将维度设置改为配置文件管理，而不是硬编码
4. **文档更新**: 更新API文档，说明新的集合删除接口用法