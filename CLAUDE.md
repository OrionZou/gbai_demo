# python 项目环境构建

```bash
# 使用uv创建Python环境
uv venv -p 3.12.8

# 激活虚拟环境
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate     # Windows

# 使用Poetry安装依赖
poetry install
```
使用 poetry 管理环境依赖


## 主功能文件夹
在 src/agent_runtime，src/workbook_ai是废弃的项目地址

## 前端playground在
playground/

## AI完成报告
如果有ai完成报告，放在docs/ai_done

## 数据类
优先使用pydantic 的 BaseModel模型实现

## 单元测试
在项目根目录的./tests中进行

## demo测试
在项目根目录的./exps中进行

## 批处理脚本
写在项目根目录的./scripts中


# 开发建议
1. 开发时，没有明确说写测试demo，请不要构建单元测试，但可以构建demo测试
2. 使用pydantic 构建数据类
3. 代码注释简洁易懂
4. 开发agent时，请基于BaseAgent的基类开发，step抽象方法需要实现，尽量减少agent中的方法创建

# 技术栈
- **Python**: 异步编程(asyncio)
- **Pydantic**: 数据验证和序列化
- **Streamlit**: Web界面
- **OpenAI API**: LLM调用

## Playground 开发记录

### 最新功能更新 (2025-09-15)

#### 🔧 BQA Extract 多轮对话解耦功能
新增多轮对话解耦功能，将多轮对话拆解为独立的背景-问题-答案(BQA)格式。

**相关文件:**
- `playground/pages/bqa_extract_page.py` - BQA Extract 页面
- `playground/components/forms.py` - 新增 BQAExtractTestForm 表单组件
- `playground/api_services.py` - 新增 BQAExtractService API服务
- `playground/config/examples.py` - 新增 BQA_EXTRACT_EXAMPLES 示例数据
- `playground/config/settings.py` - 配置页面路由
- `playground/app.py` - 主应用路由更新

**功能特性:**
- 支持 auto/minimal/detailed 三种背景提取模式
- 支持多会话并发处理
- 提供示例数据、手动输入、CSV上传三种输入方式
- 完整的结果展示和导出功能

**API 端点:** `/bqa/extract`

#### 🎯 Backward API 示例优化
更新了 Backward API 测试示例，增加了带已有目录和不带目录的10条数据示例。

**示例类型:**
- `有现有章节示例(10条数据)` - 容器化技术主题，包含预设章节结构
- `无现有章节示例(10条数据)` - 机器学习主题，让系统自动生成章节结构

### 开发规范提醒

1. **Playground 页面开发模式:**
   - 继承自对应的页面基类
   - 使用 ServiceManager 统一管理 API 调用
   - 表单组件放在 `components/forms.py`
   - 示例数据放在 `config/examples.py`
   - 页面配置在 `config/settings.py` 的 TAB_CONFIG

2. **API 服务集成:**
   - 新服务类继承 APIClient
   - 在 ServiceManager 中注册新服务
   - 使用统一的错误处理和超时配置

3. **数据格式约定:**
   - 问答对统一使用 `q`/`a` 或 `question`/`answer` 字段
   - 会话数据包含 `session_id` 和 `items` 字段
   - 处理结果包含 `success`、时间统计等标准字段