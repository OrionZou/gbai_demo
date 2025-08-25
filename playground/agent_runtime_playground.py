import os
import streamlit as st
import requests
import pandas as pd
import json
from typing import List, Dict, Any
import time

# 页面标题
st.title("🤖 Agent Runtime API Playground")

# 全局配置
DEFAULT_API_URL = "http://localhost:8011"

# API URL 配置
api_url = st.text_input("Agent Runtime API URL",
                        value=os.getenv("AGENT_RUNTIME_API_URL",
                                        DEFAULT_API_URL),
                        key="api_url_input",
                        help="Agent Runtime API 的基础URL")


# 检查 API 连接状态
def check_api_connection(url: str) -> bool:
    """检查 API 连接状态"""
    try:
        response = requests.get(f"{url}/docs", timeout=5)
        return response.status_code == 200
    except:
        return False


# 显示连接状态
col1, col2 = st.columns([3, 1])
with col1:
    if check_api_connection(api_url):
        st.success("✅ API 连接正常")
    else:
        st.error("❌ API 连接失败，请检查 URL 或启动 Agent Runtime 服务")

with col2:
    if st.button("🔄 重新检查", help="重新检查 API 连接状态"):
        st.rerun()

# 创建选项卡
tabs = st.tabs(["⚙️ LLM配置", "🏆 Reward API", "↩️ Backward API"])

# ==================== LLM 配置页面 ====================
with tabs[0]:
    st.header("🔧 LLM 配置管理")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📋 当前配置")

        if st.button("📥 获取当前配置", key="get_config"):
            try:
                response = requests.get(f"{api_url}/agent/config")
                if response.status_code == 200:
                    config = response.json()
                    st.session_state.current_config = config
                    st.success("配置获取成功！")
                    st.json(config)
                else:
                    st.error(
                        f"获取配置失败: {response.status_code} - {response.text}")
            except Exception as e:
                st.error(f"请求失败: {e}")

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
                    response = requests.post(f"{api_url}/agent/config",
                                             json=config_data)
                    if response.status_code == 200:
                        result = response.json()
                        st.success("✅ 配置更新成功！")
                        st.json(result)
                        # 更新会话状态
                        st.session_state.current_config = result.get(
                            "config", config_data)
                    else:
                        st.error(
                            f"配置更新失败: {response.status_code} - {response.text}"
                        )
                except Exception as e:
                    st.error(f"请求失败: {e}")

# ==================== Reward API 页面 ====================
with tabs[1]:
    st.header("🏆 Reward API 测试")

    st.markdown("**功能说明**: 比较多个候选答案与目标答案的语义一致性")

    col1, col2 = st.columns([2, 1])

    with col1:
        # 预设示例
        examples = {
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
            },
            "自定义输入": {}
        }

        example_choice = st.selectbox("选择测试示例",
                                      list(examples.keys()),
                                      key="reward_example")
        example = examples[example_choice]

        # 输入表单
        question = st.text_area("问题",
                                value=example.get("question", ""),
                                help="需要进行语义比较的问题")

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

        target_answer = st.text_area("目标答案",
                                     value=example.get("target_answer", ""),
                                     help="用于比较的标准答案")

        # 提交测试
        if st.button("🚀 执行 Reward 测试", type="primary", key="run_reward"):
            if not question.strip():
                st.error("请输入问题")
            elif len(candidates) < 2:
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
        },
        "综合示例 - 多技术栈": {
            "qas": [{
                "q": "Python如何定义变量？",
                "a": "在Python中使用赋值语句定义变量"
            }, {
                "q": "什么是RESTful API？",
                "a": "RESTful API是遵循REST架构风格的Web服务接口"
            }, {
                "q": "什么是数据库索引？",
                "a": "索引是提高数据库查询效率的数据结构"
            }, {
                "q": "什么是时间复杂度？",
                "a": "时间复杂度描述算法执行时间与输入规模的关系"
            }, {
                "q": "什么是版本控制？",
                "a": "版本控制是管理代码变更历史的系统"
            }],
            "chapters_extra_instructions":
            "按技术领域分类，每个章节包含2-3个相关问答",
            "gen_p_extra_instructions":
            "为每个技术领域生成专业、准确的技术文档风格提示词"
        },
        "自定义输入": {
            "qas": [],
            "chapters_extra_instructions": "",
            "gen_p_extra_instructions": ""
        }
    }

    backward_example_choice = st.selectbox("选择测试示例",
                                           list(backward_examples.keys()),
                                           key="backward_example")
    backward_example = backward_examples[backward_example_choice]

    col1, col2 = st.columns([3, 2])

    with col1:
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
            "章节聚合额外指令",
            value=backward_example.get("chapters_extra_instructions", ""),
            help="指导如何聚合问答对到章节的额外说明")

        gen_p_extra_instructions = st.text_area("提示词生成额外指令",
                                                value=backward_example.get(
                                                    "gen_p_extra_instructions",
                                                    ""),
                                                help="指导如何生成提示词的额外说明")

        # 提交测试
        if st.button("🚀 执行 Backward 处理", type="primary", key="run_backward"):
            if not qas:
                st.error("请输入至少一个问答对")
            else:
                test_data = {
                    "qas": qas,
                    "chapters_extra_instructions": chapters_extra_instructions,
                    "gen_p_extra_instructions": gen_p_extra_instructions
                }

                try:
                    with st.spinner("正在执行问答对聚合处理..."):
                        response = requests.post(f"{api_url}/agent/backward",
                                                 json=test_data)

                    if response.status_code == 200:
                        result = response.json()
                        st.success("✅ 处理完成！")

                        # 保存结果
                        st.session_state.backward_result = result

                    else:
                        st.error(
                            f"处理失败: {response.status_code} - {response.text}")
                except Exception as e:
                    st.error(f"请求失败: {e}")

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

            # 章节详情
            if result.get("chapters"):
                with st.expander("📑 章节详情", expanded=True):
                    for chapter_name, chapter_data in result["chapters"].items(
                    ):
                        st.write(f"**{chapter_name}**")
                        if hasattr(chapter_data, 'qas') or isinstance(
                                chapter_data, dict) and 'qas' in chapter_data:
                            qas_count = len(
                                chapter_data.get('qas', []) if isinstance(
                                    chapter_data, dict
                                ) else getattr(chapter_data, 'qas', []))
                            st.write(f"- 包含 {qas_count} 个问答对")

            # OSPA 数据
            if result.get("ospa"):
                with st.expander("📋 OSPA 数据"):
                    ospa_df = pd.DataFrame([
                        {
                            "O": item.get("o", ""),
                            "S": item.get("s", ""),
                            "p": item.get("p", ""),
                            "A": item.get("a", "")
                        } for item in result["ospa"][:10]  # 只显示前10条
                    ])
                    st.dataframe(ospa_df)

                    if len(result["ospa"]) > 10:
                        st.write(f"... 还有 {len(result['ospa'])-10} 条 OSPA 数据")

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

# 底部信息
st.markdown("---")
st.markdown("🤖 **Agent Runtime Playground** | 用于测试和验证 Agent Runtime API 功能")
