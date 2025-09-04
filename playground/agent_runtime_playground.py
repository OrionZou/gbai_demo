"""
重构后的 Agent Runtime API Playground
使用模块化架构，重点优化OSPA表格功能
"""
import os
import copy
import streamlit as st
import requests
import pandas as pd
import time
from typing import Optional

# 导入新的模块
from ospa_models import OSPAManager, OSPAItem
from api_services import ServiceManager
from ospa_utils import OSPADataLoader, OSPAProcessor, StreamlitUtils

# 页面配置
st.title("🤖 Agent Runtime API Playground")

# 全局配置
DEFAULT_API_URL = "http://localhost:8011/agent"

# 初始化会话状态
if 'ospa_manager' not in st.session_state:
    st.session_state.ospa_manager = OSPAManager()
if 'service_manager' not in st.session_state:
    st.session_state.service_manager = None
if 'processor' not in st.session_state:
    st.session_state.processor = None

# API URL 配置
api_url = st.text_input("Agent Runtime API URL",
                        value=os.getenv("AGENT_RUNTIME_API_URL",
                                        DEFAULT_API_URL),
                        key="api_url_input",
                        help="Agent Runtime API 的基础URL")

# 更新服务管理器
if (st.session_state.service_manager is None
        or st.session_state.service_manager.base_url != api_url):
    st.session_state.service_manager = ServiceManager(api_url)
    st.session_state.processor = OSPAProcessor(
        st.session_state.service_manager)

service_manager = st.session_state.service_manager
processor = st.session_state.processor

# 显示连接状态
col1, col2 = st.columns([3, 1])
with col1:
    if service_manager.check_connection():
        st.success("✅ API 连接正常")
    else:
        st.error("❌ API 连接失败，请检查 URL 或启动 Agent Runtime 服务")

with col2:
    if st.button("🔄 重新检查", help="重新检查 API 连接状态"):
        st.rerun()


def _handle_data_loading(
        data_source: str,
        current_manager: OSPAManager) -> Optional[OSPAManager]:
    """处理数据加载逻辑"""

    if data_source == "上传 CSV 文件":
        uploaded_file = st.file_uploader("选择 OSPA CSV 文件",
                                         type=['csv'],
                                         help="CSV文件应包含观察(O)和行动(A)等必要列")

        if uploaded_file is not None:
            # 生成文件的唯一标识符
            file_info = {
                'name': uploaded_file.name,
                'size': uploaded_file.size,
                'type': uploaded_file.type
            }

            # 检查是否已经处理过相同的文件
            if 'last_processed_file' not in st.session_state:
                st.session_state.last_processed_file = None

            # 判断是否是新文件或文件已变更
            is_new_file = (st.session_state.last_processed_file is None or
                           st.session_state.last_processed_file != file_info)

            if is_new_file:
                try:
                    new_manager = OSPADataLoader.load_from_csv_file(
                        uploaded_file)
                    st.success(f"✅ 成功加载 {len(new_manager.items)} 条 OSPA 数据")

                    # 记录已处理的文件信息
                    st.session_state.last_processed_file = file_info

                    # 强制刷新以确保数据正确加载
                    if "ospa_editor" in st.session_state:
                        del st.session_state["ospa_editor"]
                    return new_manager

                except Exception as e:
                    st.error(f"文件读取失败: {str(e)}")
                    return None
            else:
                # 文件已经被处理过，显示提示信息
                st.info(f"📁 文件 '{uploaded_file.name}' 已加载，"
                        f"当前有 {len(current_manager.items)} 条数据")
                return None

    elif data_source == "使用示例数据":
        # 使用示例数据
        example_files = {
            "示例1 (exp1.csv)": "ospa/exp1.csv",
            "示例2 (exp2.csv)": "ospa/exp2.csv",
            "示例3 (exp3.csv)": "ospa/exp3.csv"
        }

        selected_example = st.selectbox("选择示例文件", list(example_files.keys()))

        if st.button("📥 加载示例数据", key="load_example"):
            try:
                example_file = example_files[selected_example]
                new_manager = OSPADataLoader.load_from_example_file(
                    example_file)
                st.success(f"✅ 成功加载 {len(current_manager.items)} 条示例数据")

                # 强制刷新以确保数据正确加载
                if "ospa_editor" in st.session_state:
                    del st.session_state["ospa_editor"]

                return new_manager

            except Exception as e:
                st.error(f"示例数据加载失败: {str(e)}")
                return None

    elif data_source == "手动输入":
        if 'manual_ospa_count' not in st.session_state:
            st.session_state.manual_ospa_count = 3

        num_entries = st.number_input("OSPA 条目数量",
                                      min_value=1,
                                      max_value=20,
                                      value=st.session_state.manual_ospa_count,
                                      key="manual_ospa_num")

        if num_entries != st.session_state.manual_ospa_count:
            st.session_state.manual_ospa_count = num_entries
            st.rerun()

        with st.form("manual_ospa_form"):
            manual_items = []
            for i in range(num_entries):
                st.write(f"**OSPA 条目 {i+1}**")
                o = st.text_area(f"O (观察/用户输入)", key=f"manual_o_{i}")
                a = st.text_area(f"A (Agent输出)", key=f"manual_a_{i}")

                if o.strip() and a.strip():
                    manual_items.append(
                        OSPAItem(no=i + 1, O=o.strip(), A=a.strip()))

            if st.form_submit_button("💾 保存手动输入的数据", type="primary"):
                current_manager.items = manual_items
                st.success(f"✅ 成功保存 {len(manual_items)} 条 OSPA 数据")

                # 强制刷新以确保数据正确加载
                if "ospa_editor" in st.session_state:
                    del st.session_state["ospa_editor"]

                return current_manager

    return None


# 创建选项卡
tabs = st.tabs(["⚙️ LLM配置", "🏆 Reward API", "↩️ Backward API", "↩️ Backward V2 API", "📊 OSPA 表格", "🤖 Agent管理"])

# ==================== LLM 配置页面 ====================
with tabs[0]:
    st.header("🔧 LLM 配置管理")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📋 当前配置")

        if st.button("📥 获取当前配置", key="get_config"):
            try:
                config = service_manager.config_service.get_config()
                st.session_state.current_config = config
                st.success("配置获取成功！")
                st.json(config)
            except Exception as e:
                st.error(f"获取配置失败: {str(e)}")

        # 显示已保存的配置
        if 'current_config' in st.session_state:
            st.json(st.session_state.current_config)

    with col2:
        st.subheader("⚙️ 更新配置")

        # 预设配置模板
        templates = {
            "DeepSeek Chat": {
                "api_key": "your_deepseek_api_key",
                "model": "deepseek-chat",
                "base_url": "https://api.deepseek.com/v1",
                "timeout": 180.0,
                "max_completion_tokens": 2048,
                "temperature": 0.0
            },
            "OpenAI GPT-4": {
                "api_key": "your_openai_api_key",
                "model": "gpt-4",
                "base_url": "https://api.openai.com/v1",
                "timeout": 120.0,
                "max_completion_tokens": 4096,
                "temperature": 0.0
            },
            "自定义配置": {}
        }

        template_choice = st.selectbox("选择配置模板", list(templates.keys()))
        template = templates[template_choice]

        # 配置表单
        with st.form("config_form"):
            api_key = st.text_input("API Key",
                                    value=template.get("api_key", ""),
                                    type="password")
            model = st.text_input("模型名称", value=template.get("model", ""))
            base_url = st.text_input("Base URL",
                                     value=template.get("base_url", ""))
            timeout = st.number_input("超时时间 (秒)",
                                      value=template.get("timeout", 120.0),
                                      min_value=1.0)
            max_tokens = st.number_input("最大令牌数",
                                         value=template.get(
                                             "max_completion_tokens", 2048),
                                         min_value=1)
            temperature = st.number_input("温度",
                                          value=template.get(
                                              "temperature", 0.0),
                                          min_value=0.0,
                                          max_value=2.0,
                                          step=0.1)

            if st.form_submit_button("💾 保存配置", type="primary"):
                config_data = {
                    "api_key": api_key,
                    "model": model,
                    "base_url": base_url,
                    "timeout": timeout,
                    "max_completion_tokens": max_tokens,
                    "temperature": temperature
                }

                try:
                    result = service_manager.config_service.update_config(
                        config_data)
                    st.success("✅ 配置更新成功！")
                    st.json(result)
                    # 更新会话状态
                    st.session_state.current_config = result.get(
                        "config", config_data)
                except Exception as e:
                    st.error(f"配置更新失败: {str(e)}")

# ==================== Reward API 页面 ====================
with tabs[1]:
    st.header("🏆 Reward API 测试")

    st.markdown("**功能说明**: 比较多个候选答案与目标答案的语义一致性")

    col1, col2 = st.columns([2, 1])

    with col1:
        # 预设示例
        examples = {
            "自定义输入": {},
            "简单示例 - 地理题": {
                "question": "世界上最大的海洋是哪个？",
                "candidates": ["大西洋", "太平洋", "印度洋", "北冰洋", "地中海"],
                "target_answer": "太平洋"
            },
            "复杂示例 - 阅读理解": {
                "question":
                "请总结《西游记》中唐僧西天取经的目的。",
                "candidates": [
                    "唐僧带领孙悟空、猪八戒、沙僧历经九九八十一难前往西天取经，为了取得真经。",
                    "唐僧此行是因为皇帝派遣他寻找宝物。", "取经的最终目的，是为了获取佛经，弘扬佛法，普度众生。",
                    "唐僧和徒弟们一路降妖除魔，实际上是为了打败妖怪获得宝藏。", "这个故事主要讲述了团队合作、修行和坚持不懈的精神。"
                ],
                "target_answer":
                "唐僧此次取经的真正目的，是为了弘扬佛法，普度众生。"
            }
        }

        example_choice = st.selectbox("选择测试示例",
                                      list(examples.keys()),
                                      key="reward_example")
        example = examples[example_choice]

        # 输入表单
        question = st.text_area("问题",
                                value=example.get("question", ""),
                                help="需要进行语义比较的问题")

        target_answer = st.text_area("目标答案",
                                     value=example.get("target_answer", ""),
                                     help="用于比较的标准答案")

        # 候选答案输入
        st.subheader("候选答案")
        candidates = []

        # 如果有示例，使用示例数据
        if example.get("candidates"):
            candidates = example["candidates"]
            for i, candidate in enumerate(candidates):
                st.text_area(f"候选答案 {i+1}",
                             value=candidate,
                             disabled=True,
                             key=f"candidate_{i}")
        else:
            # 动态添加候选答案
            if 'num_candidates' not in st.session_state:
                st.session_state.num_candidates = 1

            col_a, col_b = st.columns([1, 4])
            with col_a:
                num_candidates = st.number_input(
                    "候选答案数量",
                    min_value=1,
                    max_value=10,
                    value=st.session_state.num_candidates)
                if num_candidates != st.session_state.num_candidates:
                    st.session_state.num_candidates = num_candidates
                    st.rerun()

            for i in range(num_candidates):
                candidate = st.text_area(f"候选答案 {i+1}",
                                         key=f"custom_candidate_{i}")
                if candidate.strip():
                    candidates.append(candidate.strip())

        # 提交测试
        if st.button("🚀 执行 Reward 测试", type="primary", key="run_reward"):
            if not question.strip():
                st.error("请输入问题")
            elif len(candidates) < 1:
                st.error("请至少输入1个候选答案")
            elif not target_answer.strip():
                st.error("请输入目标答案")
            else:
                test_data = {
                    "question": question,
                    "candidates": candidates,
                    "target_answer": target_answer
                }

                try:
                    with st.spinner("正在执行语义一致性分析..."):
                        response = requests.post(f"{api_url}/reward",
                                                 json=test_data)

                    if response.status_code == 200:
                        result = response.json()
                        st.success("✅ 测试完成！")

                        # 保存到会话状态供右侧显示
                        if 'reward_results' not in st.session_state:
                            st.session_state.reward_results = []
                        st.session_state.reward_results.append({
                            "timestamp":
                            time.strftime("%Y-%m-%d %H:%M:%S"),
                            "question":
                            question,
                            "result":
                            result
                        })
                    else:
                        st.error(
                            f"测试失败: {response.status_code} - {response.text}")
                except Exception as e:
                    st.error(f"请求失败: {e}")

    with col2:
        st.subheader("📊 测试结果")

        if 'reward_results' in st.session_state and st.session_state.reward_results:
            # 显示最新结果
            latest_result = st.session_state.reward_results[-1]
            st.write(f"**最新测试时间**: {latest_result['timestamp']}")
            st.write(f"**问题**: {latest_result['question'][:50]}...")

            with st.expander("查看详细结果", expanded=True):
                st.json(latest_result['result'])

            # 历史记录
            if len(st.session_state.reward_results) > 1:
                with st.expander(
                        f"历史记录 ({len(st.session_state.reward_results)-1} 条)"):
                    for i, result in enumerate(
                            reversed(st.session_state.reward_results[:-1])):
                        st.write(f"**{i+1}.** {result['timestamp']}")
                        st.write(f"问题: {result['question'][:30]}...")
                        if st.button(
                                f"查看",
                                key=
                                f"view_result_{len(st.session_state.reward_results)-i-2}"
                        ):
                            st.json(result['result'])

            if st.button("🗑️ 清空历史", key="clear_reward_history"):
                st.session_state.reward_results = []
                st.rerun()
        else:
            st.info("暂无测试结果")

# ==================== Backward API 页面 ====================
with tabs[2]:
    st.header("↩️ Backward API 测试")

    st.markdown("**功能说明**: 将问答对聚合成有意义的章节结构，并生成辅助提示词")

    # 预设示例
    backward_examples = {
        "自定义输入": {
            "qas": [],
            "chapters_extra_instructions": "",
            "gen_p_extra_instructions": ""
        },
        "简单示例 - Python基础": {
            "qas": [{
                "q": "Python如何定义变量？",
                "a": "在Python中使用赋值语句定义变量，如 x = 10"
            }, {
                "q": "Python如何定义函数？",
                "a": "使用def关键字定义函数，如 def func_name():"
            }, {
                "q": "什么是Python列表？",
                "a": "列表是Python中的可变序列，使用[]定义"
            }],
            "chapters_extra_instructions":
            "请将Python相关的问题聚合到一个章节",
            "gen_p_extra_instructions":
            "生成专业的Python技术文档风格提示词"
        }
    }

    col1, col2 = st.columns([3, 2])

    with col1:
        backward_example_choice = st.selectbox("选择测试示例",
                                               list(backward_examples.keys()),
                                               key="backward_example")
        backward_example = backward_examples[backward_example_choice]

        st.subheader("📝 问答对输入")

        # CSV 文件上传
        uploaded_file = st.file_uploader("上传CSV文件 (可选)",
                                         type=['csv'],
                                         help="CSV文件应包含 'q' 和 'a' 列")

        qas = []

        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file)
                if 'q' in df.columns and 'a' in df.columns:
                    qas = [{
                        "q": row['q'],
                        "a": row['a']
                    } for _, row in df.iterrows()
                           if pd.notna(row['q']) and pd.notna(row['a'])]
                    st.success(f"✅ 成功从CSV加载 {len(qas)} 个问答对")
                    st.dataframe(df[['q', 'a']].head(10))
                else:
                    st.error("CSV文件必须包含 'q' 和 'a' 列")
            except Exception as e:
                st.error(f"CSV文件读取失败: {e}")

        # 如果没有上传文件，使用示例或手动输入
        if not qas:
            if backward_example.get("qas"):
                qas = backward_example["qas"]
                st.info(f"使用示例数据: {len(qas)} 个问答对")
                # 显示示例数据
                for i, qa in enumerate(qas[:5]):  # 只显示前5个
                    with st.expander(f"问答对 {i+1}"):
                        st.write(f"**问题**: {qa['q']}")
                        st.write(f"**答案**: {qa['a']}")
                if len(qas) > 5:
                    st.write(f"... 还有 {len(qas)-5} 个问答对")
            else:
                # 手动输入
                if 'num_qas' not in st.session_state:
                    st.session_state.num_qas = 3

                num_qas = st.number_input("问答对数量",
                                          min_value=1,
                                          max_value=20,
                                          value=st.session_state.num_qas)
                if num_qas != st.session_state.num_qas:
                    st.session_state.num_qas = num_qas
                    st.rerun()

                for i in range(num_qas):
                    with st.expander(f"问答对 {i+1}"):
                        q = st.text_area(f"问题 {i+1}", key=f"q_{i}")
                        a = st.text_area(f"答案 {i+1}", key=f"a_{i}")
                        if q.strip() and a.strip():
                            qas.append({"q": q.strip(), "a": a.strip()})

        # 额外指令
        st.subheader("🎯 处理指令")
        chapters_extra_instructions = st.text_area(
            "1. 章节聚合额外指令(选填)",
            value=backward_example.get("chapters_extra_instructions", ""),
            help="指导如何聚合问答对到章节的额外说明")

        gen_p_extra_instructions = st.text_area("2. 提示词生成额外指令(选填)",
                                                value=backward_example.get(
                                                    "gen_p_extra_instructions",
                                                    ""),
                                                help="指导如何生成提示词的额外说明")

        # 提交测试
        if st.button("🚀 执行 Backward 处理", type="primary", key="run_backward"):
            if not qas:
                st.error("请输入至少一个问答对")
            else:
                try:
                    with st.spinner("正在执行问答对聚合处理..."):
                        result = service_manager.backward_service.process_qas(
                            qas, chapters_extra_instructions,
                            gen_p_extra_instructions)

                    st.success("✅ 处理完成！")
                    # 保存结果
                    st.session_state.backward_result = result

                except Exception as e:
                    st.error(f"处理失败: {str(e)}")

    with col2:
        st.subheader("📊 处理结果")

        if 'backward_result' in st.session_state:
            result = st.session_state.backward_result

            # 基本统计信息
            st.metric("处理状态", "✅ 成功" if result.get("success") else "❌ 失败")

            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("章节数", result.get("total_chapters", 0))
            with col_b:
                st.metric("问答对数", result.get("total_qas", 0))
            with col_c:
                st.metric("OSPA条目", result.get("total_ospa", 0))

            # 处理时间
            processing_time = result.get("processing_time_ms", 0)
            st.write(f"**处理耗时**: {processing_time} ms")

            # 处理消息
            if result.get("message"):
                st.info(result["message"])

            # 完整结果查看
            with st.expander("🔍 查看完整结果 JSON"):
                st.json(result)

            # 导出功能
            if st.button("💾 导出 OSPA 数据为 CSV"):
                if result.get("ospa"):
                    ospa_df = pd.DataFrame(result["ospa"])
                    csv = ospa_df.to_csv(index=False)
                    st.download_button(
                        label="下载 CSV 文件",
                        data=csv,
                        file_name=f"ospa_data_{int(time.time())}.csv",
                        mime="text/csv")
        else:
            st.info("暂无处理结果")

# ==================== Backward V2 API 页面 ====================
with tabs[3]:
    st.header("↩️ Backward V2 API 测试")

    st.markdown("**功能说明**: 改进版知识反向处理，支持多轮对话和现有章节目录更新")

    # 预设示例
    backward_v2_examples = {
        "自定义输入": {
            "qa_lists": [],
            "chapter_structure": None,
            "max_level": 3
        },
        "简单示例 - 无现有章节": {
            "qa_lists": [
                {
                    "items": [
                        {"question": "Python如何定义变量？", "answer": "在Python中使用赋值语句定义变量，如 x = 10"},
                        {"question": "如何查看变量类型？", "answer": "使用type()函数可以查看变量类型，如 type(x)"}
                    ],
                    "session_id": "session_1"
                },
                {
                    "items": [
                        {"question": "什么是RESTful API？", "answer": "RESTful API是遵循REST架构风格的Web服务接口"},
                        {"question": "API设计有什么原则？", "answer": "API设计要遵循统一接口、无状态、可缓存等原则"}
                    ],
                    "session_id": "session_2"
                }
            ],
            "chapter_structure": None,
            "max_level": 3
        },
        "复杂示例 - 3个多轮对话": {
            "qa_lists": [
                {
                    "items": [
                        {"question": "什么是机器学习？", "answer": "机器学习是人工智能的一个分支，让计算机通过数据学习并做出预测或决策，而无需明确编程。"},
                        {"question": "机器学习有哪些主要类型？", "answer": "主要有监督学习、无监督学习和强化学习三种类型。监督学习使用标记数据，无监督学习寻找数据中的模式，强化学习通过奖励机制学习。"},
                        {"question": "什么是神经网络？", "answer": "神经网络是模仿人类大脑神经元结构的计算模型，由多层相互连接的节点组成，能够学习复杂的数据模式。"},
                        {"question": "深度学习和机器学习有什么区别？", "answer": "深度学习是机器学习的一个子集，使用深度神经网络（多隐藏层）来学习数据的层次化表示，在图像、语音等领域表现出色。"},
                        {"question": "常用的机器学习算法有哪些？", "answer": "常用算法包括线性回归、逻辑回归、决策树、随机森林、支持向量机、K-means聚类、朴素贝叶斯等。"},
                        {"question": "如何评估机器学习模型的性能？", "answer": "可以使用准确率、精确率、召回率、F1分数、AUC-ROC曲线等指标。对于回归问题，常用MSE、MAE、R²等指标。"},
                        {"question": "什么是过拟合和欠拟合？", "answer": "过拟合是模型在训练数据上表现很好但在新数据上表现差；欠拟合是模型过于简单，无法捕获数据的潜在模式。可以通过正则化、交叉验证等方法解决。"},
                        {"question": "机器学习在实际中有哪些应用？", "answer": "广泛应用于推荐系统、图像识别、自然语言处理、金融风控、医疗诊断、自动驾驶、语音识别等领域。"}
                    ],
                    "session_id": "ml_conversation"
                },
                {
                    "items": [
                        {"question": "什么是RESTful API？", "answer": "REST（Representational State Transfer）是一种架构风格，RESTful API是遵循REST原则设计的Web服务接口，使用HTTP方法进行资源操作。"},
                        {"question": "REST的主要原则有哪些？", "answer": "主要原则包括：无状态性、统一接口、客户端-服务器架构、可缓存性、分层系统和按需代码（可选）。"},
                        {"question": "HTTP方法在RESTful API中如何使用？", "answer": "GET用于获取资源，POST用于创建资源，PUT用于更新整个资源，PATCH用于部分更新，DELETE用于删除资源。"},
                        {"question": "什么是API版本控制？为什么重要？", "answer": "API版本控制是管理API变更的方法，确保向后兼容性。重要性在于保护现有客户端不受新版本影响。常见方式有URL路径版本、请求头版本等。"},
                        {"question": "API文档应该包含哪些内容？", "answer": "应包含端点描述、请求/响应格式、参数说明、状态码说明、认证方式、使用示例、错误处理等信息。"},
                        {"question": "如何设计API的错误处理？", "answer": "使用标准HTTP状态码，提供清晰的错误消息，包含错误代码和详细描述，保持错误格式一致性，避免暴露敏感信息。"},
                        {"question": "API安全有哪些最佳实践？", "answer": "使用HTTPS、实施身份认证和授权、API密钥管理、输入验证、速率限制、CORS配置、安全响应头等。"},
                        {"question": "什么是API网关？有什么作用？", "answer": "API网关是微服务架构中的入口点，提供路由、认证、限流、监控、协议转换等功能，简化客户端与后端服务的交互。"},
                        {"question": "如何进行API性能优化？", "answer": "可以通过缓存策略、分页处理、异步处理、数据库优化、CDN使用、响应压缩、连接池等方式提升API性能。"}
                    ],
                    "session_id": "api_design_conversation"
                },
                {
                    "items": [
                        {"question": "什么是Docker？它解决了什么问题？", "answer": "Docker是容器化平台，解决了\"在我机器上能运行\"的环境一致性问题，提供轻量级虚拟化，简化应用部署和迁移。"},
                        {"question": "Docker容器和虚拟机有什么区别？", "answer": "容器共享宿主机内核，启动快、资源占用少；虚拟机有完整操作系统，隔离性更强但资源消耗大。容器更适合微服务架构。"},
                        {"question": "Dockerfile的作用是什么？", "answer": "Dockerfile是构建Docker镜像的脚本文件，包含一系列指令来定义镜像的构建过程，如基础镜像、依赖安装、文件复制等。"},
                        {"question": "什么是Docker Compose？", "answer": "Docker Compose是用于定义和运行多容器Docker应用的工具，通过YAML文件配置多个服务，简化复杂应用的管理和部署。"},
                        {"question": "Docker网络模式有哪些？", "answer": "主要有bridge（默认）、host、none、overlay等模式。bridge模式为容器创建独立网络，host模式共享宿主机网络，overlay用于跨主机通信。"},
                        {"question": "如何管理Docker数据持久化？", "answer": "可以使用数据卷（volumes）、绑定挂载（bind mounts）或临时文件系统（tmpfs）。数据卷是推荐方式，由Docker管理且持久化。"},
                        {"question": "什么是容器编排？Kubernetes的作用是什么？", "answer": "容器编排是管理多个容器的部署、扩展和运行的过程。Kubernetes是容器编排平台，提供自动部署、扩缩容、服务发现、负载均衡等功能。"},
                        {"question": "Docker镜像的分层机制是如何工作的？", "answer": "Docker镜像由多个只读层组成，每层包含文件系统的变更。容器运行时添加可写层。分层机制实现了镜像复用和高效存储。"},
                        {"question": "如何优化Docker镜像大小？", "answer": "使用轻量级基础镜像（如Alpine）、合并RUN命令、清理缓存、使用.dockerignore文件、多阶段构建等方法可以显著减小镜像大小。"},
                        {"question": "容器化微服务架构有什么优势和挑战？", "answer": "优势：服务独立部署、技术栈灵活、水平扩展容易。挑战：服务间通信复杂、数据一致性、监控难度增加、网络性能开销。"}
                    ],
                    "session_id": "docker_conversation"
                }
            ],
            "chapter_structure": None,
            "max_level": 3
        },
        "有现有章节示例": {
            "qa_lists": [
                {
                    "items": [
                        {"question": "什么是Docker容器？", "answer": "Docker容器是轻量级的虚拟化技术"},
                        {"question": "容器与虚拟机的区别？", "answer": "容器共享宿主机内核，虚拟机有独立的操作系统"}
                    ],
                    "session_id": "session_3"
                }
            ],
            "chapter_structure": {
                "nodes": {
                    "chapter_1": {
                        "id": "chapter_1",
                        "title": "基础知识",
                        "level": 1,
                        "parent_id": None,
                        "children": [],
                        "description": "基础技术概念",
                        "related_cqa_items": [],
                        "related_cqa_ids": [],
                        "chapter_number": "1."
                    }
                },
                "root_ids": ["chapter_1"],
                "max_level": 3
            },
            "max_level": 3
        }
    }

    col1, col2 = st.columns([3, 2])

    with col1:
        backward_v2_example_choice = st.selectbox("选择测试示例",
                                                  list(backward_v2_examples.keys()),
                                                  key="backward_v2_example")
        backward_v2_example = backward_v2_examples[backward_v2_example_choice]

        st.subheader("📝 多轮对话输入 (Q&A 二维列表)")

        # CSV 文件上传
        st.write("**📊 CSV格式要求:**")
        with st.expander("📋 查看详细的CSV格式要求", expanded=False):
            st.markdown("""
            **必需的列名 (严格区分大小写):**
            - `session_id` - 对话会话ID，用于区分不同的多轮对话
            - `question` - 用户问题
            - `answer` - 对应答案
            
            **CSV格式规范:**
            1. **文件编码**: 推荐使用 UTF-8 编码
            2. **分隔符**: 使用逗号 (,) 作为字段分隔符
            3. **引号**: 如果内容包含逗号或换行，请使用双引号包围
            4. **多轮对话**: 同一个 session_id 的多行记录会被归为一个多轮对话序列
            5. **数据顺序**: 建议按 session_id 和对话顺序排序
            
            **示例CSV内容:**
            ```csv
            session_id,question,answer
            ai_ml_conversation,什么是人工智能？,"人工智能是模拟人的智能的技术科学"
            ai_ml_conversation,机器学习和AI什么关系？,"机器学习是AI的一个重要分支"
            web_dev_conversation,什么是前端开发？,"前端开发是创建用户界面的过程"
            web_dev_conversation,HTML和CSS有什么区别？,"HTML负责结构，CSS负责样式"
            ```
            
            **质量建议:**
            - 每个对话序列建议包含 3-10 轮问答
            - 问答内容应该相关联，形成有逻辑的对话流程
            - 答案应该详细且准确，便于生成高质量的章节提示词
            - 避免空值或格式错误的数据
            """)
        
        # 提供示例CSV下载
        col1, col_ = st.columns([3, 1])
        
        with col1:
            uploaded_file = st.file_uploader("上传CSV文件 (可选)",
                                             type=['csv'],
                                             help="请确保CSV包含必需的列: session_id, question, answer",
                                             key="backward_v2_csv")
        
        with col_:
            # 从项目根目录读取示例CSV数据
            example_csv_path = "exps/data/backward_v2_test_data.csv"
            try:
                with open(example_csv_path, 'r', encoding='utf-8') as f:
                    example_csv_data = f.read()
                    
                st.download_button(
                    label="📥 下载示例CSV",
                    data=example_csv_data,
                    file_name="backward_v2_example.csv",
                    mime="text/csv",
                    help="下载标准格式的CSV示例文件（包含完整的多轮对话数据）"
                )
            except FileNotFoundError:
                st.error("❌ 示例CSV文件未找到")
                # 提供一个简化的备用示例
                fallback_csv = """session_id,question,answer
ai_conversation,什么是人工智能？,"人工智能(AI)是模拟人的智能的技术科学"
ai_conversation,机器学习是什么？,"机器学习是AI的一个重要分支"
web_conversation,什么是前端开发？,"前端开发是创建用户界面的过程"
web_conversation,什么是API？,"API是应用程序接口的缩写" """
                
                st.download_button(
                    label="📥 下载备用示例CSV",
                    data=fallback_csv,
                    file_name="backup_example.csv",
                    mime="text/csv",
                    help="备用的简化示例文件"
                )

        qa_lists = []

        if uploaded_file is not None:
            try:
                # 检查文件大小
                file_size = uploaded_file.size
                if file_size > 10 * 1024 * 1024:  # 10MB限制
                    st.error("❌ CSV文件过大，请上传小于10MB的文件")
                elif file_size == 0:
                    st.error("❌ 上传的文件为空")
                else:
                    df = pd.read_csv(uploaded_file)
                    
                    # 详细的格式验证
                    required_cols = ['session_id', 'question', 'answer']
                    missing_cols = [col for col in required_cols if col not in df.columns]
                    
                    if missing_cols:
                        st.error(f"❌ CSV文件缺少必需的列: {', '.join(missing_cols)}")
                        st.write("**现有列:**", list(df.columns))
                        st.info("💡 请检查列名是否正确（区分大小写）")
                    elif len(df) == 0:
                        st.error("❌ CSV文件没有数据行")
                    else:
                        # 数据质量检查
                        total_rows = len(df)
                        valid_rows = 0
                        empty_questions = 0
                        empty_answers = 0
                        empty_sessions = 0
                        
                        # 按session_id分组
                        sessions = {}
                        for _, row in df.iterrows():
                            session_empty = pd.isna(row['session_id']) or str(row['session_id']).strip() == ''
                            question_empty = pd.isna(row['question']) or str(row['question']).strip() == ''
                            answer_empty = pd.isna(row['answer']) or str(row['answer']).strip() == ''
                            
                            if session_empty:
                                empty_sessions += 1
                            if question_empty:
                                empty_questions += 1
                            if answer_empty:
                                empty_answers += 1
                                
                            if not (session_empty or question_empty or answer_empty):
                                valid_rows += 1
                                session_id = str(row['session_id']).strip()
                                if session_id not in sessions:
                                    sessions[session_id] = []
                                sessions[session_id].append({
                                    "question": str(row['question']).strip(),
                                    "answer": str(row['answer']).strip()
                                })
                        
                        # 显示数据质量报告
                        if valid_rows == 0:
                            st.error("❌ 没有找到有效的数据行")
                            st.write(f"**数据质量问题:**")
                            if empty_sessions > 0:
                                st.write(f"- 空的session_id: {empty_sessions}行")
                            if empty_questions > 0:
                                st.write(f"- 空的question: {empty_questions}行")
                            if empty_answers > 0:
                                st.write(f"- 空的answer: {empty_answers}行")
                        else:
                            # 转换为qa_lists格式
                            qa_lists = [
                                {
                                    "items": items,
                                    "session_id": session_id
                                }
                                for session_id, items in sessions.items()
                                if len(items) > 0  # 只包含非空的会话
                            ]
                            
                            st.success(f"✅ 成功从CSV加载 {len(qa_lists)} 个对话序列，共 {valid_rows} 个有效问答对")
                            
                            # 数据质量提示
                            skipped_rows = total_rows - valid_rows
                            if skipped_rows > 0:
                                st.warning(f"⚠️ 跳过了 {skipped_rows} 行无效数据（空值或格式错误）")
                            
                            # 会话质量检查
                            short_sessions = [session_id for session_id, items in sessions.items() if len(items) < 2]
                            if short_sessions:
                                st.info(f"💡 发现 {len(short_sessions)} 个单轮对话会话，建议多轮对话效果更佳")
                            
                            # 显示前几个序列的预览
                            st.write("**📋 数据预览:**")
                            for i, qa_list in enumerate(qa_lists[:3]):
                                st.write(f"**对话序列 {i+1} (session: {qa_list['session_id']})**: {len(qa_list['items'])} 个问答对")
                                # 显示第一个问答对
                                if qa_list['items']:
                                    first_qa = qa_list['items'][0]
                                    question_preview = first_qa['question'][:50] + "..." if len(first_qa['question']) > 50 else first_qa['question']
                                    st.write(f"  └─ Q: {question_preview}")
                            
                            if len(qa_lists) > 3:
                                st.write(f"... 还有 {len(qa_lists)-3} 个对话序列")
                        
            except pd.errors.EmptyDataError:
                st.error("❌ CSV文件为空或格式错误")
            except pd.errors.ParserError as e:
                st.error(f"❌ CSV格式解析错误: {str(e)}")
                st.info("💡 请检查CSV文件格式，确保使用逗号分隔，引号正确闭合")
            except UnicodeDecodeError:
                st.error("❌ 文件编码错误，请使用UTF-8编码保存CSV文件")
            except Exception as e:
                st.error(f"❌ CSV文件处理失败: {str(e)}")
                st.info("💡 请检查文件格式是否符合要求")

        # 如果没有上传文件，使用示例或手动输入
        if not qa_lists:
            if backward_v2_example.get("qa_lists"):
                qa_lists = backward_v2_example["qa_lists"]
                st.info(f"使用示例数据: {len(qa_lists)} 个对话序列")
                # 显示示例数据
                for i, qa_list in enumerate(qa_lists):
                    with st.expander(f"对话序列 {i+1} (session: {qa_list['session_id']})"):
                        for j, qa in enumerate(qa_list['items'][:3]):  # 只显示前3个
                            st.write(f"**Q{j+1}**: {qa['question']}")
                            st.write(f"**A{j+1}**: {qa['answer']}")
                        if len(qa_list['items']) > 3:
                            st.write(f"... 还有 {len(qa_list['items'])-3} 个问答对")
            else:
                # 手动输入多轮对话
                if 'num_sessions' not in st.session_state:
                    st.session_state.num_sessions = 2
                
                num_sessions = st.number_input("对话序列数量",
                                               min_value=1,
                                               max_value=10,
                                               value=st.session_state.num_sessions,
                                               key="backward_v2_sessions")
                if num_sessions != st.session_state.num_sessions:
                    st.session_state.num_sessions = num_sessions
                    st.rerun()

                for session_idx in range(num_sessions):
                    with st.expander(f"对话序列 {session_idx+1}", expanded=session_idx < 2):
                        session_id = st.text_input(f"会话ID", 
                                                   value=f"session_{session_idx+1}",
                                                   key=f"session_id_{session_idx}")
                        
                        if f'num_qas_{session_idx}' not in st.session_state:
                            st.session_state[f'num_qas_{session_idx}'] = 2
                        
                        num_qas = st.number_input(f"问答对数量",
                                                  min_value=1,
                                                  max_value=20,
                                                  value=st.session_state[f'num_qas_{session_idx}'],
                                                  key=f"num_qas_{session_idx}")
                        
                        session_items = []
                        for qa_idx in range(num_qas):
                            q = st.text_area(f"问题 {qa_idx+1}", key=f"q_{session_idx}_{qa_idx}")
                            a = st.text_area(f"答案 {qa_idx+1}", key=f"a_{session_idx}_{qa_idx}")
                            if q.strip() and a.strip():
                                session_items.append({"question": q.strip(), "answer": a.strip()})
                        
                        if session_items:
                            qa_lists.append({
                                "items": session_items,
                                "session_id": session_id
                            })

        # 现有章节目录输入
        st.subheader("🗂️ 现有章节目录 (可选)")
        
        use_existing_chapter = st.checkbox("使用现有章节目录", 
                                           value=backward_v2_example.get("chapter_structure") is not None)
        
        chapter_structure = None
        if use_existing_chapter:
            # 章节目录输入方式选择
            chapter_input_method = st.radio(
                "章节目录输入方式",
                ["使用示例数据", "上传JSON文件", "从历史结果导入", "手动编辑JSON"],
                key="chapter_input_method",
                horizontal=True
            )
            
            if chapter_input_method == "使用示例数据":
                if backward_v2_example.get("chapter_structure"):
                    st.success("✅ 使用示例章节目录")
                    chapter_structure = backward_v2_example["chapter_structure"]
                    
                    # 显示章节结构预览
                    with st.expander("📋 示例章节结构预览"):
                        st.json(chapter_structure)
                else:
                    st.info("当前示例无章节目录数据")
            
            elif chapter_input_method == "上传JSON文件":
                uploaded_structure_file = st.file_uploader(
                    "上传章节结构JSON文件",
                    type=['json'],
                    help="上传之前导出的章节结构JSON文件",
                    key="upload_chapter_structure"
                )
                
                if uploaded_structure_file is not None:
                    try:
                        structure_content = uploaded_structure_file.read().decode('utf-8')
                        
                        # 尝试使用新的ChapterStructure.from_json_string方法
                        try:
                            from src.agent_runtime.data_format.chapter_format import ChapterStructure
                            imported_structure_obj = ChapterStructure.from_json_string(structure_content)
                            
                            # 转换为字典格式用于API调用
                            chapter_structure = {
                                "nodes": {},
                                "root_ids": imported_structure_obj.root_ids,
                                "max_level": imported_structure_obj.max_level
                            }
                            
                            # 转换节点数据
                            for node_id, node in imported_structure_obj.nodes.items():
                                chapter_structure["nodes"][node_id] = {
                                    "id": node.id,
                                    "title": node.title,
                                    "level": node.level,
                                    "parent_id": node.parent_id,
                                    "children": node.children,
                                    "description": node.description,
                                    "content": node.content,
                                    "related_cqa_items": [
                                        {
                                            "cqa_id": cqa.cqa_id,
                                            "question": cqa.question,
                                            "answer": cqa.answer,
                                            "context": cqa.context
                                        } for cqa in node.related_cqa_items
                                    ],
                                    "related_cqa_ids": node.related_cqa_ids,
                                    "chapter_number": node.chapter_number
                                }
                            
                            nodes_count = len(chapter_structure["nodes"])
                            total_content_chars = sum(
                                len(node.get("content", "")) 
                                for node in chapter_structure["nodes"].values()
                            )
                            
                            st.success(f"✅ 成功导入完整章节结构，包含 {nodes_count} 个章节")
                            if total_content_chars > 0:
                                st.info(f"📝 包含 {total_content_chars} 字符的章节内容（提示词等）")
                            
                            # 显示结构概览
                            st.write("**📊 结构概览:**")
                            st.write(imported_structure_obj.get_summary())
                            
                            with st.expander("📋 导入的章节结构预览"):
                                st.write(imported_structure_obj.structure_str(show_cqa_info=False))
                                
                        except Exception as new_format_error:
                            # 降级到原来的JSON解析方法
                            import json
                            imported_structure = json.loads(structure_content)
                            
                            # 验证基本结构
                            if isinstance(imported_structure, dict) and "nodes" in imported_structure:
                                chapter_structure = imported_structure
                                nodes_count = len(imported_structure.get("nodes", {}))
                                st.success(f"✅ 成功导入章节结构，包含 {nodes_count} 个章节")
                                st.info("💡 导入的是简化格式的章节结构")
                                
                                with st.expander("📋 导入的章节结构预览"):
                                    st.json(chapter_structure)
                            else:
                                st.error("❌ JSON文件格式不正确，缺少必要的'nodes'字段")
                                
                    except Exception as e:
                        st.error(f"❌ 文件处理失败: {str(e)}")
            
            elif chapter_input_method == "从历史结果导入":
                # 检查是否有历史的处理结果
                if 'backward_v2_result' in st.session_state and st.session_state.backward_v2_result.get("chapter_structure"):
                    if st.button("📥 导入历史章节结构", key="import_history_structure"):
                        chapter_structure = st.session_state.backward_v2_result["chapter_structure"]
                        history_nodes_count = len(chapter_structure.get("nodes", {}))
                        st.success(f"✅ 从历史结果导入章节结构，包含 {history_nodes_count} 个章节")
                        
                        with st.expander("📋 历史章节结构预览"):
                            st.json(chapter_structure)
                else:
                    st.info("💡 暂无历史处理结果可导入，请先执行一次Backward V2处理")
            
            elif chapter_input_method == "手动编辑JSON":
                st.info("💡 提示：可以先使用其他方式导入基础结构，然后在此基础上编辑")
                
                # 提供默认的章节结构模板
                default_structure = {
                    "nodes": {
                        "chapter_1": {
                            "id": "chapter_1",
                            "title": "基础知识",
                            "level": 1,
                            "parent_id": None,
                            "children": [],
                            "description": "基础概念和原理",
                            "related_cqa_items": [],
                            "related_cqa_ids": [],
                            "chapter_number": "1."
                        }
                    },
                    "root_ids": ["chapter_1"],
                    "max_level": 3
                }
                
                # 如果有已存在的结构，使用它作为起始点
                if 'manual_chapter_structure' not in st.session_state:
                    st.session_state.manual_chapter_structure = json.dumps(default_structure, ensure_ascii=False, indent=2)
                
                edited_structure_text = st.text_area(
                    "编辑章节结构JSON",
                    value=st.session_state.manual_chapter_structure,
                    height=300,
                    key="manual_structure_editor",
                    help="编辑章节结构的JSON格式数据"
                )
                
                col_validate, col_reset = st.columns([1, 1])
                
                with col_validate:
                    if st.button("✅ 验证并应用", key="validate_manual_structure"):
                        try:
                            import json
                            parsed_structure = json.loads(edited_structure_text)
                            
                            # 基本验证
                            if isinstance(parsed_structure, dict) and "nodes" in parsed_structure:
                                chapter_structure = parsed_structure
                                st.session_state.manual_chapter_structure = edited_structure_text
                                nodes_count = len(parsed_structure.get("nodes", {}))
                                st.success(f"✅ 章节结构验证成功，包含 {nodes_count} 个章节")
                            else:
                                st.error("❌ JSON结构不正确，需要包含'nodes'字段")
                        except json.JSONDecodeError as e:
                            st.error(f"❌ JSON格式错误: {str(e)}")
                        except Exception as e:
                            st.error(f"❌ 验证失败: {str(e)}")
                
                with col_reset:
                    if st.button("🔄 重置为默认", key="reset_manual_structure"):
                        st.session_state.manual_chapter_structure = json.dumps(default_structure, ensure_ascii=False, indent=2)
                        st.rerun()

        # 处理参数
        st.subheader("🎯 处理参数")
        max_level = st.number_input("最大章节层级",
                                    min_value=1,
                                    max_value=5,
                                    value=backward_v2_example.get("max_level", 3))

        # 提交测试
        if st.button("🚀 执行 Backward V2 处理", type="primary", key="run_backward_v2"):
            if not qa_lists:
                st.error("请输入至少一个对话序列")
            else:
                try:
                    request_data = {
                        "qa_lists": qa_lists,
                        "max_level": max_level
                    }
                    if chapter_structure:
                        request_data["chapter_structure"] = chapter_structure

                    with st.spinner("正在执行 Backward V2 处理..."):
                        response = requests.post(f"{api_url}/backward_v2", json=request_data)

                    if response.status_code == 200:
                        result = response.json()
                        st.success("✅ 处理完成！")
                        # 保存结果
                        st.session_state.backward_v2_result = result
                    else:
                        st.error(f"处理失败: {response.status_code} - {response.text}")

                except Exception as e:
                    st.error(f"请求失败: {str(e)}")

    with col2:
        st.subheader("📊 处理结果")

        if 'backward_v2_result' in st.session_state:
            result = st.session_state.backward_v2_result

            # 基本统计信息
            col_a, col_b = st.columns(2)
            with col_a:
                chapter_count = len(result.get("chapter_structure", {}).get("nodes", {}))
                st.metric("章节数", chapter_count)
            with col_b:
                ospa_count = len(result.get("ospa_list", []))
                st.metric("OSPA条目", ospa_count)

            # 操作日志
            if result.get("operation_log"):
                st.write("**操作日志**:")
                for i, log in enumerate(result["operation_log"]):
                    st.write(f"{i+1}. {log}")

            # 章节结构树状预览
            if result.get("chapter_structure"):
                with st.expander("🗂️ 查看章节结构（树状视图）", expanded=True):
                    def display_tree_node(node, level=0, is_last=True, prefix=""):
                        """递归显示树状结构节点"""
                        # 创建树状显示的前缀
                        if level == 0:
                            tree_prefix = ""
                            current_prefix = ""
                        else:
                            tree_prefix = prefix + ("└── " if is_last else "├── ")
                            current_prefix = prefix + ("    " if is_last else "│   ")
                        
                        # 显示当前节点
                        title = node.get('title', 'Unknown')
                        chapter_num = node.get('chapter_number', '')
                        related_count = len(node.get('related_cqa_items', []))
                        
                        st.write(f"{tree_prefix}📁 **{chapter_num}{title}**")
                        if node.get('description'):
                            st.write(f"{current_prefix}   📝 {node['description']}")
                        
                        # 显示章节内容（生成的提示词）
                        if node.get('content'):
                            content = node['content']
                            if len(content) > 80:
                                content_preview = content[:80] + "..."
                                st.write(f"{current_prefix}   🎯 提示词: {content_preview}")
                                # 在expander中显示完整内容
                                with st.expander(f"查看完整提示词 ({len(content)} 字符)", expanded=False):
                                    st.code(content, language="text")
                            else:
                                st.write(f"{current_prefix}   🎯 提示词: {content}")
                        
                        if related_count > 0:
                            st.write(f"{current_prefix}   💬 包含 {related_count} 个问答对")
                        
                        # 递归显示子节点
                        children = node.get('children', [])
                        if children:
                            for i, child_id in enumerate(children):
                                child_node = chapter_nodes.get(child_id)
                                if child_node:
                                    is_last_child = (i == len(children) - 1)
                                    display_tree_node(child_node, level + 1, is_last_child, current_prefix)
                    
                    chapter_nodes = result["chapter_structure"].get("nodes", {})
                    root_ids = result["chapter_structure"].get("root_ids", [])
                    
                    if root_ids:
                        st.write("### 📊 章节层次结构")
                        for i, root_id in enumerate(root_ids):
                            root_node = chapter_nodes.get(root_id)
                            if root_node:
                                is_last_root = (i == len(root_ids) - 1)
                                display_tree_node(root_node, 0, is_last_root, "")
                                if not is_last_root:
                                    st.write("")  # 根节点之间添加空行
                    else:
                        st.info("章节结构为空或格式不正确")
                    
                    # 章节统计信息
                    st.write("---")
                    total_nodes = len(chapter_nodes)
                    total_qas = sum(len(node.get('related_cqa_items', [])) for node in chapter_nodes.values())
                    max_level = result["chapter_structure"].get("max_level", 0)
                    
                    col_stat1, col_stat2, col_stat3 = st.columns(3)
                    with col_stat1:
                        st.metric("总章节数", total_nodes)
                    with col_stat2:
                        st.metric("总问答数", total_qas)
                    with col_stat3:
                        st.metric("最大层级", max_level)

            # OSPA数据详细预览
            if result.get("ospa_list"):
                with st.expander(f"📋 查看OSPA数据详情 ({len(result['ospa_list'])} 条)", expanded=False):
                    # 显示模式选择
                    display_mode = st.radio(
                        "显示模式",
                        ["表格概览", "详细展开"],
                        key="ospa_display_mode",
                        horizontal=True
                    )
                    
                    if display_mode == "表格概览":
                        # 简化表格显示
                        ospa_df = pd.DataFrame([
                            {
                                "序号": i+1,
                                "观察(O)": ospa.get("o", "")[:60] + "..." if len(ospa.get("o", "")) > 60 else ospa.get("o", ""),
                                "场景(S)": ospa.get("s", "")[:25] + "..." if len(ospa.get("s", "")) > 25 else ospa.get("s", ""),
                                "提示词长度": f"{len(ospa.get('p', ''))} 字符",
                                "回答(A)": ospa.get("a", "")[:60] + "..." if len(ospa.get("a", "")) > 60 else ospa.get("a", "")
                            }
                            for i, ospa in enumerate(result["ospa_list"][:15])  # 显示前15条
                        ])
                        st.dataframe(ospa_df, use_container_width=True)
                        if len(result["ospa_list"]) > 15:
                            st.info(f"📋 共 {len(result['ospa_list'])} 条OSPA数据，表格显示前15条，请切换到'详细展开'模式查看完整内容")
                    
                    else:  # 详细展开模式
                        # 数量选择
                        max_display = min(len(result["ospa_list"]), 10)
                        num_to_display = st.slider(
                            "显示条目数量",
                            min_value=1,
                            max_value=max_display,
                            value=min(5, max_display),
                            key="ospa_detail_count"
                        )
                        
                        st.write(f"### 📋 详细OSPA内容 (显示前{num_to_display}条)")
                        
                        for i, ospa in enumerate(result["ospa_list"][:num_to_display]):
                            with st.container():
                                st.write(f"#### 🔢 OSPA条目 {i+1}")
                                
                                # O - 观察
                                st.write("**🔍 观察 (Observation)**")
                                st.info(ospa.get("o", "未提供"))
                                
                                # S - 场景
                                st.write("**🎭 场景 (Scenario)**")
                                st.success(ospa.get("s", "未提供"))
                                
                                # P - 提示词（完整显示）
                                st.write("**🎯 完整章节提示词 (Prompt)**")
                                prompt_content = ospa.get("p", "未提供提示词")
                                
                                # 分析提示词内容，尝试提取案例
                                if "案例" in prompt_content or "例如" in prompt_content or "举例" in prompt_content:
                                    st.write("✨ **包含相关案例的完整提示词：**")
                                else:
                                    st.write("📝 **章节提示词内容：**")
                                
                                # 使用代码块显示完整提示词
                                st.code(prompt_content, language="text")
                                
                                # 提示词统计
                                prompt_stats = f"📊 字符数: {len(prompt_content)} | 行数: {len(prompt_content.split())}"
                                st.caption(prompt_stats)
                                
                                # A - 回答
                                st.write("**💬 标准回答 (Answer)**")
                                st.write(ospa.get("a", "未提供"))
                                
                                # 分隔线
                                if i < num_to_display - 1:
                                    st.markdown("---")
                        
                        # 显示更多数据的提示
                        if len(result["ospa_list"]) > num_to_display:
                            remaining = len(result["ospa_list"]) - num_to_display
                            st.info(f"📋 还有 {remaining} 条OSPA数据未显示，可调整上方滑块查看更多内容")
                    
                    # OSPA数据统计
                    st.write("---")
                    st.write("### 📊 OSPA数据统计")
                    
                    # 计算统计信息
                    total_ospa = len(result["ospa_list"])
                    avg_prompt_length = sum(len(ospa.get("p", "")) for ospa in result["ospa_list"]) / total_ospa if total_ospa > 0 else 0
                    scenarios = list(set(ospa.get("s", "") for ospa in result["ospa_list"]))
                    
                    col_s1, col_s2, col_s3 = st.columns(3)
                    with col_s1:
                        st.metric("OSPA总数", total_ospa)
                    with col_s2:
                        st.metric("平均提示词长度", f"{int(avg_prompt_length)} 字符")
                    with col_s3:
                        st.metric("场景类型数", len(scenarios))
                    
                    # 场景分布
                    if scenarios:
                        st.write("**📊 场景分布：**")
                        scenario_counts = {}
                        for ospa in result["ospa_list"]:
                            scenario = ospa.get("s", "未知场景")
                            scenario_counts[scenario] = scenario_counts.get(scenario, 0) + 1
                        
                        for scenario, count in sorted(scenario_counts.items(), key=lambda x: x[1], reverse=True):
                            st.write(f"• **{scenario}**: {count} 条")

            # 完整结果查看
            with st.expander("🔍 查看完整结果 JSON"):
                st.json(result)

            # 导出功能
            st.write("### 📤 数据导出")
            col_export1, col_export2 = st.columns(2)
            
            with col_export1:
                # 导出OSPA数据
                if st.button("💾 导出 OSPA 数据", key="export_backward_v2_ospa"):
                    if result.get("ospa_list"):
                        ospa_df = pd.DataFrame([
                            {
                                "O": ospa.get("o", ""),
                                "S": ospa.get("s", ""),
                                "P": ospa.get("p", ""),
                                "A": ospa.get("a", "")
                            }
                            for ospa in result["ospa_list"]
                        ])
                        csv = ospa_df.to_csv(index=False)
                        st.download_button(
                            label="📄 下载 OSPA CSV 文件",
                            data=csv,
                            file_name=f"backward_v2_ospa_data_{int(time.time())}.csv",
                            mime="text/csv",
                            key="download_ospa_csv")
            
            with col_export2:
                # 导出章节结构 
                if st.button("🗂️ 导出章节结构", key="export_backward_v2_structure"):
                    if result.get("chapter_structure"):
                        try:
                            # 重建ChapterStructure对象以使用新的导出方法
                            from src.agent_runtime.data_format.chapter_format import ChapterStructure
                            chapter_data = result["chapter_structure"]
                            
                            # 使用新的JSON导出方法
                            if hasattr(chapter_data, 'to_json_string'):
                                # 如果已经是ChapterStructure对象
                                structure_json = chapter_data.to_json_string(indent=2, ensure_ascii=False)
                            else:
                                # 如果是字典格式，先转换为ChapterStructure对象
                                structure = ChapterStructure.from_json_string(
                                    json.dumps(chapter_data, ensure_ascii=False)
                                )
                                structure_json = structure.to_json_string(indent=2, ensure_ascii=False)
                            
                            st.download_button(
                                label="📋 下载完整章节结构 JSON",
                                data=structure_json,
                                file_name=f"complete_chapter_structure_{int(time.time())}.json",
                                mime="application/json",
                                key="download_complete_structure_json",
                                help="包含完整的章节内容、CQA数据和元数据"
                            )
                        except Exception as e:
                            # 降级到原来的导出方法
                            import json
                            structure_json = json.dumps(result["chapter_structure"], ensure_ascii=False, indent=2)
                            st.download_button(
                                label="📋 下载章节结构 JSON",
                                data=structure_json,
                                file_name=f"chapter_structure_{int(time.time())}.json",
                                mime="application/json",
                                key="download_structure_json")
                            st.warning(f"使用简化导出格式: {str(e)}")
            
            # 导出组合数据
            if result.get("chapter_structure") and result.get("ospa_list"):
                if st.button("📦 导出完整处理结果", key="export_complete_result"):
                    import json
                    complete_result = {
                        "metadata": {
                            "export_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "total_chapters": len(result.get("chapter_structure", {}).get("nodes", {})),
                            "total_ospa": len(result.get("ospa_list", [])),
                            "operation_log": result.get("operation_log", [])
                        },
                        "chapter_structure": result.get("chapter_structure"),
                        "ospa_list": result.get("ospa_list")
                    }
                    complete_json = json.dumps(complete_result, ensure_ascii=False, indent=2)
                    st.download_button(
                        label="📁 下载完整结果 JSON",
                        data=complete_json,
                        file_name=f"backward_v2_complete_result_{int(time.time())}.json",
                        mime="application/json",
                        key="download_complete_result")
        else:
            st.info("暂无处理结果")

# ==================== OSPA 表格页面（重点优化） ====================
with tabs[4]:
    st.header("📊 OSPA 表格管理")

    st.markdown("**功能说明**: 管理和分析 OSPA (Observation-State-Prompt-Action) 数据，"
                "支持一致性检测和自动生成")

    ospa_manager = st.session_state.ospa_manager

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("📁 数据加载")

        col_data_source, col_statistics = st.columns([1, 3])
        with col_data_source:
            # 选择数据源
            data_source = st.radio("数据源选择", ["上传 CSV 文件", "使用示例数据", "手动输入"],
                                   key="ospa_data_source")
        with col_statistics:
            # 显示数据统计
            StreamlitUtils.show_statistics(ospa_manager)

        # 数据加载处理
        new_manager = _handle_data_loading(data_source, ospa_manager)
        if new_manager:
            ospa_manager = st.session_state.ospa_manager = copy.deepcopy(
                new_manager)
            new_manager = None
            st.rerun()

        # 显示和编辑当前数据
        if ospa_manager.items:
            # 表格标题和更新按钮
            col_title, col_update = st.columns([4, 1])
            with col_title:
                st.subheader("📋 当前 OSPA 数据表格")
            with col_update:
                if st.button("🔄 更新数据",
                             type="primary",
                             help="保存表格编辑的内容并刷新显示",
                             key="update_ospa_table"):
                    st.rerun()

            # 显示可编辑表格
            edited_df = StreamlitUtils.display_ospa_table(
                ospa_manager, "ospa_editor")

            # 显示表格说明
            st.markdown("""
            **表格说明**：
            - **O**: 观察/用户输入
            - **S**: 状态/场景
            - **p**: 提示词
            - **A**: Agent输出/标准答案
            - **A'**: 候选答案（用于一致性比较）
            - **consistency**: A与A'的语义一致性得分
            - **confidence_score**: 一致性检测的置信度
            - **error**: 错误信息
            """)

            # 更新管理器数据
            if edited_df is not None:
                if StreamlitUtils.update_manager_from_edited_df(
                        ospa_manager, edited_df):
                    # 数据已更新
                    pass

    with col2:
        st.subheader("🔧 操作控制")

        if ospa_manager.items:
            # 显示统计信息
            # StreamlitUtils.show_statistics(ospa_manager)

            # 状态提示词生成
            st.write("**状态提示词生成**")
            st.markdown("使用 Backward API 根据 O、A 生成对应的 S、p")

            valid_backward_count = len(
                ospa_manager.get_valid_items_for_backward())
            # st.info(f"当前有 {valid_backward_count} 条数据可进行状态和提示词生成")

            with st.expander("🔧 生成参数配置", expanded=False):
                chapters_extra_instructions = st.text_area(
                    "章节聚合额外指令(选填)", value="", help="指导如何聚合问答对到章节的额外说明")
                gen_p_extra_instructions = st.text_area("提示词生成额外指令(选填)",
                                                        value="",
                                                        help="指导如何生成提示词的额外说明")
                overwrite_mode = st.radio("数据更新模式", ["只更新空白字段", "覆盖所有字段"],
                                          index=0,
                                          help="选择如何处理已有的S、p数据")

            col_c, col_d = st.columns(2)
            with col_c:
                if st.button("↩️ 生成状态和提示词",
                             type="secondary",
                             key="run_backward_generation",
                             disabled=valid_backward_count == 0):
                    status_placeholder = st.empty()

                    result = processor.process_backward_generation(
                        ospa_manager, chapters_extra_instructions,
                        gen_p_extra_instructions, overwrite_mode)

                    status_placeholder.empty()

                    if result['success']:
                        if result.get('skipped_count', 0) > 0:
                            st.success(
                                f"✅ 成功生成状态和提示词！更新了 {result['updated_count']} 条，跳过了 {result['skipped_count']} 条"
                            )
                        else:
                            st.success(
                                f"✅ 成功生成状态和提示词！更新了 {result['updated_count']} 条"
                            )

                        # 保存结果到会话状态
                        st.session_state.backward_generation_result = result
                        # 强制刷新页面以显示更新的表格数据
                        st.rerun()
                    else:
                        st.error(f"❌ {result['error']}")
                        st.session_state.backward_generation_result = result

            with col_d:
                if st.button("🔄 清空状态提示词", type="secondary"):
                    ospa_manager.clear_field('S')
                    ospa_manager.clear_field('p')
                    st.rerun()
                    st.success("✅ 已清空所有状态和提示词")

            # 显示状态提示词生成结果
            if 'backward_generation_result' in st.session_state:
                with st.expander("📄 状态提示词生成结果", expanded=False):
                    st.json(st.session_state.backward_generation_result)

            # 智能答案生成
            st.write("**智能答案生成**")
            st.markdown("使用 LLM Ask API 根据 O（观察）和 p（提示词）生成 A'（答案）")

            valid_llm_count = len(ospa_manager.get_valid_items_for_llm())
            # st.info(f"当前有 {valid_llm_count} 条数据可进行答案生成")

            with st.expander("🔧 生成配置", expanded=False):
                answer_temperature = st.slider(
                    "生成温度",
                    min_value=0.0,
                    max_value=2.0,
                    value=0.3,
                    step=0.1,
                    help="控制生成答案的创造性，0.0最确定，2.0最有创造性")
                answer_generation_mode = st.radio("A'字段更新模式",
                                                  ["只更新空白字段", "覆盖所有字段"],
                                                  index=0,
                                                  help="选择如何处理已有的A'字段数据")
                llm_enable_concurrent = st.checkbox(
                    "启用并发处理", value=True, key="llm_concurrent_enabled")
                llm_max_concurrent = st.selectbox("并发请求数", [1, 3, 5, 8, 10],
                                                  index=3,
                                                  key="llm_concurrent_num")

            col_e, col_f = st.columns(2)
            with col_e:
                if st.button("🤖 智能生成答案",
                             type="secondary",
                             key="run_answer_generation",
                             disabled=valid_llm_count == 0):
                    progress_bar = st.progress(0)
                    status_placeholder = st.empty()

                    result = processor.process_llm_generation(
                        ospa_manager, answer_temperature,
                        answer_generation_mode, llm_enable_concurrent,
                        llm_max_concurrent, lambda p: progress_bar.progress(p),
                        lambda s: status_placeholder.info(s))

                    progress_bar.empty()
                    status_placeholder.empty()

                    if result['success']:
                        if result.get('skipped_count', 0) > 0:
                            st.success(
                                f"✅ 完成答案生成！生成了 {result['success_count']} 条新答案，跳过了 {result['skipped_count']} 条"
                            )
                        else:
                            st.success(
                                f"✅ 完成答案生成！成功生成: {result['success_count']} 条答案"
                            )

                        # 保存结果到会话状态
                        st.session_state.answer_generation_result = result
                        # 清除表格编辑器的状态缓存，强制重新渲染
                        st.rerun()
                    else:
                        st.error(f"❌ {result['error']}")
                        st.session_state.answer_generation_result = result

            with col_f:
                if st.button("🔄 清空生成答案", type="secondary"):
                    ospa_manager.clear_field('A_prime')
                    st.rerun()
                    st.success("✅ 已清空所有生成的答案")

            # 显示智能答案生成结果
            if 'answer_generation_result' in st.session_state:
                with st.expander("🤖 智能答案生成结果", expanded=False):
                    st.json(st.session_state.answer_generation_result)

            # 一致性检测
            st.write("**一致性检测**")
            st.markdown("使用 Reward API 计算每行数据中 A 和 A' 的语义一致性")

            valid_reward_count = len(ospa_manager.get_valid_items_for_reward())
            # st.info(f"当前有 {valid_reward_count} 条数据可进行一致性检测")

            with st.expander("🔧 一致性检测配置", expanded=False):
                reward_enable_concurrent = st.checkbox(
                    "启用并发处理", value=True, key="reward_concurrent_enabled")
                reward_max_concurrent = st.selectbox(
                    "并发请求数", [1, 3, 5, 8, 10],
                    index=3,
                    key="reward_concurrent_num")

            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("🏆 执行一致性检测",
                             type="primary",
                             key="run_consistency_check",
                             disabled=valid_reward_count == 0):
                    progress_bar = st.progress(0)
                    status_placeholder = st.empty()

                    result = processor.process_reward_consistency(
                        ospa_manager, reward_enable_concurrent,
                        reward_max_concurrent,
                        lambda p: progress_bar.progress(p),
                        lambda s: status_placeholder.info(s))

                    progress_bar.empty()
                    status_placeholder.empty()

                    if result['success']:
                        st.success(
                            f"✅ 完成一致性检测！成功: {result['success_count']}/{result['processed_count']} 条"
                        )

                        # 保存结果到会话状态
                        st.session_state.consistency_check_result = result
                        # 强制刷新页面以显示更新的表格数据
                        st.rerun()
                    else:
                        st.error(f"❌ {result['error']}")
                        st.session_state.consistency_check_result = result

            with col_b:
                if st.button("🔄 清空一致性结果", type="secondary"):
                    ospa_manager.clear_field('consistency')
                    ospa_manager.clear_field('confidence_score')
                    ospa_manager.clear_field('error')
                    st.rerun()
                    st.success("✅ 已清空所有一致性检测结果")

            # 显示一致性检测结果
            if 'consistency_check_result' in st.session_state:
                with st.expander("🏆 一致性检测结果", expanded=False):
                    st.json(st.session_state.consistency_check_result)

            # 数据管理
            st.write("**数据管理**")
            col_a, col_b = st.columns(2)

            with col_a:
                if st.button("💾 导出 OSPA 数据", key="export_ospa"):
                    export_df = ospa_manager.to_dataframe()
                    csv = export_df.to_csv(index=False)
                    st.download_button(
                        label="下载 CSV 文件",
                        data=csv,
                        file_name=f"ospa_data_{int(time.time())}.csv",
                        mime="text/csv")

            with col_b:
                if st.button("🗑️ 清空所有数据", key="clear_ospa"):
                    st.session_state.ospa_manager = OSPAManager()
                    st.rerun()
        else:
            st.info("请先加载或输入 OSPA 数据")

# ==================== Agent 管理页面 ====================
with tabs[5]:
    # 页面标题和简洁说明
    st.markdown("## 🤖 Agent 提示词管理")

    # 获取支持的Agent名称（自动加载）
    if 'agent_names' not in st.session_state:
        try:
            response = requests.get(f"{api_url}/agents/names")
            if response.status_code == 200:
                agent_names = response.json()
                st.session_state.agent_names = agent_names
            else:
                st.error(f"🚫 获取Agent名称失败: {response.status_code}")
                st.session_state.agent_names = []
        except Exception as e:
            st.error(f"🚫 请求失败: {e}")
            st.session_state.agent_names = []

    # 紧凑的Agent选择区域
    if st.session_state.agent_names:
        col_select, col_info = st.columns([2, 3])

        with col_select:
            selected_agent = st.selectbox("🎯 选择Agent",
                                          st.session_state.agent_names,
                                          key="selected_agent_name",
                                          help="选择后自动加载提示词")

        with col_info:
            if selected_agent:
                st.info(f"📋 正在管理: **{selected_agent}**")

        # 自动获取选定Agent的详细信息
        if selected_agent:
            try:
                response = requests.get(
                    f"{api_url}/agents/{selected_agent}/prompts")
                if response.status_code == 200:
                    agent_info = response.json()
                    # 只在Agent变更时更新信息，避免重复请求
                    if ('current_agent_info' not in st.session_state
                            or st.session_state.current_agent_info.get(
                                'agent_name') != selected_agent):
                        st.session_state.current_agent_info = agent_info
                        st.session_state.original_system_prompt = agent_info.get(
                            'system_prompt', '')
                        st.session_state.original_user_template = agent_info.get(
                            'user_prompt_template', '')
                else:
                    st.error(f"🚫 获取Agent信息失败: {response.status_code}")
            except Exception as e:
                st.error(f"🚫 请求失败: {e}")

        # 显示和编辑Agent提示词
        if 'current_agent_info' in st.session_state:
            agent_info = st.session_state.current_agent_info

            # 紧凑的基本信息展示
            template_vars = agent_info.get('template_variables', [])

            with st.container():
                col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
                with col1:
                    st.metric("Agent名称",
                              agent_info.get('agent_name', 'N/A'),
                              delta=None)
                with col2:
                    st.metric("模板变量", 
                             f"{len(template_vars)} 个", 
                             delta=None)
                with col3:
                    sys_len = len(agent_info.get('system_prompt', ''))
                    st.metric("系统提示词", 
                             f"{sys_len} 字符", 
                             delta=None)
                with col4:
                    tpl_len = len(agent_info.get('user_prompt_template', ''))
                    st.metric("用户模板", 
                             f"{tpl_len} 字符", 
                             delta=None)

            if template_vars:
                st.info(f"🔧 **模板变量**: {', '.join(template_vars)}")

            # 主编辑区域 - 使用紧凑布局
            main1_col, main2_col, side_col = st.columns([3, 3, 2])

            with main1_col:
                # 使用expander来节省空间
                with st.expander("📝 系统提示词编辑", expanded=True):
                    current_system_prompt = st.text_area(
                        "系统提示词内容",
                        value=agent_info.get('system_prompt', ''),
                        height=360,
                        key="edit_system_prompt",
                        label_visibility="collapsed",
                        help="编辑系统提示词内容")

            with main2_col:
                with st.expander("📄 用户提示词模板编辑", expanded=True):
                    current_user_template = st.text_area(
                        "用户模板内容",
                        value=agent_info.get('user_prompt_template', ''),
                        height=360,
                        key="edit_user_template",
                        label_visibility="collapsed",
                        help="支持Jinja2模板语法")

            with side_col:
                # 紧凑的操作面板
                st.markdown("#### 🔧 操作中心")

                # 检查是否有修改
                has_system_changes = current_system_prompt != st.session_state.get(
                    'original_system_prompt', '')
                has_template_changes = current_user_template != st.session_state.get(
                    'original_user_template', '')
                has_changes = has_system_changes or has_template_changes

                # 状态指示器
                if has_changes:
                    st.warning("⚠️ 有未保存修改")
                    changes_info = []
                    if has_system_changes:
                        changes_info.append("系统提示词")
                    if has_template_changes:
                        changes_info.append("用户模板")
                    st.caption(f"修改: {', '.join(changes_info)}")
                else:
                    st.success("✅ 内容已保存")

                # 主要操作按钮
                update_clicked = st.button(
                    "💾 保存修改",
                    type="primary" if has_changes else "secondary",
                    disabled=not has_changes,
                    key="update_prompts_btn",
                    use_container_width=True,
                    help="保存当前修改的提示词内容")

                if update_clicked and has_changes:
                    # 构建更新数据
                    update_data = {}
                    if has_system_changes:
                        update_data[
                            "system_prompt"] = current_system_prompt.strip()
                    if has_template_changes:
                        update_data[
                            "user_prompt_template"] = current_user_template.strip(
                            )

                    try:
                        with st.spinner("正在保存..."):
                            response = requests.put(
                                f"{api_url}/agents/{selected_agent}"
                                f"/prompts",
                                json=update_data)

                        if response.status_code == 200:
                            updated_info = response.json()
                            st.session_state.current_agent_info = updated_info
                            st.session_state.original_system_prompt = \
                                updated_info.get('system_prompt', '')
                            st.session_state.original_user_template = \
                                updated_info.get('user_prompt_template', '')
                            st.success("✅ 保存成功！")
                            st.rerun()
                        else:
                            st.error(f"保存失败: {response.status_code}")
                    except Exception as e:
                        st.error(f"请求失败: {e}")

                # 辅助操作按钮组
                col_reset, col_refresh = st.columns(2)

                with col_reset:
                    reset_clicked = st.button("🔄默认",
                                              key="reset_to_default",
                                              help="重置为默认",
                                              use_container_width=True)
                with col_refresh:
                    refresh_clicked = st.button("🔃刷新",
                                                key="refresh_agent",
                                                help="刷新内容",
                                                use_container_width=True)

                # 处理重置操作
                if reset_clicked:
                    try:
                        response = requests.post(
                            f"{api_url}/agents/{selected_agent}"
                            f"/prompts/reset")
                        if response.status_code == 200:
                            reset_info = response.json()
                            st.session_state.current_agent_info = reset_info
                            st.session_state.original_system_prompt = \
                                reset_info.get('system_prompt', '')
                            st.session_state.original_user_template = \
                                reset_info.get('user_prompt_template', '')
                            st.success("✅ 已重置")
                            st.rerun()
                        else:
                            st.error("重置失败")
                    except Exception as e:
                        st.error(f"重置失败: {e}")

                # 处理刷新操作
                if refresh_clicked:
                    try:
                        response = requests.get(
                            f"{api_url}/agents/{selected_agent}/prompts")
                        if response.status_code == 200:
                            fresh_info = response.json()
                            st.session_state.current_agent_info = fresh_info
                            st.session_state.original_system_prompt = \
                                fresh_info.get('system_prompt', '')
                            st.session_state.original_user_template = \
                                fresh_info.get('user_prompt_template', '')
                            st.success("✅ 已刷新")
                            st.rerun()
                        else:
                            st.error("刷新失败")
                    except Exception as e:
                        st.error(f"刷新失败: {e}")

                # 快捷统计信息     
                st.markdown("---")
                st.markdown("##### 📊 内容统计")

                if has_changes:
                    # 显示修改前后对比
                    orig_sys_len = len(
                        st.session_state.get('original_system_prompt', ''))
                    curr_sys_len = len(current_system_prompt)
                    orig_tpl_len = len(
                        st.session_state.get('original_user_template', ''))
                    curr_tpl_len = len(current_user_template)

                    st.caption(f"系统提示词: {orig_sys_len} → {curr_sys_len} 字符")
                    st.caption(f"用户模板: {orig_tpl_len} → {curr_tpl_len} 字符")
                else:
                    sys_len = len(current_system_prompt)
                    tpl_len = len(current_user_template)
                    st.caption(f"系统提示词: {sys_len} 字符")
                    st.caption(f"用户模板: {tpl_len} 字符")

            # 模板变量验证区域
            st.markdown("---")

            col_validate, col_preview = st.columns([1, 1])

            with col_validate:
                st.subheader("🧪 模板变量验证")
                template_vars = agent_info.get('template_variables', [])

                if template_vars:
                    st.write(f"**需要变量**: {', '.join(template_vars)}")

                    # 定义默认值映射
                    def get_default_value(var_name: str) -> str:
                        """获取变量的默认测试值"""
                        defaults = {
                            'question': '什么是人工智能？',
                            'target_answer':
                            '人工智能是计算机科学的一个分支，致力于创建能够执行通常需要人类智能的任务的系统。',
                            'candidates':
                            '人工智能是机器学习,AI是计算机技术,人工智能模拟人类思维,AI用于自动化任务',
                            'query': '请解释机器学习的基本概念',
                            'context': '机器学习是人工智能的重要组成部分',
                            'input': '请分析以下文本内容',
                            'text': '这是一段需要分析的示例文本内容',
                            'prompt': '请根据以下信息进行分析',
                            'content': '这里是需要处理的内容示例',
                            'task': '文本分类任务',
                            'examples': '示例1,示例2,示例3',
                            'instructions': '请按照以下步骤进行操作',
                            'format': 'JSON格式输出',
                            'language': '中文',
                            'topic': '科技发展',
                            'style': '正式学术风格'
                        }
                        return defaults.get(var_name, f'{var_name}的测试值')

                    # col_inputs, col_buttons = st.columns([3, 1])

                    # with col_inputs:
                        # 简化的变量验证表单
                    with st.form("quick_validate_form"):
                        test_vars = {}
                        
                        # 检查是否需要使用随机数据
                        use_random = st.session_state.get(
                            'use_random_data', False)

                        for var in template_vars:
                            if var == 'candidates':
                                # 获取数据源（随机或默认）
                                if (use_random and 
                                    'random_data' in st.session_state):
                                    random_candidates = st.session_state.\
                                        random_data.get(var, [])
                                    if isinstance(random_candidates, list):
                                        display_value = ','.join(
                                            random_candidates)
                                    else:
                                        display_value = str(
                                            random_candidates)
                                else:
                                    display_value = get_default_value(var)
                                
                                candidates_input = st.text_input(
                                    f"{var} (用逗号分隔)",
                                    value=display_value,
                                    key=f"quick_test_{var}",
                                    help="已填入测试数据，可直接使用或修改")
                                if candidates_input.strip():
                                    test_vars[var] = [
                                        item.strip() for item in
                                        candidates_input.split(',')
                                        if item.strip()
                                    ]
                            else:
                                # 获取数据源（随机或默认）
                                if (use_random and 
                                    'random_data' in st.session_state):
                                    display_value = st.session_state.\
                                        random_data.get(var, 
                                                        get_default_value(var))
                                else:
                                    display_value = get_default_value(var)
                                
                                var_input = st.text_input(
                                    var,
                                    value=str(display_value),
                                    key=f"quick_test_{var}",
                                    help="已填入测试数据，可直接使用或修改")
                                if var_input.strip():
                                    test_vars[var] = var_input.strip()

                        # 四列按钮：验证、清空、默认值、随机
                        col_validate, col_clear, col_default, col_random = \
                            st.columns(4)
                        
                        with col_validate:
                            validate_clicked = st.form_submit_button(
                                "✅ 验证", type="primary")
                        with col_clear:
                            clear_clicked = st.form_submit_button(
                                "🗑️ 清空")
                        with col_default:
                            default_clicked = st.form_submit_button(
                                "🎯 默认值")
                        with col_random:
                            random_clicked = st.form_submit_button(
                                "🎲 随机")

                        if validate_clicked:
                            if test_vars:
                                try:
                                    with st.spinner("正在验证模板..."):
                                        response = requests.post(
                                            f"{api_url}/agents/"
                                            f"{selected_agent}/prompts/"
                                            f"validate",
                                            json=test_vars)

                                    if response.status_code == 200:
                                        validation_result = response.json()
                                        st.session_state.validation_result = \
                                            validation_result
                                        st.session_state.last_test_vars = \
                                            test_vars

                                        if validation_result.get('valid'):
                                            st.success("✅ 模板验证通过！")
                                        else:
                                            st.error("❌ 模板验证失败")
                                    else:
                                        st.error(
                                            f"验证失败: {response.status_code}"
                                        )
                                except Exception as e:
                                    st.error(f"请求失败: {e}")
                            else:
                                st.warning("请至少提供一个变量值")

                        if clear_clicked:
                            # 清空验证结果和随机数据标记
                            for key in ['validation_result', 
                                        'use_random_data', 'random_data']:
                                if key in st.session_state:
                                    del st.session_state[key]
                            st.info("已清空验证结果")
                            st.rerun()
                            
                        if default_clicked:
                            # 使用默认值
                            for key in ['use_random_data', 'random_data']:
                                if key in st.session_state:
                                    del st.session_state[key]
                            st.success("✅ 已重置为默认值")
                            st.rerun()
                            
                        if random_clicked:
                            # 生成随机数据
                            import random
                            random_data = {
                                'question': random.choice([
                                    '什么是深度学习？', '如何理解神经网络？', 
                                    '机器学习有哪些应用？', '什么是自然语言处理？'
                                ]),
                                'target_answer': random.choice([
                                    '深度学习是机器学习的一个子领域。', 
                                    '神经网络是模仿人脑结构的计算模型。',
                                    '机器学习广泛应用于各个领域。', 
                                    '自然语言处理让计算机理解人类语言。'
                                ]),
                                'candidates': random.sample([
                                    '这是第一个候选答案', '这是另一个可能的答案', 
                                    '还有这个备选方案', '最后一个候选答案', 
                                    '额外的答案选项', '补充的候选内容'
                                ], 3),
                                'query': random.choice([
                                    '请解释机器学习的基本概念',
                                    '分析深度学习的应用场景', 
                                    '描述神经网络的工作原理'
                                ]),
                                'context': random.choice([
                                    '机器学习是人工智能的重要组成部分',
                                    '深度学习推动了AI技术的发展',
                                    '神经网络模拟人类大脑的学习过程'
                                ])
                            }
                            st.session_state.random_data = random_data
                            st.session_state.use_random_data = True
                            st.success("🎲 已生成随机测试数据")
                            st.rerun()

                    # with col_buttons:
                    st.write("**验证统计**")
                    
                    # 显示变量统计
                    st.info(f"📊 共需 {len(template_vars)} 个变量")
                    
                    # 显示当前数据类型
                    if st.session_state.get('use_random_data', False):
                        st.success("🎲 当前使用随机数据")
                    else:
                        st.info("🎯 当前使用默认数据")

                    # 显示当前使用的测试值统计
                    if 'last_test_vars' in st.session_state:
                        st.write("**上次验证:**")
                        for var, value in st.session_state.\
                                last_test_vars.items():
                            if isinstance(value, list):
                                st.write(f"• {var}: {len(value)} 项")
                            else:
                                st.write(f"• {var}: "
                                        f"{len(str(value))} 字符")
                else:
                    st.info("✨ 此Agent无需模板变量，可直接使用")

            with col_preview:
                st.subheader("🔍 渲染预览")

                if 'validation_result' in st.session_state:
                    result = st.session_state.validation_result

                    # 验证状态指示
                    if result.get('valid'):
                        st.success("✅ 验证通过")
                    else:
                        st.error("❌ 验证失败")

                    # 显示详细信息
                    col_stats1, col_stats2 = st.columns(2)

                    with col_stats1:
                        missing = result.get('missing_variables', [])
                        if missing:
                            st.error(f"**缺失变量**: {len(missing)}")
                            for var in missing:
                                st.write(f"• {var}")
                        else:
                            st.success("**变量完整**: 无缺失")

                    with col_stats2:
                        extra = result.get('extra_variables', [])
                        if extra:
                            st.warning(f"**多余变量**: {len(extra)}")
                            for var in extra:
                                st.write(f"• {var}")
                        else:
                            st.success("**变量准确**: 无多余")

                    # 显示渲染结果
                    if result.get('rendered_preview'):
                        st.markdown("**渲染结果**:")
                        preview_text = result['rendered_preview']

                        # 显示渲染统计
                        lines_count = len(preview_text.split('\n'))
                        chars_count = len(preview_text)
                        st.caption(f"📊 {lines_count} 行, {chars_count} 字符")

                        # 渲染结果文本框
                        st.text_area("完整渲染内容:",
                                     value=preview_text,
                                     height=500,
                                     disabled=True,
                                     label_visibility="collapsed")

                        # 提供复制按钮功能提示
                        st.caption("💡 提示: 可以从上方文本框复制渲染结果")
                    else:
                        st.info("模板验证失败，无法生成预览")

                    # 显示错误信息
                    if result.get('error'):
                        st.error(f"**错误**: {result['error']}")

                else:
                    st.info("🚀 进行模板验证后将显示预览结果")

                    # 显示说明信息
                    st.markdown("""
                    **验证说明**:
                    - ✅ **验证通过**: 所有变量都已正确提供
                    - ❌ **验证失败**: 存在缺失或多余变量
                    - 📄 **渲染预览**: 显示模板的最终输出效果
                    - 📊 **统计信息**: 显示内容行数和字符数
                    """)

                # 快速测试提示
                if template_vars and 'validation_result' not in st.session_state:
                    st.info("💡 左侧已自动填入测试值，点击'验证'按钮开始测试")
    else:
        st.error("无法获取Agent名称列表，请检查API连接")


# 底部信息
st.markdown("---")
st.markdown("🤖 **Agent Runtime Playground** | 用于测试和验证 Agent Runtime API 功能")
