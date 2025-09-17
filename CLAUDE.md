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

## demo
写demo，在项目根目录的./exps中进行

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

## 开发记录

在 docs/ai_dev_log 中完成，文件以 {开发内容关键词}_{年}-{月}-{日}.md 去命名
