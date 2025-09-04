"""
OSPA表格管理页面
"""
import streamlit as st
import copy
from typing import Optional
from components.common import ResultDisplay, StatusIndicator
from ospa_models import OSPAManager
from ospa_utils import OSPADataLoader, OSPAProcessor, StreamlitUtils


class OSPAPage:
    """OSPA表格管理页面"""
    
    def __init__(self, service_manager):
        self.service_manager = service_manager
        self.processor = OSPAProcessor(service_manager)
    
    def render(self):
        """渲染OSPA页面"""
        st.header("📊 OSPA 表格管理")
        st.markdown("**功能说明**: 管理和分析 OSPA (Observation-State-Prompt-Action) 数据，"
                   "支持一致性检测和自动生成")
        
        # 确保OSPA管理器存在
        if 'ospa_manager' not in st.session_state:
            st.session_state.ospa_manager = OSPAManager()
        
        ospa_manager = st.session_state.ospa_manager
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            self._render_data_section(ospa_manager)
        
        with col2:
            self._render_operations_section(ospa_manager)
    
    def _render_data_section(self, ospa_manager: OSPAManager):
        """渲染数据区域"""
        st.subheader("📁 数据加载")
        
        col_data_source, col_statistics = st.columns([1, 3])
        
        with col_data_source:
            # 选择数据源
            data_source = st.radio(
                "数据源选择", 
                ["上传 CSV 文件", "使用示例数据", "手动输入"],
                key="ospa_data_source"
            )
        
        with col_statistics:
            # 显示数据统计
            StreamlitUtils.show_statistics(ospa_manager)
        
        # 数据加载处理
        new_manager = self._handle_data_loading(data_source, ospa_manager)
        if new_manager:
            ospa_manager = st.session_state.ospa_manager = copy.deepcopy(new_manager)
            st.rerun()
        
        # 显示和编辑当前数据
        if ospa_manager.items:
            self._render_data_table(ospa_manager)
    
    def _handle_data_loading(self, data_source: str, current_manager: OSPAManager) -> Optional[OSPAManager]:
        """处理数据加载逻辑"""
        if data_source == "上传 CSV 文件":
            return self._handle_csv_upload(current_manager)
        elif data_source == "使用示例数据":
            return self._handle_example_data()
        elif data_source == "手动输入":
            return self._handle_manual_input(current_manager)
        return None
    
    def _handle_csv_upload(self, current_manager: OSPAManager) -> Optional[OSPAManager]:
        """处理CSV文件上传"""
        uploaded_file = st.file_uploader(
            "选择 OSPA CSV 文件",
            type=['csv'],
            help="CSV文件应包含观察(O)和行动(A)等必要列"
        )
        
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
                    new_manager = OSPADataLoader.load_from_csv_file(uploaded_file)
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
        
        return None
    
    def _handle_example_data(self) -> Optional[OSPAManager]:
        """处理示例数据"""
        example_files = {
            "示例1 (exp1.csv)": "ospa/exp1.csv",
            "示例2 (exp2.csv)": "ospa/exp2.csv", 
            "示例3 (exp3.csv)": "ospa/exp3.csv"
        }
        
        selected_example = st.selectbox("选择示例文件", list(example_files.keys()))
        
        if st.button("📥 加载示例数据", key="load_example"):
            try:
                example_file = example_files[selected_example]
                new_manager = OSPADataLoader.load_from_example_file(example_file)
                st.success(f"✅ 成功加载 {len(new_manager.items)} 条示例数据")
                
                # 强制刷新以确保数据正确加载
                if "ospa_editor" in st.session_state:
                    del st.session_state["ospa_editor"]
                
                return new_manager
                
            except Exception as e:
                st.error(f"示例数据加载失败: {str(e)}")
                return None
        
        return None
    
    def _handle_manual_input(self, current_manager: OSPAManager) -> Optional[OSPAManager]:
        """处理手动输入"""
        if 'manual_ospa_count' not in st.session_state:
            st.session_state.manual_ospa_count = 3
        
        num_entries = st.number_input(
            "OSPA 条目数量",
            min_value=1,
            max_value=20,
            value=st.session_state.manual_ospa_count,
            key="manual_ospa_num"
        )
        
        if num_entries != st.session_state.manual_ospa_count:
            st.session_state.manual_ospa_count = num_entries
            st.rerun()
        
        with st.form("manual_ospa_form"):
            from ospa_models import OSPAItem
            manual_items = []
            for i in range(num_entries):
                st.write(f"**OSPA 条目 {i+1}**")
                o = st.text_area(f"O (观察/用户输入)", key=f"manual_o_{i}")
                a = st.text_area(f"A (Agent输出)", key=f"manual_a_{i}")
                
                if o.strip() and a.strip():
                    manual_items.append(OSPAItem(no=i + 1, O=o.strip(), A=a.strip()))
            
            if st.form_submit_button("💾 保存手动输入的数据", type="primary"):
                current_manager.items = manual_items
                st.success(f"✅ 成功保存 {len(manual_items)} 条 OSPA 数据")
                
                # 强制刷新以确保数据正确加载
                if "ospa_editor" in st.session_state:
                    del st.session_state["ospa_editor"]
                
                return current_manager
        
        return None
    
    def _render_data_table(self, ospa_manager: OSPAManager):
        """渲染数据表格"""
        # 表格标题和更新按钮
        col_title, col_update = st.columns([4, 1])
        with col_title:
            st.subheader("📋 当前 OSPA 数据表格")
        with col_update:
            if st.button("🔄 更新数据", type="primary", 
                        help="保存表格编辑的内容并刷新显示",
                        key="update_ospa_table"):
                st.rerun()
        
        # 显示可编辑表格
        edited_df = StreamlitUtils.display_ospa_table(ospa_manager, "ospa_editor")
        
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
            if StreamlitUtils.update_manager_from_edited_df(ospa_manager, edited_df):
                pass  # 数据已更新
    
    def _render_operations_section(self, ospa_manager: OSPAManager):
        """渲染操作区域"""
        st.subheader("🔧 操作控制")
        
        if ospa_manager.items:
            # 状态提示词生成
            self._render_backward_generation(ospa_manager)
            
            # 智能答案生成
            self._render_llm_generation(ospa_manager)
            
            # 一致性检测
            self._render_consistency_check(ospa_manager)
            
            # 数据管理
            self._render_data_management(ospa_manager)
        else:
            st.info("请先加载或输入 OSPA 数据")
    
    def _render_backward_generation(self, ospa_manager: OSPAManager):
        """渲染状态提示词生成"""
        st.write("**状态提示词生成**")
        st.markdown("使用 Backward API 根据 O、A 生成对应的 S、p")
        
        valid_backward_count = len(ospa_manager.get_valid_items_for_backward())
        
        with st.expander("🔧 生成参数配置", expanded=False):
            chapters_extra_instructions = st.text_area(
                "章节聚合额外指令(选填)", 
                value="", 
                help="指导如何聚合问答对到章节的额外说明"
            )
            gen_p_extra_instructions = st.text_area(
                "提示词生成额外指令(选填)",
                value="",
                help="指导如何生成提示词的额外说明"
            )
            overwrite_mode = st.radio(
                "数据更新模式", 
                ["只更新空白字段", "覆盖所有字段"],
                index=0,
                help="选择如何处理已有的S、p数据"
            )
        
        col_c, col_d = st.columns(2)
        with col_c:
            if st.button("↩️ 生成状态和提示词", type="secondary",
                        key="run_backward_generation",
                        disabled=valid_backward_count == 0):
                self._execute_backward_generation(
                    ospa_manager, chapters_extra_instructions,
                    gen_p_extra_instructions, overwrite_mode
                )
        
        with col_d:
            if st.button("🔄 清空状态提示词", type="secondary"):
                ospa_manager.clear_field('S')
                ospa_manager.clear_field('p')
                st.rerun()
                st.success("✅ 已清空所有状态和提示词")
    
    def _execute_backward_generation(self, ospa_manager: OSPAManager,
                                   chapters_extra_instructions: str,
                                   gen_p_extra_instructions: str,
                                   overwrite_mode: str):
        """执行状态提示词生成"""
        status_placeholder = st.empty()
        
        result = self.processor.process_backward_generation(
            ospa_manager, chapters_extra_instructions,
            gen_p_extra_instructions, overwrite_mode
        )
        
        status_placeholder.empty()
        
        if result['success']:
            if result.get('skipped_count', 0) > 0:
                st.success(
                    f"✅ 成功生成状态和提示词！更新了 {result['updated_count']} 条，"
                    f"跳过了 {result['skipped_count']} 条"
                )
            else:
                st.success(f"✅ 成功生成状态和提示词！更新了 {result['updated_count']} 条")
            
            # 保存结果到会话状态
            st.session_state.backward_generation_result = result
            # 强制刷新页面以显示更新的表格数据
            st.rerun()
        else:
            st.error(f"❌ {result['error']}")
            st.session_state.backward_generation_result = result
    
    def _render_llm_generation(self, ospa_manager: OSPAManager):
        """渲染智能答案生成"""
        st.write("**智能答案生成**")
        st.markdown("使用 LLM Ask API 根据 O（观察）和 p（提示词）生成 A'（答案）")
        
        valid_llm_count = len(ospa_manager.get_valid_items_for_llm())
        
        with st.expander("🔧 生成配置", expanded=False):
            answer_temperature = st.slider(
                "生成温度",
                min_value=0.0,
                max_value=2.0,
                value=0.3,
                step=0.1,
                help="控制生成答案的创造性，0.0最确定，2.0最有创造性"
            )
            answer_generation_mode = st.radio(
                "A'字段更新模式",
                ["只更新空白字段", "覆盖所有字段"],
                index=0,
                help="选择如何处理已有的A'字段数据"
            )
            llm_enable_concurrent = st.checkbox(
                "启用并发处理", 
                value=True, 
                key="llm_concurrent_enabled"
            )
            llm_max_concurrent = st.selectbox(
                "并发请求数", 
                [1, 3, 5, 8, 10],
                index=3,
                key="llm_concurrent_num"
            )
        
        col_e, col_f = st.columns(2)
        with col_e:
            if st.button("🤖 智能生成答案", type="secondary",
                        key="run_answer_generation",
                        disabled=valid_llm_count == 0):
                self._execute_llm_generation(
                    ospa_manager, answer_temperature, answer_generation_mode,
                    llm_enable_concurrent, llm_max_concurrent
                )
        
        with col_f:
            if st.button("🔄 清空生成答案", type="secondary"):
                ospa_manager.clear_field('A_prime')
                st.rerun()
                st.success("✅ 已清空所有生成的答案")
    
    def _execute_llm_generation(self, ospa_manager: OSPAManager, temperature: float,
                               generation_mode: str, enable_concurrent: bool,
                               max_concurrent: int):
        """执行智能答案生成"""
        progress_bar = st.progress(0)
        status_placeholder = st.empty()
        
        result = self.processor.process_llm_generation(
            ospa_manager, temperature, generation_mode, enable_concurrent,
            max_concurrent, lambda p: progress_bar.progress(p),
            lambda s: status_placeholder.info(s)
        )
        
        progress_bar.empty()
        status_placeholder.empty()
        
        if result['success']:
            if result.get('skipped_count', 0) > 0:
                st.success(
                    f"✅ 完成答案生成！生成了 {result['success_count']} 条新答案，"
                    f"跳过了 {result['skipped_count']} 条"
                )
            else:
                st.success(f"✅ 完成答案生成！成功生成: {result['success_count']} 条答案")
            
            # 保存结果到会话状态
            st.session_state.answer_generation_result = result
            # 清除表格编辑器的状态缓存，强制重新渲染
            st.rerun()
        else:
            st.error(f"❌ {result['error']}")
            st.session_state.answer_generation_result = result
    
    def _render_consistency_check(self, ospa_manager: OSPAManager):
        """渲染一致性检测"""
        st.write("**一致性检测**")
        st.markdown("使用 Reward API 计算每行数据中 A 和 A' 的语义一致性")
        
        valid_reward_count = len(ospa_manager.get_valid_items_for_reward())
        
        with st.expander("🔧 一致性检测配置", expanded=False):
            reward_enable_concurrent = st.checkbox(
                "启用并发处理", 
                value=True, 
                key="reward_concurrent_enabled"
            )
            reward_max_concurrent = st.selectbox(
                "并发请求数", 
                [1, 3, 5, 8, 10],
                index=3,
                key="reward_concurrent_num"
            )
        
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🏆 执行一致性检测", type="primary",
                        key="run_consistency_check",
                        disabled=valid_reward_count == 0):
                self._execute_consistency_check(
                    ospa_manager, reward_enable_concurrent, reward_max_concurrent
                )
        
        with col_b:
            if st.button("🔄 清空一致性结果", type="secondary"):
                ospa_manager.clear_field('consistency')
                ospa_manager.clear_field('confidence_score')
                ospa_manager.clear_field('error')
                st.rerun()
                st.success("✅ 已清空所有一致性检测结果")
    
    def _execute_consistency_check(self, ospa_manager: OSPAManager,
                                  enable_concurrent: bool, max_concurrent: int):
        """执行一致性检测"""
        progress_bar = st.progress(0)
        status_placeholder = st.empty()
        
        result = self.processor.process_reward_consistency(
            ospa_manager, enable_concurrent, max_concurrent,
            lambda p: progress_bar.progress(p),
            lambda s: status_placeholder.info(s)
        )
        
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
    
    def _render_data_management(self, ospa_manager: OSPAManager):
        """渲染数据管理"""
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
                    mime="text/csv"
                )
        
        with col_b:
            if st.button("🗑️ 清空所有数据", key="clear_ospa"):
                st.session_state.ospa_manager = OSPAManager()
                st.rerun()