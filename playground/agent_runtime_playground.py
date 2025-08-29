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
tabs = st.tabs(["⚙️ LLM配置", "🏆 Reward API", "↩️ Backward API", "📊 OSPA 表格", "🤖 Agent管理"])

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

# ==================== OSPA 表格页面（重点优化） ====================
with tabs[3]:
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
with tabs[4]:
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
