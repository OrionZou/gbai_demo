# Agent配置统一更新功能

## 🎯 功能概述

现在通过 `/agent/config` 接口更新LLM配置时，系统会自动更新所有services中的agent配置，确保配置的一致性。

## 🔧 实现原理

### 问题背景
由于BaseAgent使用单例模式，当通过config接口更新LLM配置时，已经创建的Agent实例仍然使用旧的LLM客户端，导致配置不一致。

### 解决方案
1. **BaseAgent类增强**: 添加全局更新LLM引擎的类方法
2. **API接口改进**: 在config更新时同步更新所有Agent实例
3. **状态监控**: 提供Agent状态查询接口

## 📋 新增API接口

### 1. 获取Agent状态
```http
GET /agent/config/agents
```

**响应示例**:
```json
{
  "current_llm_config": {
    "model": "gpt-4-turbo-preview",
    "api_key": "sk-xxx...",
    "base_url": "https://api.openai.com/v1", 
    "temperature": 0.2
  },
  "total_agents": 4,
  "agent_instances": {
    "reward_agent": {
      "class_name": "RewardAgent",
      "agent_name": "reward_agent",
      "llm_model": "gpt-4-turbo-preview",
      "initialized": true
    },
    "cqa_agent": {
      "class_name": "CQAAgent", 
      "agent_name": "cqa_agent",
      "llm_model": "gpt-4-turbo-preview",
      "initialized": true
    }
  },
  "services_status": {
    "reward_service": {
      "llm_model": "gpt-4-turbo-preview"
    },
    "backward_service": {
      "llm_model": "gpt-4-turbo-preview"
    },
    "agent_prompt_service": {
      "llm_model": "gpt-4-turbo-preview"
    }
  }
}
```

### 2. 更新配置（增强版）
```http
POST /agent/config
```

**新增响应字段**:
```json
{
  "message": "配置已更新，所有services和agent实例已同步更新",
  "config": { /* 新的LLM配置 */ },
  "updated_agents": 4,
  "agent_instances": { /* 更新后的Agent实例信息 */ }
}
```

## 🏗️ 代码实现

### BaseAgent类增强

#### 1. 单个实例更新
```python
def update_llm_engine(self, llm_engine: LLM) -> None:
    """更新单个Agent实例的LLM引擎"""
    self.llm_engine = llm_engine
    logger.debug(f"LLM engine updated for agent {self.agent_name}")
```

#### 2. 全局批量更新
```python
@classmethod
def update_all_agents_llm_engine(cls, new_llm_engine: LLM) -> None:
    """更新所有已创建的Agent实例的LLM引擎"""
    with cls._lock:
        updated_count = 0
        for agent_name, agent_instance in cls._instances.items():
            if hasattr(agent_instance, 'update_llm_engine'):
                agent_instance.update_llm_engine(new_llm_engine)
                updated_count += 1
        logger.info(f"Updated LLM engine for {updated_count} agent instances")
```

#### 3. 状态查询
```python
@classmethod
def get_all_agent_instances(cls) -> Dict[str, Any]:
    """获取所有已创建的Agent实例信息"""
    with cls._lock:
        instances_info = {}
        for agent_name, agent_instance in cls._instances.items():
            instances_info[agent_name] = {
                'class_name': agent_instance.__class__.__name__,
                'agent_name': agent_instance.agent_name,
                'llm_model': getattr(agent_instance.llm_engine, 'model', 'unknown'),
                'initialized': agent_name in cls._initialized
            }
        return instances_info
```

### API接口更新流程

```python
@router.post("/config")
async def set_config(cfg: LLMSetting) -> dict:
    try:
        from agent_runtime.agents.base import BaseAgent
        
        # 1. 更新配置
        new_cfg = SettingLoader.set_llm_setting(cfg.model_dump(exclude_none=True))
        
        # 2. 创建新的LLM客户端
        llm_client = LLM(llm_setting=new_cfg)
        
        # 3. 更新所有Agent实例的LLM引擎
        BaseAgent.update_all_agents_llm_engine(llm_client)
        
        # 4. 重新创建所有services
        reward_service = RewardService(llm_client)
        backward_service = BackwardService(llm_client)
        agent_prompt_service = AgentPromptService(llm_client)
        
        # 5. 返回更新结果
        agent_instances_info = BaseAgent.get_all_agent_instances()
        return {
            "message": "配置已更新，所有services和agent实例已同步更新",
            "config": new_cfg.model_dump(),
            "updated_agents": len(agent_instances_info),
            "agent_instances": agent_instances_info
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新配置失败: {e}")
```

## 🚀 使用方法

### 1. 通过API更新配置
```bash
curl -X POST "http://localhost:8011/agent/config" \
     -H "Content-Type: application/json" \
     -d '{
       "api_key": "your_new_api_key",
       "model": "gpt-4-turbo-preview",
       "base_url": "https://api.openai.com/v1",
       "temperature": 0.2,
       "max_completion_tokens": 4096
     }'
```

### 2. 检查更新状态
```bash
curl -X GET "http://localhost:8011/agent/config/agents"
```

### 3. Python代码示例
```python
import aiohttp
import asyncio

async def update_config():
    new_config = {
        "api_key": "your_api_key",
        "model": "gpt-4-turbo-preview",
        "temperature": 0.1
    }
    
    async with aiohttp.ClientSession() as session:
        # 更新配置
        async with session.post(
            "http://localhost:8011/agent/config",
            json=new_config
        ) as response:
            result = await response.json()
            print(f"更新了 {result['updated_agents']} 个Agent实例")
        
        # 验证更新
        async with session.get(
            "http://localhost:8011/agent/config/agents"
        ) as response:
            status = await response.json()
            print(f"当前模型: {status['current_llm_config']['model']}")

asyncio.run(update_config())
```

## 📊 更新流程图

```
API Request (/config)
       ↓
1. 验证新配置
       ↓
2. 更新SettingLoader配置
       ↓
3. 创建新的LLM客户端
       ↓
4. 更新所有Agent实例的LLM引擎 ← BaseAgent.update_all_agents_llm_engine()
       ↓
5. 重新创建所有Services实例
       ↓
6. 返回更新结果和Agent状态
```

## 🔍 验证方法

### 1. 检查配置一致性
```python
# 获取Agent状态
status = await get_agents_status()

# 验证所有Agent都使用新模型
current_model = status['current_llm_config']['model']
for agent_name, agent_info in status['agent_instances'].items():
    assert agent_info['llm_model'] == current_model

# 验证所有Services都使用新模型  
for service_name, service_info in status['services_status'].items():
    assert service_info['llm_model'] == current_model
```

### 2. 测试实际调用
```python
# 更新配置后测试API调用
await update_config({"model": "gpt-4", "temperature": 0.1})

# 调用各个API验证是否使用新配置
reward_result = await call_reward_api(test_data)
backward_result = await call_backward_api(test_data)
# 检查返回结果中的模型信息
```

## ⚠️ 注意事项

### 1. 线程安全
- 使用`threading.Lock()`确保并发更新的安全性
- Agent实例的创建和更新都是线程安全的

### 2. 性能考虑
- 批量更新所有Agent实例，避免逐个重新创建
- Services重新创建是必要的，确保依赖关系正确

### 3. 错误处理
- 配置更新失败时，原有实例保持不变
- 提供详细的错误信息和状态反馈

### 4. 兼容性
- 保持与现有API的向后兼容性
- 新增的字段都是可选的，不影响现有客户端

## 🎯 使用场景

### 1. 模型切换
```python
# 从GPT-3.5切换到GPT-4
await update_config({
    "model": "gpt-4-turbo-preview",
    "temperature": 0.1,
    "max_completion_tokens": 4096
})
```

### 2. API提供商切换
```python
# 从OpenAI切换到DeepSeek
await update_config({
    "api_key": "deepseek_api_key", 
    "model": "deepseek-chat",
    "base_url": "https://api.deepseek.com/v1"
})
```

### 3. 参数调优
```python
# 调整温度和token限制
await update_config({
    "temperature": 0.2,
    "max_completion_tokens": 2048
})
```

## 📝 总结

这个功能实现了：

1. **配置统一性**: 确保所有Agent和Services使用相同的LLM配置
2. **操作简便性**: 一次API调用更新所有相关组件
3. **状态透明性**: 提供详细的更新状态和验证信息
4. **系统稳定性**: 线程安全的批量更新机制

通过这种方式，用户可以轻松地在运行时更新整个系统的LLM配置，而无需重启服务或手动更新各个组件。