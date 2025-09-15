"""
表单组件
提供各种API测试表单
"""
import streamlit as st
import pandas as pd
import time
from typing import Dict, List, Any, Optional, Tuple, Union
from components.common import FormHelpers, DataPreview


class RewardTestForm:
    """Reward API测试表单"""
    
    @staticmethod
    def render(examples: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """渲染Reward测试表单"""
        st.markdown("**功能说明**: 比较多个候选答案与目标答案的语义一致性")
        
        # 示例选择
        example_choice = st.selectbox(
            "选择测试示例",
            list(examples.keys()),
            key="reward_example"
        )
        example = examples[example_choice]
        
        # 基本输入
        question = st.text_area(
            "问题",
            value=example.get("question", ""),
            help="需要进行语义比较的问题"
        )
        
        target_answer = st.text_area(
            "目标答案",
            value=example.get("target_answer", ""),
            help="用于比较的标准答案"
        )
        
        # 候选答案处理
        candidates = RewardTestForm._handle_candidates(example)
        
        # 提交按钮
        if st.button("🚀 执行 Reward 测试", type="primary", key="run_reward"):
            if not question.strip():
                st.error("请输入问题")
                return None
            elif len(candidates) < 1:
                st.error("请至少输入1个候选答案")
                return None
            elif not target_answer.strip():
                st.error("请输入目标答案")
                return None
            else:
                return {
                    "question": question,
                    "candidates": candidates,
                    "target_answer": target_answer
                }
        
        return None
    
    @staticmethod
    def _handle_candidates(example: Dict[str, Any]) -> List[str]:
        """处理候选答案输入"""
        st.subheader("候选答案")
        candidates = []
        
        if example.get("candidates"):
            # 使用示例数据
            candidates = example["candidates"]
            for i, candidate in enumerate(candidates):
                st.text_area(
                    f"候选答案 {i+1}",
                    value=candidate,
                    disabled=True,
                    key=f"candidate_{i}"
                )
        else:
            # 动态输入
            if 'num_candidates' not in st.session_state:
                st.session_state.num_candidates = 1
            
            col_a, col_b = st.columns([1, 4])
            with col_a:
                num_candidates = st.number_input(
                    "候选答案数量",
                    min_value=1,
                    max_value=10,
                    value=st.session_state.num_candidates
                )
                if num_candidates != st.session_state.num_candidates:
                    st.session_state.num_candidates = num_candidates
                    st.rerun()
            
            for i in range(num_candidates):
                candidate = st.text_area(
                    f"候选答案 {i+1}",
                    key=f"custom_candidate_{i}"
                )
                if candidate.strip():
                    candidates.append(candidate.strip())
        
        return candidates


class BackwardTestForm:
    """Backward API测试表单"""
    
    @staticmethod
    def render(examples: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """渲染Backward测试表单"""
        st.markdown("**功能说明**: 将问答对聚合成有意义的章节结构，并生成辅助提示词")
        
        # 示例选择
        example_choice = st.selectbox(
            "选择测试示例",
            list(examples.keys()),
            key="backward_example"
        )
        example = examples[example_choice]
        
        # 问答对处理
        qas = BackwardTestForm._handle_qas(example)
        
        # 现有章节结构
        chapter_structure = BackwardTestForm._handle_chapter_structure(example)
        
        # 处理参数
        st.subheader("🎯 处理参数")
        col1, col2 = st.columns(2)
        
        with col1:
            max_level = st.number_input(
                "最大章节层级",
                min_value=1,
                max_value=5,
                value=example.get("max_level", 3),
                help="章节结构的最大层级深度"
            )
        
        with col2:
            max_concurrent_llm = st.number_input(
                "最大并发LLM数量",
                min_value=1,
                max_value=20,
                value=example.get("max_concurrent_llm", 10),
                help="同时进行的LLM调用数量"
            )
        
        # 提交按钮
        if st.button("🚀 执行 Backward 处理", type="primary", key="run_backward"):
            if not qas:
                st.error("请输入至少一个问答对")
                return None
            else:
                return {
                    "qas": qas,
                    "chapter_structure": chapter_structure,
                    "max_level": max_level,
                    "max_concurrent_llm": max_concurrent_llm
                }
        
        return None
    
    @staticmethod
    def _handle_qas(example: Dict[str, Any]) -> List[Dict[str, str]]:
        """处理问答对输入"""
        st.subheader("📝 问答对输入")
        
        # CSV文件上传
        uploaded_file = FormHelpers.render_file_uploader_with_example(
            "上传CSV文件 (可选)",
            ['csv'],
            "CSV文件应包含 'q' 和 'a' 列"
        )
        
        qas = []
        
        if uploaded_file is not None:
            qas = BackwardTestForm._process_csv_file(uploaded_file)
        elif example.get("qas"):
            qas = example["qas"]
            st.info(f"使用示例数据: {len(qas)} 个问答对")
            BackwardTestForm._show_qas_preview(qas)
        else:
            qas = BackwardTestForm._handle_manual_input()
        
        return qas
    
    @staticmethod
    def _process_csv_file(uploaded_file) -> List[Dict[str, str]]:
        """处理CSV文件"""
        try:
            df = pd.read_csv(uploaded_file)
            if 'q' in df.columns and 'a' in df.columns:
                qas = [
                    {"q": row['q'], "a": row['a']}
                    for _, row in df.iterrows()
                    if pd.notna(row['q']) and pd.notna(row['a'])
                ]
                st.success(f"✅ 成功从CSV加载 {len(qas)} 个问答对")
                DataPreview.show_dataframe_preview(df[['q', 'a']])
                return qas
            else:
                st.error("CSV文件必须包含 'q' 和 'a' 列")
                return []
        except Exception as e:
            st.error(f"CSV文件读取失败: {e}")
            return []
    
    @staticmethod
    def _show_qas_preview(qas: List[Dict[str, str]], max_show: int = 5):
        """显示问答对预览"""
        for i, qa in enumerate(qas[:max_show]):
            with st.expander(f"问答对 {i+1}"):
                st.write(f"**问题**: {qa['q']}")
                st.write(f"**答案**: {qa['a']}")
        
        if len(qas) > max_show:
            st.write(f"... 还有 {len(qas)-max_show} 个问答对")
    
    @staticmethod
    def _handle_manual_input() -> List[Dict[str, str]]:
        """处理手动输入"""
        if 'num_qas' not in st.session_state:
            st.session_state.num_qas = 3
        
        num_qas = st.number_input(
            "问答对数量",
            min_value=1,
            max_value=20,
            value=st.session_state.num_qas
        )
        
        if num_qas != st.session_state.num_qas:
            st.session_state.num_qas = num_qas
            st.rerun()
        
        qas = []
        for i in range(num_qas):
            with st.expander(f"问答对 {i+1}"):
                q = st.text_area(f"问题 {i+1}", key=f"q_{i}")
                a = st.text_area(f"答案 {i+1}", key=f"a_{i}")
                if q.strip() and a.strip():
                    qas.append({"q": q.strip(), "a": a.strip()})
        
        return qas

    @staticmethod
    def _handle_chapter_structure(example: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """处理现有章节目录"""
        st.subheader("🗂️ 现有章节目录 (可选)")
        
        use_existing_chapter = st.checkbox(
            "使用现有章节目录",
            value=example.get("chapter_structure") is not None
        )
        
        if not use_existing_chapter:
            return None
        
        # 输入方式选择
        chapter_input_method = st.radio(
            "章节目录输入方式",
            ["使用示例数据", "上传JSON文件", "手动编辑JSON"],
            key="backward_chapter_input_method",
            horizontal=True
        )
        
        if chapter_input_method == "使用示例数据":
            if example.get("chapter_structure"):
                st.success("✅ 使用示例章节目录")
                with st.expander("📋 示例章节结构预览"):
                    st.json(example["chapter_structure"])
                return example["chapter_structure"]
            else:
                st.info("当前示例无章节目录数据")
                return None
        elif chapter_input_method == "上传JSON文件":
            uploaded_structure_file = st.file_uploader(
                "上传章节结构JSON文件",
                type=['json'],
                help="上传之前导出的章节结构JSON文件",
                key="backward_upload_chapter_structure"
            )
            
            if uploaded_structure_file is not None:
                try:
                    import json
                    structure_content = uploaded_structure_file.read().decode('utf-8')
                    imported_structure = json.loads(structure_content)
                    
                    if isinstance(imported_structure, dict) and "nodes" in imported_structure:
                        nodes_count = len(imported_structure.get("nodes", {}))
                        st.success(f"✅ 成功导入章节结构，包含 {nodes_count} 个章节")
                        
                        with st.expander("📋 导入的章节结构预览"):
                            st.json(imported_structure)
                        
                        return imported_structure
                    else:
                        st.error("❌ JSON文件格式不正确，缺少必要的'nodes'字段")
                        return None
                except Exception as e:
                    st.error(f"❌ 文件处理失败: {str(e)}")
                    return None
            return None
        else:  # 手动编辑JSON
            # 默认结构模板
            default_structure = {
                "nodes": {
                    "chapter_1": {
                        "id": "chapter_1",
                        "title": "基础知识",
                        "level": 1,
                        "parent_id": None,
                        "children": [],
                        "description": "基础概念和原理",
                        "related_qa_items": [],
                        "chapter_number": "1."
                    }
                },
                "root_ids": ["chapter_1"],
                "max_level": 3
            }
            
            if 'backward_manual_chapter_structure' not in st.session_state:
                import json
                st.session_state.backward_manual_chapter_structure = json.dumps(
                    default_structure, ensure_ascii=False, indent=2
                )
            
            edited_structure_text = st.text_area(
                "编辑章节结构JSON",
                value=st.session_state.backward_manual_chapter_structure,
                height=300,
                key="backward_manual_structure_editor",
                help="编辑章节结构的JSON格式数据"
            )
            
            col_validate, col_reset = st.columns([1, 1])
            
            with col_validate:
                if st.button("✅ 验证并应用", key="backward_validate_manual_structure"):
                    try:
                        import json
                        parsed_structure = json.loads(edited_structure_text)
                        
                        if isinstance(parsed_structure, dict) and "nodes" in parsed_structure:
                            st.session_state.backward_manual_chapter_structure = edited_structure_text
                            nodes_count = len(parsed_structure.get("nodes", {}))
                            st.success(f"✅ 章节结构验证成功，包含 {nodes_count} 个章节")
                            return parsed_structure
                        else:
                            st.error("❌ JSON结构不正确，需要包含'nodes'字段")
                            return None
                    except Exception as e:
                        st.error(f"❌ JSON格式错误: {str(e)}")
                        return None
            
            with col_reset:
                if st.button("🔄 重置为默认", key="backward_reset_manual_structure"):
                    import json
                    st.session_state.backward_manual_chapter_structure = json.dumps(
                        default_structure, ensure_ascii=False, indent=2
                    )
                    st.rerun()
            
            return None


class BQAExtractTestForm:
    """BQA Extract API测试表单 - 多轮对话解耦"""

    @staticmethod
    def render(examples: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """渲染BQA Extract测试表单"""
        st.markdown("**功能说明**: 将多轮对话拆解为独立的背景-问题-答案格式，确保每个内容都可以独立理解")

        # 示例选择
        example_choice = st.selectbox(
            "选择测试示例",
            list(examples.keys()),
            key="bqa_extract_example"
        )
        example = examples[example_choice]

        # 对话会话处理
        qa_lists = BQAExtractTestForm._handle_qa_lists(example)

        # 处理参数
        st.subheader("🎯 处理参数")
        col1, col2 = st.columns(2)

        with col1:
            context_extraction_mode = st.selectbox(
                "背景提取模式",
                ["auto", "minimal", "detailed"],
                index=["auto", "minimal", "detailed"].index(example.get("context_extraction_mode", "auto")),
                help="auto: 智能判断；minimal: 最小化；detailed: 详细模式"
            )

        with col2:
            max_concurrent_processing = st.number_input(
                "最大并发处理数量",
                min_value=1,
                max_value=10,
                value=example.get("max_concurrent_processing", 3),
                help="同时处理的会话数量"
            )

        # 高级选项
        with st.expander("🔧 高级选项"):
            preserve_session_info = st.checkbox(
                "保留会话信息",
                value=example.get("preserve_session_info", True),
                help="是否在输出中保留原始会话ID等信息"
            )

        # 提交按钮
        if st.button("🚀 执行 BQA Extract 处理", type="primary", key="run_bqa_extract"):
            if not qa_lists or all(len(qa_list) == 0 for qa_list in qa_lists):
                st.error("请输入至少一个会话的问答对")
                return None
            else:
                return {
                    "qa_lists": qa_lists,
                    "context_extraction_mode": context_extraction_mode,
                    "preserve_session_info": preserve_session_info,
                    "max_concurrent_processing": max_concurrent_processing
                }

        return None

    @staticmethod
    def _handle_qa_lists(example: Dict[str, Any]) -> List[List[Dict[str, str]]]:
        """处理多个对话会话的问答对输入"""
        st.subheader("💬 多轮对话会话")

        # 输入方式选择
        input_method = st.radio(
            "输入方式",
            ["使用示例数据", "手动输入", "CSV文件上传"],
            key="bqa_extract_input_method",
            horizontal=True
        )

        qa_lists = []

        if input_method == "使用示例数据":
            if example.get("qa_lists"):
                qa_lists = example["qa_lists"]
                st.info(f"使用示例数据: {len(qa_lists)} 个对话会话")
                BQAExtractTestForm._show_qa_lists_preview(qa_lists)
            else:
                st.info("当前示例无对话数据")

        elif input_method == "手动输入":
            qa_lists = BQAExtractTestForm._handle_manual_sessions()

        elif input_method == "CSV文件上传":
            uploaded_file = st.file_uploader(
                "上传CSV文件",
                type=['csv'],
                help="CSV文件应包含 'session_id', 'q', 'a' 列",
                key="bqa_extract_csv"
            )

            if uploaded_file is not None:
                qa_lists = BQAExtractTestForm._process_sessions_csv(uploaded_file)

        return qa_lists

    @staticmethod
    def _show_qa_lists_preview(qa_lists: List[List[Dict[str, str]]], max_show: int = 3):
        """显示多个会话的预览"""
        for i, qa_list in enumerate(qa_lists[:max_show]):
            with st.expander(f"会话 {i+1} - {len(qa_list)} 个问答对"):
                for j, qa in enumerate(qa_list[:3]):
                    st.write(f"**Q{j+1}**: {qa.get('q', qa.get('question', ''))}")
                    st.write(f"**A{j+1}**: {qa.get('a', qa.get('answer', ''))}")
                    if j < len(qa_list) - 1:
                        st.markdown("---")
                if len(qa_list) > 3:
                    st.write(f"... 还有 {len(qa_list)-3} 个问答对")

        if len(qa_lists) > max_show:
            st.write(f"... 还有 {len(qa_lists)-max_show} 个对话会话")

    @staticmethod
    def _handle_manual_sessions() -> List[List[Dict[str, str]]]:
        """处理手动输入的对话会话"""
        if 'num_sessions' not in st.session_state:
            st.session_state.num_sessions = 2

        num_sessions = st.number_input(
            "对话会话数量",
            min_value=1,
            max_value=5,
            value=st.session_state.num_sessions,
            key="bqa_extract_num_sessions"
        )

        if num_sessions != st.session_state.num_sessions:
            st.session_state.num_sessions = num_sessions
            st.rerun()

        qa_lists = []
        for session_idx in range(num_sessions):
            with st.expander(f"📋 会话 {session_idx+1}"):
                # 每个会话的问答对数量
                session_key = f"session_{session_idx}_num_qas"
                if session_key not in st.session_state:
                    st.session_state[session_key] = 3

                num_qas = st.number_input(
                    f"会话 {session_idx+1} 问答对数量",
                    min_value=1,
                    max_value=10,
                    value=st.session_state[session_key],
                    key=f"num_qas_session_{session_idx}"
                )

                if num_qas != st.session_state[session_key]:
                    st.session_state[session_key] = num_qas
                    st.rerun()

                session_qas = []
                for qa_idx in range(num_qas):
                    col_q, col_a = st.columns(2)
                    with col_q:
                        q = st.text_area(
                            f"问题 {qa_idx+1}",
                            key=f"q_s{session_idx}_qa{qa_idx}",
                            height=80
                        )
                    with col_a:
                        a = st.text_area(
                            f"答案 {qa_idx+1}",
                            key=f"a_s{session_idx}_qa{qa_idx}",
                            height=80
                        )

                    if q.strip() and a.strip():
                        session_qas.append({"q": q.strip(), "a": a.strip()})

                if session_qas:
                    qa_lists.append(session_qas)

        return qa_lists

    @staticmethod
    def _process_sessions_csv(uploaded_file) -> List[List[Dict[str, str]]]:
        """处理包含多个会话的CSV文件"""
        try:
            df = pd.read_csv(uploaded_file)
            required_cols = ['session_id', 'q', 'a']

            if not all(col in df.columns for col in required_cols):
                st.error(f"CSV文件必须包含以下列: {', '.join(required_cols)}")
                return []

            # 按会话ID分组
            sessions = {}
            for _, row in df.iterrows():
                if pd.notna(row['session_id']) and pd.notna(row['q']) and pd.notna(row['a']):
                    session_id = str(row['session_id'])
                    if session_id not in sessions:
                        sessions[session_id] = []
                    sessions[session_id].append({
                        "q": str(row['q']),
                        "a": str(row['a'])
                    })

            qa_lists = list(sessions.values())
            total_qas = sum(len(qa_list) for qa_list in qa_lists)

            st.success(f"✅ 成功从CSV加载 {len(qa_lists)} 个会话，共 {total_qas} 个问答对")

            # 显示预览
            preview_data = []
            for session_id, qa_list in list(sessions.items())[:3]:
                for i, qa in enumerate(qa_list[:2]):
                    preview_data.append({
                        "会话ID": session_id,
                        "问题": qa['q'][:50] + ("..." if len(qa['q']) > 50 else ""),
                        "答案": qa['a'][:50] + ("..." if len(qa['a']) > 50 else "")
                    })

            if preview_data:
                st.write("**数据预览:**")
                st.dataframe(pd.DataFrame(preview_data), use_container_width=True)

            return qa_lists

        except Exception as e:
            st.error(f"CSV文件处理失败: {e}")
            return []


class ConfigForm:
    """配置表单"""
    
    @staticmethod
    def render_llm_config() -> Optional[Dict[str, Any]]:
        """渲染LLM配置表单"""
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
                "timeout": 600.0,
                "max_completion_tokens": 4096,
                "temperature": 0.0
            },
            "自定义配置": {}
        }
        
        template_choice = st.selectbox("选择配置模板", list(templates.keys()))
        template = templates[template_choice]
        
        # 配置表单
        with st.form("config_form"):
            api_key = st.text_input(
                "API Key",
                value=template.get("api_key", ""),
                type="password"
            )
            model = st.text_input("模型名称", value=template.get("model", ""))
            base_url = st.text_input("Base URL", value=template.get("base_url", ""))
            timeout = st.number_input(
                "超时时间 (秒)",
                value=template.get("timeout", 120.0),
                min_value=1.0
            )
            max_tokens = st.number_input(
                "最大令牌数",
                value=template.get("max_completion_tokens", 2048),
                min_value=1
            )
            temperature = st.number_input(
                "温度",
                value=template.get("temperature", 0.0),
                min_value=0.0,
                max_value=2.0,
                step=0.1
            )
            
            if st.form_submit_button("💾 保存配置", type="primary"):
                return {
                    "api_key": api_key,
                    "model": model,
                    "base_url": base_url,
                    "timeout": timeout,
                    "max_completion_tokens": max_tokens,
                    "temperature": temperature
                }
        
        return None