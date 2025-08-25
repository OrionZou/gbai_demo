# 🤖 Agent Runtime Playground

一个基于 Streamlit 的前端界面，用于测试和使用 Agent Runtime API 的各项功能。

## 📋 功能概述

Agent Runtime Playground 提供了直观的 Web 界面来测试以下三个核心 API：

- **⚙️ LLM 配置管理** - 管理和更新 LLM 配置
- **🏆 Reward API** - 执行语义一致性比较测试  
- **↩️ Backward API** - 问答对聚合和知识结构化处理

## 🚀 快速开始

### 1. 环境要求

- Python 3.12
- Agent Runtime 服务已启动并运行

### 2. 安装依赖

```bash
uv venv -p 3.12.8
source .venv/bin/activate 
poetry install
```

### 3. 启动 Playground

```bash
# 方式一：使用 streamlit 直接运行
streamlit run playground/main.py

# 方式二：指定端口和配置
streamlit run playground/main.py --server.port 8501 --server.enableCORS false
```

### 4. 访问界面

打开浏览器访问：`http://localhost:8501`

## 🎯 功能详解

### ⚙️ LLM 配置管理

**主要功能**：
- 查看当前 LLM 配置状态
- 更新 LLM 配置参数
- 支持预设配置模板（DeepSeek、OpenAI等）

**使用步骤**：
1. 点击 "📥 获取当前配置" 查看现有配置
2. 在右侧选择预设模板或自定义配置
3. 填写必要参数（API Key、模型名称、Base URL等）
4. 点击 "💾 保存配置" 更新设置

**预设模板**：
- **DeepSeek Chat**: 配置 DeepSeek API
- **OpenAI GPT-4**: 配置 OpenAI API
- **自定义配置**: 手动输入配置参数

### 🏆 Reward API 测试

**主要功能**：
- 比较多个候选答案与目标答案的语义一致性
- 支持预设测试示例
- 显示详细的分析结果和历史记录

**使用步骤**：
1. 选择预设示例或输入自定义测试数据
2. 填写问题、候选答案列表和目标答案
3. 点击 "🚀 执行 Reward 测试"
4. 查看右侧的分析结果

**预设示例**：
- **简单示例 - 地理题**: 基础的单选题测试
- **复杂示例 - 阅读理解**: 复杂的语义理解测试

### ↩️ Backward API 测试

**主要功能**：
- 将问答对聚合成有意义的章节结构
- 生成辅助提示词用于知识检索
- 转换为 OSPA 格式数据
- 支持批量处理和结果导出

**使用步骤**：
1. 选择输入方式：
   - 上传 CSV 文件（包含 'q' 和 'a' 列）
   - 使用预设示例
   - 手动输入问答对
2. 配置处理指令（可选）
3. 点击 "🚀 执行 Backward 处理"
4. 查看章节聚合结果和 OSPA 数据

**CSV 文件格式**：
```csv
q,a
Python如何定义变量？,在Python中使用赋值语句定义变量
什么是函数？,函数是可重用的代码块
```

## 🔧 配置说明

### API 连接配置

在界面顶部的 "Agent Runtime API URL" 输入框中配置 API 地址：

```
默认地址: http://localhost:8011
```

也可以通过环境变量设置：

```bash
export AGENT_RUNTIME_API_URL=http://your-api-server:8011
```

### LLM 配置参数

| 参数 | 说明 | 示例 |
|------|------|------|
| API Key | LLM 服务的 API 密钥 | `sk-xxx` |
| 模型名称 | 要使用的模型 | `gpt-4`, `deepseek-chat` |
| Base URL | LLM API 的基础地址 | `https://api.openai.com/v1` |
| 超时时间 | 请求超时时间（秒） | `120.0` |
| 最大令牌数 | 最大生成令牌数 | `2048` |
| 温度 | 生成随机性控制 | `0.0` - `2.0` |

## 📊 结果解读

### Reward API 结果

返回的结果包含语义一致性分析，通常包括：
- 每个候选答案的相似度分数
- 最匹配的候选答案
- 详细的分析说明

### Backward API 结果

返回的结果包含：
- **章节信息**: 聚合后的知识章节结构
- **OSPA 数据**: 标准化的观察-状态-问题-行动数据
- **统计信息**: 处理的数据量和耗时信息

## 🛠️ 开发和调试

### 项目结构

```
playground/
├── main.py                        # Streamlit 入口文件
├── agent_runtime_playground.py    # 主要功能实现
├── README.md                      # 本说明文档
```

### 运行要求

1. **Agent Runtime 服务**: 确保 Agent Runtime API 服务正在运行
2. **网络连接**: Playground 需要能够访问 Agent Runtime API
3. **依赖包**: 安装所有必要的 Python 包

### 调试技巧

1. **API 连接问题**: 检查 API URL 是否正确，服务是否启动
2. **配置错误**: 查看错误消息，验证 LLM 配置参数
3. **数据格式**: 确保输入数据格式符合 API 要求

## 🔍 常见问题

### Q: API 连接失败怎么办？

**A**: 检查以下几点：
- Agent Runtime 服务是否正常启动
- API URL 是否正确（默认 `http://localhost:8000`）
- 网络连接是否正常
- 防火墙是否阻止了连接

### Q: LLM 配置更新失败？

**A**: 确认：
- API Key 是否有效
- 模型名称是否正确
- Base URL 是否可访问
- 参数格式是否符合要求

### Q: Reward API 测试没有结果？

**A**: 检查：
- 问题和答案是否为空
- 候选答案数量是否足够（至少2个）
- LLM 配置是否正确设置

### Q: CSV 文件上传失败？

**A**: 确保：
- CSV 文件包含 'q' 和 'a' 列
- 文件编码为 UTF-8
- 数据行不为空
- 文件大小在合理范围内

### Q: 如何导出 Backward API 的结果？

**A**: 在 Backward API 结果页面：
1. 点击 "💾 导出 OSPA 数据为 CSV"
2. 选择 "下载 CSV 文件"
3. 文件将保存为 `ospa_data_timestamp.csv`

## 📝 示例用法

### 1. 配置 DeepSeek API

```
1. 进入 "⚙️ LLM配置" 选项卡
2. 选择 "DeepSeek Chat" 模板
3. 输入你的 DeepSeek API Key
4. 点击 "💾 保存配置"
```

### 2. 测试语义一致性

```
1. 进入 "🏆 Reward API" 选项卡
2. 选择 "简单示例 - 地理题"
3. 点击 "🚀 执行 Reward 测试"
4. 查看右侧的分析结果
```

### 3. 批量处理问答对

```
1. 进入 "↩️ Backward API" 选项卡
2. 准备包含 'q' 和 'a' 列的 CSV 文件
3. 上传 CSV 文件
4. 点击 "🚀 执行 Backward 处理"
5. 导出 OSPA 数据结果
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来改进这个工具！

## 📄 许可证

此项目使用 MIT 许可证。

---

🎉 **享受使用 Agent Runtime Playground！** 如有问题请查看常见问题部分或提交 Issue。