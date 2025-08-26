"""
重构后的 Agent Runtime API Playground
使用模块化架构，重点优化OSPA表格功能
"""
import os
import streamlit as st
import requests
import pandas as pd
import time
from typing import Dict, Any

# 导入新的模块
from ospa_models import OSPAManager, OSPAItem
from api_services import ServiceManager
from ospa_utils import OSPADataLoader, OSPAProcessor, StreamlitUtils

# 页面配置
st.title("🤖 Agent Runtime API Playground")

# 全局配置
DEFAULT_API_URL = "http://localhost:8011"

# 初始化会话状态
if 'ospa_manager' not in st.session_state:
    st.session_state.ospa_manager = OSPAManager()
if 'service_manager' not in st.session_state:
    st.session_state.service_manager = None
if 'processor' not in st.session_state:
    st.session_state.processor = None

# API URL 配置
api_url = st.text_input(
    "Agent Runtime API URL",
    value=os.getenv("AGENT_RUNTIME_API_URL", DEFAULT_API_URL),
    key="api_url_input",
    help="Agent Runtime API 的基础URL"
)

# 更新服务管理器
if (st.session_state.service_manager is None or
    st.session_state.service_manager.base_url != api_url):
    st.session_state.service_manager = ServiceManager(api_url)
    st.session_state.processor = OSPAProcessor(st.session_state.service_manager)

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

# 创建选项卡
tabs = st.tabs(["⚙️ LLM配置", "🏆 Reward API", "↩️ Backward API", "📊 OSPA 表格"])

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
                                        value=template.get("max_completion_tokens", 2048),
                                        min_value=1)
            temperature = st.number_input("温度",
                                         value=template.get("temperature", 0.0),
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
                    result = service_manager.config_service.update_config(config_data)
                    st.success("✅ 配置更新成功！")
                    st.json(result)
                    # 更新会话状态
                    st.session_state.current_config = result.get("config", config_data)
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
                "question": "请总结《西游记》中唐僧西天取经的目的。",
                "candidates": [
                    "唐僧带领孙悟空、猪八戒、沙僧历经九九八十一难前往西天取经，为了取得真经。",
                    "唐僧此行是因为皇帝派遣他寻找宝物。",
                    "取经的最终目的，是为了获取佛经，弘扬佛法，普度众生。",
                    "唐僧和徒弟们一路降妖除魔，实际上是为了打败妖怪获得宝藏。",
                    "这个故事主要讲述了团队合作、修行和坚持不懈的精神。"
                ],
                "target_answer": "唐僧此次取经的真正目的，是为了弘扬佛法，普度众生。"
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
                        response = requests.post(f"{api_url}/agent/reward",
                                               json=test_data)

                    if response.status_code == 200:
                        result = response.json()
                        st.success("✅ 测试完成！")

                        # 保存到会话状态供右侧显示
                        if 'reward_results' not in st.session_state:
                            st.session_state.reward_results = []
                        st.session_state.reward_results.append({
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "question": question,
                            "result": result
                        })
                    else:
                        st.error(f"测试失败: {response.status_code} - {response.text}")
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
                with st.expander(f"历史记录 ({len(st.session_state.reward_results)-1} 条)"):
                    for i, result in enumerate(reversed(st.session_state.reward_results[:-1])):
                        st.write(f"**{i+1}.** {result['timestamp']}")
                        st.write(f"问题: {result['question'][:30]}...")
                        if st.button(f"查看",
                                   key=f"view_result_{len(st.session_state.reward_results)-i-2}"):
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
            "qas": [
                {"q": "Python如何定义变量？", "a": "在Python中使用赋值语句定义变量，如 x = 10"},
                {"q": "Python如何定义函数？", "a": "使用def关键字定义函数，如 def func_name():"},
                {"q": "什么是Python列表？", "a": "列表是Python中的可变序列，使用[]定义"}
            ],
            "chapters_extra_instructions": "请将Python相关的问题聚合到一个章节",
            "gen_p_extra_instructions": "生成专业的Python技术文档风格提示词"
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
                    qas = [{"q": row['q'], "a": row['a']}
                          for _, row in df.iterrows()
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

        gen_p_extra_instructions = st.text_area(
            "2. 提示词生成额外指令(选填)",
            value=backward_example.get("gen_p_extra_instructions", ""),
            help="指导如何生成提示词的额外说明")

        # 提交测试
        if st.button("🚀 执行 Backward 处理", type="primary", key="run_backward"):
            if not qas:
                st.error("请输入至少一个问答对")
            else:
                try:
                    with st.spinner("正在执行问答对聚合处理..."):
                        result = service_manager.backward_service.process_qas(
                            qas, chapters_extra_instructions, gen_p_extra_instructions)

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

        # 选择数据源
        data_source = st.radio("数据源选择", ["上传 CSV 文件", "使用示例数据", "手动输入"],
                               key="ospa_data_source")

        if data_source == "上传 CSV 文件":
            uploaded_file = st.file_uploader("选择 OSPA CSV 文件",
                                             type=['csv'],
                                             help="CSV文件应包含观察(O)和行动(A)等必要列")

            if uploaded_file is not None:
                try:
                    new_manager = OSPADataLoader.load_from_csv_file(
                        uploaded_file)
                    st.session_state.ospa_manager = new_manager
                    ospa_manager = new_manager

                    st.success(f"✅ 成功加载 {len(ospa_manager.items)} 条 OSPA 数据")

                    # 显示数据统计
                    StreamlitUtils.show_statistics(ospa_manager)

                except Exception as e:
                    st.error(f"文件读取失败: {str(e)}")

        elif data_source == "使用示例数据":
            # 使用示例数据
            example_files = {
                "示例1 (exp1.csv)": "ospa/exp1.csv",
                "示例2 (exp2.csv)": "ospa/exp2.csv",
                "示例3 (exp3.csv)": "ospa/exp3.csv"
            }

            selected_example = st.selectbox("选择示例文件",
                                            list(example_files.keys()))

            if st.button("📥 加载示例数据", key="load_example"):
                try:
                    example_file = example_files[selected_example]
                    new_manager = OSPADataLoader.load_from_example_file(
                        example_file)
                    st.session_state.ospa_manager = new_manager
                    ospa_manager = new_manager

                    st.success(f"✅ 成功加载 {len(ospa_manager.items)} 条示例数据")

                    # 显示数据统计
                    StreamlitUtils.show_statistics(ospa_manager)

                except Exception as e:
                    st.error(f"示例数据加载失败: {str(e)}")

        elif data_source == "手动输入":
            if 'manual_ospa_count' not in st.session_state:
                st.session_state.manual_ospa_count = 3

            num_entries = st.number_input(
                "OSPA 条目数量",
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
                    ospa_manager.items = manual_items
                    st.success(f"✅ 成功保存 {len(manual_items)} 条 OSPA 数据")

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
                    else:
                        st.error(f"❌ {result['error']}")
                        st.session_state.backward_generation_result = result

            with col_d:
                if st.button("🔄 清空状态提示词", type="secondary"):
                    ospa_manager.clear_field('S')
                    ospa_manager.clear_field('p')
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
                    else:
                        st.error(f"❌ {result['error']}")
                        st.session_state.answer_generation_result = result

            with col_f:
                if st.button("🔄 清空生成答案", type="secondary"):
                    ospa_manager.clear_field('A_prime')
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

# 底部信息
st.markdown("---")
st.markdown("🤖 **Agent Runtime Playground** | 用于测试和验证 Agent Runtime API 功能")
