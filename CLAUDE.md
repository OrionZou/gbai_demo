# GBAI Demo - 开发指南

本文档为AI辅助开发提供项目特定的指导原则和最佳实践。

## 🐍 Python 项目环境

### 环境管理
```bash
# 使用uv创建Python环境
uv venv -p 3.12.8

# 激活虚拟环境
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# 使用Poetry管理依赖
poetry install
```

## 📁 项目结构

### 主功能模块
- **核心代码**: `src/agent_runtime/` - 所有核心功能实现
- **前端界面**: `playground/` - Streamlit Web界面
- **测试代码**: `tests/` - 单元测试和集成测试
- **演示脚本**: `exps/` - 功能演示和验证脚本
- **批处理脚本**: `scripts/` - 自动化脚本和工具

### AI开发记录
- **路径**: `docs/ai_dev_log/`
- **命名格式**: `{功能描述}_{年}-{月}-{日}.md`
- **内容**: 记录AI辅助开发的过程、决策和实现细节

## 🏗️ 架构原则

### 1. 数据类设计
- **优先使用**: Pydantic BaseModel 构建所有数据类
- **类型注解**: 必须包含完整的类型提示
- **验证规则**: 利用Pydantic的验证功能确保数据完整性

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class ExampleData(BaseModel):
    """示例数据类"""
    id: str = Field(..., description="唯一标识符")
    name: str = Field(..., min_length=1, description="名称")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    created_at: Optional[datetime] = Field(default=None, description="创建时间")
```

### 2. Agent开发规范
- **基类继承**: 所有Agent必须继承 `BaseAgent`
- **核心方法**: 实现 `step` 抽象方法
- **职责单一**: 每个Agent专注单一功能领域
- **方法最小化**: 尽量减少Agent内部方法数量

```python
from agent_runtime.agents.base import BaseAgent
from agent_runtime.data_format.context import Context

class ExampleAgent(BaseAgent):
    """示例Agent实现"""

    async def step(self, context: Context) -> Context:
        """
        执行单步处理逻辑

        Args:
            context: 输入上下文

        Returns:
            Context: 处理后的上下文
        """
        # 实现具体逻辑
        return context
```

### 3. 服务层设计
- **异步优先**: 使用 asyncio 进行异步编程
- **错误处理**: 完善的异常处理和日志记录
- **接口统一**: 使用Pydantic模型定义输入输出

```python
from pydantic import BaseModel
from agent_runtime.data_format.message import Message
import logging

logger = logging.getLogger(__name__)

class ExampleService:
    """示例服务类"""

    async def process(self, input_data: BaseModel) -> Message:
        """
        处理业务逻辑

        Args:
            input_data: 输入数据

        Returns:
            Message: 处理结果
        """
        try:
            # 业务逻辑实现
            result = await self._internal_process(input_data)
            logger.info(f"处理完成: {result}")
            return result
        except Exception as e:
            logger.error(f"处理失败: {e}")
            raise

    async def _internal_process(self, data: BaseModel) -> Message:
        """内部处理逻辑"""
        pass
```

## 💻 开发工作流

### 1. 功能开发
1. **需求分析**: 明确功能需求和接口设计
2. **数据模型**: 设计Pydantic数据模型
3. **核心逻辑**: 实现业务逻辑和算法
4. **接口暴露**: 添加API端点或CLI命令
5. **测试验证**: 编写测试用例验证功能

### 2. 测试策略
- **单元测试**: 在 `tests/` 目录编写全面的单元测试
- **Demo测试**: 在 `exps/` 目录创建功能演示
- **清理规则**: 完成验证后删除demo文件

```python
# tests/test_example.py
import pytest
from agent_runtime.services.example_service import ExampleService

@pytest.mark.asyncio
async def test_example_service():
    """测试示例服务"""
    service = ExampleService()
    result = await service.process(input_data)
    assert result.status == "success"

# exps/demo_example.py
from agent_runtime.services.example_service import ExampleService

async def demo_example():
    """演示示例功能"""
    service = ExampleService()
    result = await service.process(test_data)
    print(f"Demo结果: {result}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(demo_example())
```

### 3. 代码质量
- **注释规范**: 简洁易懂的中文注释
- **类型提示**: 完整的类型注解
- **错误处理**: 适当的异常处理
- **日志记录**: 关键操作的日志记录

## 🔧 技术栈集成

### FastAPI集成
```python
from fastapi import FastAPI, HTTPException
from agent_runtime.services.example_service import ExampleService

app = FastAPI()

@app.post("/api/example")
async def example_endpoint(request: ExampleRequest):
    """示例API端点"""
    try:
        service = ExampleService()
        result = await service.process(request)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Streamlit集成
```python
import streamlit as st
from agent_runtime.services.example_service import ExampleService

def example_page():
    """示例Streamlit页面"""
    st.title("示例功能")

    user_input = st.text_input("输入内容")

    if st.button("处理"):
        with st.spinner("处理中..."):
            service = ExampleService()
            result = await service.process(user_input)
            st.success(f"处理结果: {result}")

if __name__ == "__main__":
    example_page()
```

## 🚫 重要约束

### 开发约束
1. **测试要求**:
   - 没有明确要求时，不构建单元测试
   - 可以构建demo进行功能验证
   - Demo验证完成后必须删除

2. **文件创建**:
   - 优先编辑现有文件
   - 避免创建不必要的新文件
   - 不主动创建文档文件

3. **依赖管理**:
   - 使用Poetry管理所有Python依赖
   - 检查现有依赖避免重复引入
   - 遵循项目既定的技术栈

### 代码规范
1. **导入顺序**:
   - 标准库导入
   - 第三方库导入
   - 本地模块导入

2. **命名规范**:
   - 类名: PascalCase
   - 函数名: snake_case
   - 常量: UPPER_CASE
   - 私有方法: _private_method

3. **文档字符串**:
   - 使用中文编写
   - 包含参数和返回值说明
   - 提供使用示例

## 🔍 调试和监控

### 日志配置
```python
import logging
from agent_runtime.logging.logger import logger

# 使用项目统一的logger
logger.info("功能执行开始")
logger.error(f"发生错误: {error_message}")
logger.debug(f"调试信息: {debug_data}")
```

### 性能监控
```python
import time
from functools import wraps

def monitor_performance(func):
    """性能监控装饰器"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        end_time = time.time()
        logger.info(f"{func.__name__} 执行时间: {end_time - start_time:.2f}秒")
        return result
    return wrapper
```

## 📋 检查清单

### 开发完成检查
- [ ] 代码符合项目架构规范
- [ ] 使用Pydantic定义数据模型
- [ ] 包含适当的错误处理
- [ ] 添加必要的日志记录
- [ ] 编写demo验证功能
- [ ] 清理临时文件和demo代码
- [ ] 更新相关文档

### 提交前检查
- [ ] 代码格式化 (`black`, `isort`)
- [ ] 类型检查 (`mypy`)
- [ ] 测试通过 (`pytest`)
- [ ] 依赖更新 (`poetry lock`)
- [ ] 文档更新

## 🚀 快速命令

### 开发命令
```bash
# 代码格式化
black src/ playground/ tests/
isort src/ playground/ tests/

# 类型检查
mypy src/

# 运行测试
pytest tests/

# 启动开发服务器
python -m uvicorn agent_runtime.main:app --reload --port 8011

# 启动前端
cd playground && streamlit run app.py
```

### 项目维护
```bash
# 更新依赖
poetry update

# 安全检查
poetry audit

# 导出依赖
poetry export -f requirements.txt --output requirements.txt
```

---

**记住**: 这些指导原则旨在确保代码质量、一致性和可维护性。在开发过程中，请始终参考此文档并遵循既定的模式和约定。