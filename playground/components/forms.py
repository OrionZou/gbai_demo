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
        
        # 额外指令
        st.subheader("🎯 处理指令")
        chapters_extra_instructions = st.text_area(
            "1. 章节聚合额外指令(选填)",
            value=example.get("chapters_extra_instructions", ""),
            help="指导如何聚合问答对到章节的额外说明"
        )
        
        gen_p_extra_instructions = st.text_area(
            "2. 提示词生成额外指令(选填)",
            value=example.get("gen_p_extra_instructions", ""),
            help="指导如何生成提示词的额外说明"
        )
        
        # 提交按钮
        if st.button("🚀 执行 Backward 处理", type="primary", key="run_backward"):
            if not qas:
                st.error("请输入至少一个问答对")
                return None
            else:
                return {
                    "qas": qas,
                    "chapters_extra_instructions": chapters_extra_instructions,
                    "gen_p_extra_instructions": gen_p_extra_instructions
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


class BackwardV2TestForm:
    """Backward V2 API测试表单"""
    
    @staticmethod
    def render(examples: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """渲染Backward V2测试表单"""
        st.markdown("**功能说明**: 改进版知识反向处理，支持多轮对话和现有章节目录更新")
        
        # 示例选择
        example_choice = st.selectbox(
            "选择测试示例",
            list(examples.keys()),
            key="backward_v2_example"
        )
        example = examples[example_choice]
        
        # 多轮对话输入
        qa_lists = BackwardV2TestForm._handle_qa_lists(example)
        
        # 现有章节目录输入
        chapter_structure = BackwardV2TestForm._handle_chapter_structure(example)
        
        # 处理参数
        st.subheader("🎯 处理参数")
        max_level = st.number_input(
            "最大章节层级",
            min_value=1,
            max_value=5,
            value=example.get("max_level", 3)
        )
        
        # 提交按钮
        if st.button("🚀 执行 Backward V2 处理", type="primary", key="run_backward_v2"):
            if not qa_lists:
                st.error("请输入至少一个对话序列")
                return None
            else:
                request_data = {
                    "qa_lists": qa_lists,
                    "max_level": max_level
                }
                if chapter_structure:
                    request_data["chapter_structure"] = chapter_structure
                return request_data
        
        return None
    
    @staticmethod
    def _handle_qa_lists(example: Dict[str, Any]) -> List[Dict[str, Any]]:
        """处理多轮对话输入"""
        st.subheader("📝 多轮对话输入 (Q&A 二维列表)")
        
        # CSV格式说明
        BackwardV2TestForm._show_csv_format_help()
        
        # CSV文件上传
        uploaded_file = BackwardV2TestForm._render_csv_uploader()
        
        qa_lists = []
        
        if uploaded_file is not None:
            qa_lists = BackwardV2TestForm._process_csv_file(uploaded_file)
        elif example.get("qa_lists"):
            qa_lists = example["qa_lists"]
            st.info(f"使用示例数据: {len(qa_lists)} 个对话序列")
            BackwardV2TestForm._show_qa_lists_preview(qa_lists)
        else:
            qa_lists = BackwardV2TestForm._handle_manual_sessions()
        
        return qa_lists
    
    @staticmethod
    def _show_csv_format_help():
        """显示CSV格式帮助"""
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
            """)
    
    @staticmethod
    def _render_csv_uploader():
        """渲染CSV上传器"""
        col1, col2 = st.columns([3, 1])
        
        with col1:
            uploaded_file = st.file_uploader(
                "上传CSV文件 (可选)",
                type=['csv'],
                help="请确保CSV包含必需的列: session_id, question, answer",
                key="backward_v2_csv"
            )
        
        with col2:
            # 提供示例CSV下载
            BackwardV2TestForm._render_example_download()
        
        return uploaded_file
    
    @staticmethod
    def _render_example_download():
        """渲染示例下载"""
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
            # 备用示例
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
    
    @staticmethod
    def _process_csv_file(uploaded_file) -> List[Dict[str, Any]]:
        """处理CSV文件"""
        try:
            file_size = uploaded_file.size
            if file_size > 10 * 1024 * 1024:  # 10MB限制
                st.error("❌ CSV文件过大，请上传小于10MB的文件")
                return []
            elif file_size == 0:
                st.error("❌ 上传的文件为空")
                return []
            
            df = pd.read_csv(uploaded_file)
            
            # 格式验证
            required_cols = ['session_id', 'question', 'answer']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                st.error(f"❌ CSV文件缺少必需的列: {', '.join(missing_cols)}")
                st.write("**现有列:**", list(df.columns))
                return []
            
            # 数据处理
            qa_lists = BackwardV2TestForm._convert_df_to_qa_lists(df)
            
            if qa_lists:
                st.success(f"✅ 成功从CSV加载 {len(qa_lists)} 个对话序列")
                BackwardV2TestForm._show_csv_quality_report(df, qa_lists)
            
            return qa_lists
            
        except Exception as e:
            st.error(f"❌ CSV文件处理失败: {str(e)}")
            return []
    
    @staticmethod
    def _convert_df_to_qa_lists(df: pd.DataFrame) -> List[Dict[str, Any]]:
        """转换DataFrame为qa_lists格式"""
        sessions = {}
        valid_rows = 0
        
        for _, row in df.iterrows():
            session_id = str(row['session_id']).strip()
            question = str(row['question']).strip()
            answer = str(row['answer']).strip()
            
            if session_id and question and answer:
                valid_rows += 1
                if session_id not in sessions:
                    sessions[session_id] = []
                sessions[session_id].append({
                    "question": question,
                    "answer": answer
                })
        
        return [
            {
                "items": items,
                "session_id": session_id
            }
            for session_id, items in sessions.items()
            if len(items) > 0
        ]
    
    @staticmethod
    def _show_csv_quality_report(df: pd.DataFrame, qa_lists: List[Dict[str, Any]]):
        """显示CSV质量报告"""
        total_rows = len(df)
        valid_rows = sum(len(qa_list['items']) for qa_list in qa_lists)
        skipped_rows = total_rows - valid_rows
        
        if skipped_rows > 0:
            st.warning(f"⚠️ 跳过了 {skipped_rows} 行无效数据（空值或格式错误）")
        
        # 显示预览
        st.write("**📋 数据预览:**")
        for i, qa_list in enumerate(qa_lists[:3]):
            st.write(f"**对话序列 {i+1} (session: {qa_list['session_id']})**: {len(qa_list['items'])} 个问答对")
            if qa_list['items']:
                first_qa = qa_list['items'][0]
                question_preview = first_qa['question'][:50] + "..." if len(first_qa['question']) > 50 else first_qa['question']
                st.write(f"  └─ Q: {question_preview}")
        
        if len(qa_lists) > 3:
            st.write(f"... 还有 {len(qa_lists)-3} 个对话序列")
    
    @staticmethod
    def _show_qa_lists_preview(qa_lists: List[Dict[str, Any]]):
        """显示qa_lists预览"""
        for i, qa_list in enumerate(qa_lists):
            with st.expander(f"对话序列 {i+1} (session: {qa_list['session_id']})"):
                for j, qa in enumerate(qa_list['items'][:3]):
                    st.write(f"**Q{j+1}**: {qa['question']}")
                    st.write(f"**A{j+1}**: {qa['answer']}")
                if len(qa_list['items']) > 3:
                    st.write(f"... 还有 {len(qa_list['items'])-3} 个问答对")
    
    @staticmethod
    def _handle_manual_sessions() -> List[Dict[str, Any]]:
        """处理手动输入的会话"""
        if 'num_sessions' not in st.session_state:
            st.session_state.num_sessions = 2
        
        num_sessions = st.number_input(
            "对话序列数量",
            min_value=1,
            max_value=10,
            value=st.session_state.num_sessions,
            key="backward_v2_sessions"
        )
        
        if num_sessions != st.session_state.num_sessions:
            st.session_state.num_sessions = num_sessions
            st.rerun()
        
        qa_lists = []
        for session_idx in range(num_sessions):
            with st.expander(f"对话序列 {session_idx+1}", expanded=session_idx < 2):
                session_id = st.text_input(
                    "会话ID",
                    value=f"session_{session_idx+1}",
                    key=f"session_id_{session_idx}"
                )
                
                # 问答对输入
                session_items = BackwardV2TestForm._handle_session_qas(session_idx)
                
                if session_items:
                    qa_lists.append({
                        "items": session_items,
                        "session_id": session_id
                    })
        
        return qa_lists
    
    @staticmethod
    def _handle_session_qas(session_idx: int) -> List[Dict[str, str]]:
        """处理单个会话的问答对"""
        if f'num_qas_{session_idx}' not in st.session_state:
            st.session_state[f'num_qas_{session_idx}'] = 2
        
        num_qas = st.number_input(
            "问答对数量",
            min_value=1,
            max_value=20,
            value=st.session_state[f'num_qas_{session_idx}'],
            key=f"num_qas_{session_idx}"
        )
        
        session_items = []
        for qa_idx in range(num_qas):
            q = st.text_area(f"问题 {qa_idx+1}", key=f"q_{session_idx}_{qa_idx}")
            a = st.text_area(f"答案 {qa_idx+1}", key=f"a_{session_idx}_{qa_idx}")
            if q.strip() and a.strip():
                session_items.append({"question": q.strip(), "answer": a.strip()})
        
        return session_items
    
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
            ["使用示例数据", "上传JSON文件", "从历史结果导入", "手动编辑JSON"],
            key="chapter_input_method",
            horizontal=True
        )
        
        if chapter_input_method == "使用示例数据":
            return BackwardV2TestForm._handle_example_structure(example)
        elif chapter_input_method == "上传JSON文件":
            return BackwardV2TestForm._handle_json_upload()
        elif chapter_input_method == "从历史结果导入":
            return BackwardV2TestForm._handle_history_import()
        else:  # 手动编辑JSON
            return BackwardV2TestForm._handle_manual_json()
    
    @staticmethod
    def _handle_example_structure(example: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """处理示例章节结构"""
        if example.get("chapter_structure"):
            st.success("✅ 使用示例章节目录")
            with st.expander("📋 示例章节结构预览"):
                st.json(example["chapter_structure"])
            return example["chapter_structure"]
        else:
            st.info("当前示例无章节目录数据")
            return None
    
    @staticmethod
    def _handle_json_upload() -> Optional[Dict[str, Any]]:
        """处理JSON文件上传"""
        uploaded_structure_file = st.file_uploader(
            "上传章节结构JSON文件",
            type=['json'],
            help="上传之前导出的章节结构JSON文件",
            key="upload_chapter_structure"
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
    
    @staticmethod
    def _handle_history_import() -> Optional[Dict[str, Any]]:
        """处理历史结果导入"""
        if ('backward_v2_result' in st.session_state and
                st.session_state.backward_v2_result.get("chapter_structure")):
            if st.button("📥 导入历史章节结构", key="import_history_structure"):
                chapter_structure = st.session_state.backward_v2_result["chapter_structure"]
                history_nodes_count = len(chapter_structure.get("nodes", {}))
                st.success(f"✅ 从历史结果导入章节结构，包含 {history_nodes_count} 个章节")
                
                with st.expander("📋 历史章节结构预览"):
                    st.json(chapter_structure)
                
                return chapter_structure
        else:
            st.info("💡 暂无历史处理结果可导入，请先执行一次Backward V2处理")
        
        return None
    
    @staticmethod
    def _handle_manual_json() -> Optional[Dict[str, Any]]:
        """处理手动JSON编辑"""
        st.info("💡 提示：可以先使用其他方式导入基础结构，然后在此基础上编辑")
        
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
                    "related_cqa_items": [],
                    "related_cqa_ids": [],
                    "chapter_number": "1."
                }
            },
            "root_ids": ["chapter_1"],
            "max_level": 3
        }
        
        if 'manual_chapter_structure' not in st.session_state:
            import json
            st.session_state.manual_chapter_structure = json.dumps(
                default_structure, ensure_ascii=False, indent=2
            )
        
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
                    
                    if isinstance(parsed_structure, dict) and "nodes" in parsed_structure:
                        st.session_state.manual_chapter_structure = edited_structure_text
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
            if st.button("🔄 重置为默认", key="reset_manual_structure"):
                import json
                st.session_state.manual_chapter_structure = json.dumps(
                    default_structure, ensure_ascii=False, indent=2
                )
                st.rerun()
        
        return None


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