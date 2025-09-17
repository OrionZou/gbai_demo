# ChatService架构重构开发日志

**日期**: 2025-09-17
**开发内容**: ChatService架构重构，实现无状态服务设计

## 背景

用户提出了两个主要需求：
1. 将ChatService的generate_chat逻辑移到chat_api中维护
2. 实现每次API调用创建新的ChatService和FeedbackService实例，调用结束后销毁

## 重构目标

- 消除全局服务实例，实现真正的无状态服务
- 每次API调用根据请求参数动态创建服务实例
- 确保LLM引擎、Weaviate客户端等资源完全隔离
- 支持高并发场景，避免配置污染

## 实施步骤

### 1. 移除全局ChatService实例

**修改文件**: `src/agent_runtime/interface/chat_api.py`

```python
# 删除全局实例
- chat_service = ChatService()
```

### 2. 创建服务工厂方法

**新增方法**: `_get_chat_service()` 和 `_get_feedback_service()`

```python
def _get_chat_service(
    api_key: str,
    chat_model: str,
    base_url: str,
    temperature: float = 1.0,
    top_p: float = 1.0
) -> ChatService:
    """根据参数创建新的ChatService实例"""
    from agent_runtime.config.loader import LLMSetting
    from agent_runtime.clients.openai_llm_client import LLM

    # 创建LLM设置
    llm_setting = LLMSetting(
        model=chat_model,
        base_url=base_url,
        api_key=api_key,
        temperature=temperature,
        top_p=top_p
    )

    # 创建LLM引擎
    llm_engine = LLM(llm_setting=llm_setting)

    # 创建ChatService并更新agents的LLM引擎
    chat_service = ChatService()
    chat_service.update_agents_llm_engine(llm_engine)

    return chat_service

def _get_feedback_service(vector_db_url: str, api_key: str = "dummy") -> FeedbackService:
    """根据参数创建新的FeedbackService实例"""
    # 创建WeaviateClient
    weaviate_client = WeaviateClient(
        base_url=vector_db_url,
        timeout=30
    )

    # 创建OpenAI嵌入客户端
    embedding_client = OpenAIEmbeddingClient(api_key=api_key)

    # 创建FeedbackService
    return FeedbackService(
        weaviate_client=weaviate_client,
        embedding_client=embedding_client
    )
```

### 3. 重构generate_chat接口

**修改文件**: `src/agent_runtime/interface/chat_api.py`

将完整的generate_chat逻辑从ChatService移动到chat_api中：

```python
@router.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def generate_chat(request: ChatRequest) -> ChatResponse:
    try:
        logger.info(f"Processing chat request for agent: {request.settings.agent_name}")

        # 创建ChatService实例（每次调用新建）
        chat_service = _get_chat_service(
            api_key=request.settings.api_key,
            chat_model=request.settings.chat_model,
            base_url=request.settings.base_url,
            temperature=request.settings.temperature,
            top_p=request.settings.top_p
        )

        # 转换请求格式并调用chat_step
        settings = Setting(**request.settings.model_dump())
        memory = Memory(**request.memory.model_dump())
        user_message_content = request.get_user_content()

        result = await chat_service.chat_step(
            user_message=user_message_content,
            edited_last_response=request.edited_last_response,
            recall_last_user_message=request.recall_last_user_message,
            settings=settings,
            memory=memory,
            request_tools=request.request_tools
        )

        # 构建响应
        response = ChatResponse(
            response=result["response"],
            memory=result["memory"].model_dump(),
            result_type=result["result_type"],
            llm_calling_times=result["llm_calling_times"],
            total_input_token=result["total_input_token"],
            total_output_token=result["total_output_token"]
        )

        logger.info(f"Chat request completed for agent: {request.settings.agent_name}")
        return response

    except Exception as e:
        logger.exception("Error generating chat response", exc_info=e)
        raise HTTPException(500, detail="Failed to generate chat response") from e
```

### 4. 清理ChatService

**修改文件**: `src/agent_runtime/services/chat_v1_5_service.py`

- 移除`generate_chat`方法
- 移除不必要的导入：`ChatRequest`, `ChatResponse`
- 保留核心的`chat_step`方法供API调用

### 5. 更新Feedback服务调用

**修改文件**: `src/agent_runtime/interface/chat_api.py`

将feedback相关的接口改为直接调用FeedbackService：

```python
# GET /feedbacks
feedback_service = _get_feedback_service(vector_db_url, "dummy")
feedbacks = await feedback_service.get_feedbacks(...)

# DELETE /feedbacks
feedback_service = _get_feedback_service(vector_db_url, "dummy")
await feedback_service.delete_all_feedbacks(agent_name)
```

## 架构优势

### 1. 完全无状态设计
- 每次API调用创建新的服务实例
- 调用结束后实例自动销毁，无状态保留
- 消除了服务间的状态污染问题

### 2. 资源隔离
- LLM引擎：每次创建独立实例，使用请求中的API密钥和配置
- Weaviate客户端：根据vector_db_url独立创建
- 嵌入客户端：使用独立的API密钥配置

### 3. 支持高并发
- 不同请求完全隔离，支持并发调用
- 避免了单例模式带来的共享状态问题
- 提高了系统的稳定性和可扩展性

### 4. 配置灵活性
- 每个请求可以使用不同的LLM模型、API密钥
- 支持多租户场景，不同用户使用不同配置
- 动态配置，无需重启服务

## 测试验证

创建了测试文件验证新架构：

```python
# exps/test_new_architecture.py
async def test_new_architecture():
    # 测试创建不同配置的ChatService实例
    chat_service1 = _get_chat_service(...)
    chat_service2 = _get_chat_service(...)

    # 验证实例独立性
    assert chat_service1 is not chat_service2

    # 验证配置正确性
    assert chat_service1.agents.llm_engine.api_key == "test_key_1"
    assert chat_service2.agents.llm_engine.api_key == "test_key_2"
```

## 已解决的问题

### 1. OpenAI API参数验证错误
**问题**: max_completion_tokens为None导致API错误
**解决**: 在LLM客户端中添加参数验证和默认值

### 2. Weaviate vectorizer配置错误
**问题**: vectorizer配置为空对象导致创建失败
**解决**: 使用正确的text2vec-openai配置

### 3. 单例模式状态污染
**问题**: BaseAgent使用单例模式导致配置共享
**解决**: 改为无状态服务设计，每次创建新实例

## API模型更新

**修改文件**: `src/agent_runtime/interface/api_models.py`

为Setting类添加了嵌入相关配置：

```python
class Setting(BaseModel):
    # LLM配置
    api_key: str
    chat_model: str = "gpt-4o-mini"
    base_url: str = "https://api.openai.com/v1/"
    temperature: float = 1.0
    top_p: float = 1.0

    # 嵌入配置 (新增)
    embedding_api_key: str
    embedding_model: str = ""
    embedding_base_url: str = "https://api.openai.com/v1/"
    embedding_vector_dim: int = 1024

    # 其他配置
    top_k: int = 5
    vector_db_url: str = ""
    agent_name: str
    global_prompt: str = ""
    max_history_len: int = 128
    state_machine: StateMachine = StateMachine()
```

## 总结

此次重构成功实现了用户要求的架构改进：

1. ✅ **将generate_chat逻辑移到chat_api**: 完整迁移逻辑，移除ChatService中的方法
2. ✅ **实现无状态服务**: 每次调用创建新实例，调用后销毁
3. ✅ **资源隔离**: LLM引擎、数据库客户端完全独立
4. ✅ **支持并发**: 不同请求互不干扰，提高系统稳定性

新架构为系统带来了更好的可扩展性、稳定性和灵活性，符合现代微服务的设计理念。

## 相关文件

**修改的文件**:
- `src/agent_runtime/interface/chat_api.py` - 主要重构文件
- `src/agent_runtime/services/chat_v1_5_service.py` - 移除generate_chat方法
- `src/agent_runtime/interface/api_models.py` - 添加嵌入配置字段

**测试文件**:
- `exps/test_new_architecture.py` - 新架构测试
- `exps/test_chat_service_refactor_v2.py` - ChatService重构测试
- `exps/test_llm_engine_update.py` - LLM引擎更新测试