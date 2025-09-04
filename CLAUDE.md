# GBAI Demo 项目开发文档

## 项目概述
这是一个基于Agent架构的智能问答系统，主要功能包括：
- 多轮对话处理和章节结构生成
- OSPA (Observation-State-Prompt-Action) 数据格式支持
- 异步并发的LLM调用优化
- Streamlit交互式playground界面

## 核心架构

### 🤖 Agent系统
基于BaseAgent的多Agent协作架构：
- `CQAAgent`: Q&A到CQA格式转换
- `ChapterStructureAgent`: 章节结构生成
- `ChapterClassificationAgent`: 章节内容分类
- `GenChptPAgent`: 章节提示词生成

### 📊 数据格式
- `QAList`: 问答对列表
- `CQAList`: 上下文化问答列表  
- `ChapterStructure`: 层次化章节结构
- `OSPA`: 观察-状态-提示-行动格式

### 🔄 服务层
- `BackwardV2Service`: 主要业务逻辑服务，支持异步并发
- 异步并发优化：使用`asyncio.Semaphore`控制并发数
- 智能章节更新：只为新章节生成提示词

## 开发原则
1. 开发时，没有明确说写测试demo，请不要构建单元测试以及测试demo
2. 使用pydantic 构建数据类
3. 代码注释尽可能简洁
4. 开发agent时，请基于BaseAgent的基类开发，step抽象方法需要实现，尽量减少agent中的方法创建

## 重要功能特性

### 🚀 Backward V2 API
主要处理流程：
1. **Q&A转换**: 并发处理多个对话序列
2. **章节处理**: 
   - 无现有结构：生成新章节目录
   - 有现有结构：使用分类agent更新，只为新章节生成提示词
3. **OSPA生成**: 异步并发生成章节提示词

### 📈 性能优化
- **并发控制**: `max_concurrent_llm`参数控制并发数(默认15)
- **智能更新**: 区分新旧章节，避免重复生成
- **错误处理**: 完善的异常处理和降级机制

### 🖥️ Playground界面
位置: `playground/agent_runtime_playground.py`

主要功能：
- **多种API测试**: CQA Agent, Chapter Structure, Backward V2等
- **CSV上传支持**: 详细格式验证和错误提示
- **可视化展示**: 树形章节结构、OSPA数据预览
- **导入导出**: 章节结构JSON格式支持

### 📄 CSV格式要求
必需列名（严格区分大小写）：
- `session_id`: 对话会话ID
- `question`: 用户问题  
- `answer`: 对应答案

示例数据文件: `backward_v2_test_data.csv`

## 技术栈
- **Python**: 异步编程(asyncio)
- **Pydantic**: 数据验证和序列化
- **Streamlit**: Web界面
- **OpenAI API**: LLM调用

## 文件结构关键路径
```
src/agent_runtime/
├── agents/          # Agent实现
├── data_format/     # 数据模型定义
├── services/        # 业务逻辑服务
└── interface/       # API接口

playground/          # 交互式测试界面
backward_v2_test_data.csv  # 示例数据
```

## 开发建议

### 🔧 添加新Agent
1. 继承`BaseAgent`基类
2. 实现`step`抽象方法
3. 使用Pydantic定义输入输出格式
4. 在playground中添加测试界面

### 📊 数据格式扩展
1. 使用Pydantic BaseModel
2. 添加JSON序列化支持
3. 考虑向后兼容性

### ⚡ 性能优化
1. 使用`asyncio.gather`并发调用
2. `asyncio.Semaphore`控制并发数
3. 避免重复计算，缓存中间结果

### 🐛 调试技巧
- 使用playground测试单个组件
- 检查日志输出定位问题
- CSV格式错误时查看详细验证信息

## 最近更新 (2025年1月)
- ✅ 异步并发优化BackwardV2Service
- ✅ 智能章节更新（只处理新章节）
- ✅ 完善CSV上传验证和错误处理  
- ✅ 章节结构JSON导入导出功能
- ✅ playground界面全面增强

## 注意事项
- 确保LLM API密钥正确配置
- CSV文件使用UTF-8编码
- 章节结构最大层级限制为3层
- 并发数建议根据API限制调整