# SelectActionsAgent重构和Token_Counter移除 - 2025-09-17

## 任务概述

本次开发主要完成了两个任务：
1. 参考 `reward_agent.py` 重构 `select_actions_agent.py`
2. 完全移除 `agent_runtime` 中所有 `token_counter` 相关内容

## 1. SelectActionsAgent重构

### 重构目标
参考 `reward_agent.py` 的设计模式，使 `select_actions_agent.py` 具有相同的架构风格和代码结构。

### 主要改进

#### 1.1 构造函数重构
- **修改前**: LLM引擎为可选参数，会在构造函数中创建默认实例
- **修改后**: LLM引擎为必需参数，与reward_agent保持一致
- **参数顺序调整**: 调整为与reward_agent一致的参数顺序

```python
# 修改前
def __init__(
    self,
    agent_name: Optional[str] = None,
    llm_engine: Optional[LLM] = None,  # 可选参数
    system_prompt: Optional[str] = None,
    user_prompt_template: Optional[str] = None
):

# 修改后
def __init__(
    self,
    llm_engine: LLM,  # 必需参数
    agent_name: Optional[str] = None,
    system_prompt: Optional[str] = None,
    user_prompt_template: Optional[str] = None,
):
```

#### 1.2 Step方法简化
- **修改前**: 复杂的方法调用链，核心逻辑分散在多个私有方法中
- **修改后**: 将核心逻辑整合到step方法中，减少方法数量

#### 1.3 代码精简
- 移除了冗余的 `_select_actions` 私有方法
- 移除了重复的 `_parse_tool_calls` 方法
- 只保留了必要的 `_parse_tool_calls_from_message` 方法

### 重构效果
- 代码更加简洁和一致
- 与项目中其他agent保持相同的设计模式
- 减少了代码复杂度，提高了可维护性

## 2. Token_Counter完全移除

### 移除范围
完全移除了 `src/agent_runtime` 目录中所有与 `token_counter` 和 `TokenCounter` 相关的代码。

### 2.1 删除的文件
- `src/agent_runtime/stats/` 整个目录
  - `__init__.py`
  - `token_counter.py`

### 2.2 修改的文件

#### 2.2.1 data_format/__init__.py
- 移除 `from ..stats import TokenCounter` 导入
- 从 `__all__` 列表中移除 `"TokenCounter"`

#### 2.2.2 clients/openai_llm_client.py
- 移除 `TokenCounter` 导入
- 从以下方法中移除 `token_counter` 参数：
  - `ask()` 方法
  - `ask_tool()` 方法
  - `structured_output()` 方法
  - `structured_output_old()` 方法
- 移除所有token计数逻辑

#### 2.2.3 agents/state_select_agent.py & agents/new_state_agent.py
- 移除文档注释中的token_counter说明
- 移除step方法中的token_counter获取和使用

#### 2.2.4 data_format/v2_core.py
- 移除 `TokenCounter` 导入
- 更新 `chat()` 函数返回类型从 `Tuple[Memory, TokenCounter]` 改为 `Memory`
- 移除token_counter参数和相关逻辑

#### 2.2.5 services/chat_v1_5_service.py
- 移除 `TokenCounter` 导入和初始化
- 更新所有相关方法签名，移除token_counter参数：
  - `chat()` 方法
  - `_select_next_state()` 方法
  - `_select_next_actions()` 方法
- 修复SelectActionsAgent初始化，添加必需的llm_engine参数
- 更新agent引擎更新方法，包含SelectActionsAgent

## 3. Bug修复

### 3.1 FeedbackSetting参数缺失
**问题**: FeedbackSetting创建时缺少必需的 `embedding_api_key` 参数
**解决**: 在两处FeedbackSetting创建中添加 `embedding_api_key=settings.embedding_api_key or ""`

### 3.2 Action Arguments访问错误
**问题**: `action.arguments.get()` 调用时arguments可能为None
**解决**: 改为 `(action.arguments or {}).get("agent_message", "")`

### 3.3 Weaviate查询限制超出
**问题**: 查询limit设置为20000，超出了Weaviate的限制
**解决**: 将feedback_service.py中的两处limit值从20000调整为10000

## 4. 技术收益

### 4.1 代码一致性
- 所有Agent现在遵循相同的设计模式
- 构造函数参数和方法签名保持一致

### 4.2 性能优化
- 移除了token计数开销
- 简化了方法调用链

### 4.3 维护性提升
- 减少了代码重复
- 降低了系统复杂度
- 统一了错误处理模式

## 5. 测试验证

所有修改完成后：
- 代码编译无错误
- 类型检查通过
- 导入依赖正确
- 运行时无token_counter相关错误

## 6. 注意事项

1. **向后兼容性**: 移除token_counter是破坏性变更，需要更新所有调用代码
2. **Agent初始化**: SelectActionsAgent现在需要显式传入llm_engine参数
3. **FeedbackSetting**: 需要确保settings对象包含有效的embedding_api_key
4. **查询限制**: Weaviate查询现在限制在10000条记录以内

## 7. 后续建议

1. 考虑为FeedbackSetting的embedding_api_key提供更好的默认值处理
2. 可以考虑将Weaviate的查询limit设为可配置参数
3. 统一所有Agent的错误处理和日志记录方式