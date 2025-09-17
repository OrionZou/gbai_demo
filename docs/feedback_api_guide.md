# Feedback API 使用指南

基于FeedbackService的反馈管理API，提供学习、获取和删除反馈的完整功能。

## 🚀 快速开始

### 1. 启动服务

```bash
# 确保Weaviate运行
docker run -p 8080:8080 semitechnologies/weaviate:latest

# 启动API服务器
cd exps
python feedback_api_server.py
```

API文档将在以下地址可用：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 2. 环境配置

```bash
# 可选：设置OpenAI API密钥以获得更好的嵌入效果
export OPENAI_API_KEY="your-openai-api-key"
```

## 📚 API接口

### Learn API - 学习反馈

**POST** `/feedback/learn`

添加新的反馈到系统中进行学习。

```json
{
  "agent_name": "my_agent",
  "feedbacks": [
    {
      "observation_name": "user_query",
      "observation_content": "用户询问Python编程问题",
      "action_name": "provide_answer",
      "action_content": "提供了详细的Python教程",
      "state_name": "teaching"
    }
  ],
  "vector_db_url": "http://localhost:8080",
  "top_k": 5
}
```

**响应：**
```json
{
  "success": true,
  "message": "Successfully learned 1 feedbacks",
  "feedback_ids": ["uuid1", "uuid2"],
  "count": 10
}
```

### Get API - 获取/搜索反馈

**POST** `/feedback/get`

支持普通获取和语义搜索两种模式。

#### 普通获取（分页）

```json
{
  "agent_name": "my_agent",
  "vector_db_url": "http://localhost:8080",
  "offset": 0,
  "limit": 10
}
```

#### 语义搜索

```json
{
  "agent_name": "my_agent",
  "vector_db_url": "http://localhost:8080",
  "query": "Python编程学习",
  "tags": ["observation_name_user_query"],
  "top_k": 5
}
```

**响应：**
```json
{
  "success": true,
  "message": "Retrieved 5 feedbacks",
  "feedbacks": [...],
  "total_count": 100,
  "query_count": 5
}
```

### Delete API - 删除反馈

**POST** `/feedback/delete`

支持删除所有反馈或删除整个集合。

```json
{
  "agent_name": "my_agent",
  "vector_db_url": "http://localhost:8080",
  "delete_type": "all"  // "all" 或 "collection"
}
```

**响应：**
```json
{
  "success": true,
  "message": "All 10 feedbacks deleted for agent 'my_agent'",
  "deleted_count": 10
}
```

### Stats API - 获取统计

**GET** `/feedback/stats/{agent_name}`

```bash
curl "http://localhost:8000/feedback/stats/my_agent"
```

**响应：**
```json
{
  "agent_name": "my_agent",
  "feedback_count": 25,
  "has_embeddings": true
}
```

## 🔧 使用示例

### Python客户端

```python
import asyncio
import httpx

async def learn_and_search():
    async with httpx.AsyncClient() as client:
        # 学习反馈
        learn_data = {
            "agent_name": "demo_agent",
            "feedbacks": [{
                "observation_name": "user_query",
                "observation_content": "用户询问机器学习",
                "action_name": "explain_ml",
                "action_content": "详细解释了机器学习概念",
                "state_name": "teaching"
            }]
        }

        response = await client.post(
            "http://localhost:8000/feedback/learn",
            json=learn_data
        )
        print(f"学习结果: {response.json()}")

        # 语义搜索
        search_data = {
            "agent_name": "demo_agent",
            "query": "机器学习基础",
            "top_k": 3
        }

        response = await client.post(
            "http://localhost:8000/feedback/get",
            json=search_data
        )
        print(f"搜索结果: {response.json()}")

asyncio.run(learn_and_search())
```

### cURL示例

```bash
# 学习反馈
curl -X POST "http://localhost:8000/feedback/learn" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "test_agent",
    "feedbacks": [{
      "observation_name": "user_question",
      "observation_content": "用户问题内容",
      "action_name": "respond",
      "action_content": "回答内容",
      "state_name": "helping"
    }]
  }'

# 语义搜索
curl -X POST "http://localhost:8000/feedback/get" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "test_agent",
    "query": "搜索关键词",
    "top_k": 5
  }'

# 获取统计
curl "http://localhost:8000/feedback/stats/test_agent"
```

## 🎯 高级功能

### 1. 标签过滤

反馈系统自动为每个反馈生成标签：
- `state_name_` + 状态名称
- `observation_name_` + 观察名称

```json
{
  "query": "Python编程",
  "tags": ["observation_name_user_query", "state_name_teaching"]
}
```

### 2. OpenAI嵌入集成

当设置`OPENAI_API_KEY`环境变量时，系统将：
- 使用OpenAI API计算高质量嵌入向量
- 提供更准确的语义搜索
- 自动回退到哈希嵌入（当API不可用时）

### 3. 批量处理

Learn API支持批量添加反馈，提高效率：

```json
{
  "agent_name": "my_agent",
  "feedbacks": [
    // 可以包含多个反馈对象
    {"observation_name": "...", ...},
    {"observation_name": "...", ...},
    {"observation_name": "...", ...}
  ]
}
```

## 🐛 故障排除

### 常见问题

1. **Weaviate连接失败**
   ```
   确保Weaviate运行在 http://localhost:8080
   docker run -p 8080:8080 semitechnologies/weaviate:latest
   ```

2. **OpenAI API错误**
   ```
   检查OPENAI_API_KEY环境变量
   系统会自动回退到哈希嵌入
   ```

3. **内存不足**
   ```
   调整批量大小和limit参数
   使用分页获取大量数据
   ```

### 错误响应

API返回标准的HTTP状态码：
- `200`: 成功
- `400`: 请求参数错误
- `500`: 服务器内部错误

错误响应格式：
```json
{
  "detail": "错误描述信息"
}
```

## 📊 性能优化

1. **批量操作**: 尽量批量添加反馈而不是逐个添加
2. **分页查询**: 对于大量数据使用offset和limit参数
3. **标签过滤**: 使用标签减少搜索范围
4. **嵌入缓存**: OpenAI嵌入会被自动缓存

## 🔗 相关文件

- `src/agent_runtime/interface/feedback_api.py` - API实现
- `src/agent_runtime/services/feedback_service.py` - 核心服务
- `exps/feedback_api_server.py` - 服务器启动脚本
- `exps/test_feedback_api.py` - API测试脚本
- `exps/feedback_api_example.py` - 使用示例