"""
OSPA表格管理页面
"""

import streamlit as st
import copy
import time
from typing import Optional, Union
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
        st.markdown(
            "**功能说明**: 管理和分析 OSPA (Observation-State-Prompt-Action) 数据，"
            "支持一致性检测和自动生成"
        )

        # 确保OSPA管理器存在
        if "ospa_manager" not in st.session_state:
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
                key="ospa_data_source",
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

    def _handle_data_loading(
        self, data_source: str, current_manager: OSPAManager
    ) -> Optional[OSPAManager]:
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
            type=["csv"],
            help="CSV文件应包含观察(O)和行动(A)等必要列",
        )

        if uploaded_file is not None:
            # 生成文件的唯一标识符
            file_info = {
                "name": uploaded_file.name,
                "size": uploaded_file.size,
                "type": uploaded_file.type,
            }

            # 检查是否已经处理过相同的文件
            if "last_processed_file" not in st.session_state:
                st.session_state.last_processed_file = None

            # 判断是否是新文件或文件已变更
            is_new_file = (
                st.session_state.last_processed_file is None
                or st.session_state.last_processed_file != file_info
            )

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
                st.info(
                    f"📁 文件 '{uploaded_file.name}' 已加载，"
                    f"当前有 {len(current_manager.items)} 条数据"
                )
                return None

        return None

    def _handle_example_data(self) -> Optional[OSPAManager]:
        """处理示例数据"""
        example_files = {
            "示例1 (exp1.csv)": "data/ospa/exp1.csv",
            "示例2 (exp2.csv)": "data/ospa/exp2.csv",
            "示例3 (exp3.csv)": "data/ospa/exp3.csv",
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

    def _handle_manual_input(
        self, current_manager: OSPAManager
    ) -> Optional[OSPAManager]:
        """处理手动输入"""
        if "manual_ospa_count" not in st.session_state:
            st.session_state.manual_ospa_count = 3

        num_entries = st.number_input(
            "OSPA 条目数量",
            min_value=1,
            max_value=20,
            value=st.session_state.manual_ospa_count,
            key="manual_ospa_num",
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
            if st.button(
                "🔄 更新数据",
                type="primary",
                help="保存表格编辑的内容并刷新显示",
                key="update_ospa_table",
            ):
                st.rerun()

        # 显示可编辑表格
        edited_df = StreamlitUtils.display_ospa_table(ospa_manager, "ospa_editor")

        # 显示表格说明
        st.markdown(
            """
        **表格说明**：
        - **O**: 观察/用户输入
        - **S**: 状态/场景
        - **p**: 提示词
        - **A**: Agent输出/标准答案
        - **A'**: 候选答案（用于一致性比较）
        - **consistency**: A与A'的语义一致性得分
        - **confidence_score**: 一致性检测的置信度
        - **error**: 错误信息
        """
        )

        # 更新管理器数据
        if edited_df is not None:
            if StreamlitUtils.update_manager_from_edited_df(ospa_manager, edited_df):
                pass  # 数据已更新

    def _render_operations_section(self, ospa_manager: OSPAManager):
        """渲染操作区域"""
        st.subheader("🔧 操作控制")

        if ospa_manager.items:
            # 章节结构可视化
            self._render_chapter_structure_visualization()

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
        st.markdown(
            "使用 Backward API 根据 O、A 生成对应的 S、p，通过章节结构聚合问答对"
        )

        valid_backward_count = len(ospa_manager.get_valid_items_for_backward())

        with st.expander("🔧 Backward API 参数配置", expanded=False):
            # 章节结构导入选项
            st.markdown("**章节结构配置**")
            use_existing_structure = st.radio(
                "章节结构来源",
                ["自动生成新结构", "导入已有章节结构"],
                index=0,
                help="选择是让API自动创建章节结构，还是使用已有的章节结构",
            )

            imported_chapter_structure = None
            if use_existing_structure == "导入已有章节结构":
                import_method = st.radio(
                    "导入方式", ["从JSON文件导入", "从上次Backward结果导入"], index=0
                )

                if import_method == "从JSON文件导入":
                    uploaded_json = st.file_uploader(
                        "选择章节结构JSON文件",
                        type=["json"],
                        help="请上传符合章节结构格式的JSON文件",
                    )

                    if uploaded_json is not None:
                        try:
                            import json

                            chapter_data = json.load(uploaded_json)

                            # 验证章节结构格式
                            if "nodes" in chapter_data and "root_ids" in chapter_data:
                                imported_chapter_structure = chapter_data
                                st.success(
                                    f"✅ 成功导入章节结构：{len(chapter_data['nodes'])} 个节点，{len(chapter_data['root_ids'])} 个根节点"
                                )

                                # 显示导入结构的预览
                                with st.expander(
                                    "📋 预览导入的章节结构", expanded=True
                                ):
                                    self._render_chapter_tree_compact(
                                        imported_chapter_structure, "从JSON导入的章节"
                                    )

                                # 提供保存到预览的选项
                                if st.button(
                                    "💾 保存到导入预览", key="save_to_preview"
                                ):
                                    st.session_state["imported_chapter_for_reuse"] = (
                                        imported_chapter_structure
                                    )
                                    st.success(
                                        "✅ 已保存到导入预览，可在'章节结构可视化'中查看"
                                    )
                            else:
                                st.error(
                                    "❌ JSON文件格式不正确，缺少'nodes'或'root_ids'字段"
                                )
                        except Exception as e:
                            st.error(f"❌ JSON文件解析失败: {str(e)}")

                elif import_method == "从上次Backward结果导入":
                    if st.session_state.get("backward_generation_result"):
                        last_result = st.session_state["backward_generation_result"]
                        if last_result.get("result") and last_result["result"].get(
                            "chapter_structure"
                        ):
                            imported_chapter_structure = last_result["result"][
                                "chapter_structure"
                            ]
                            st.info(
                                f"✅ 使用上次生成的章节结构：{last_result['result'].get('total_chapters', 0)} 个章节"
                            )
                        else:
                            st.warning("⚠️ 上次结果中没有章节结构数据")
                    elif st.session_state.get("imported_chapter_for_reuse"):
                        imported_chapter_structure = st.session_state[
                            "imported_chapter_for_reuse"
                        ]
                        st.info(
                            f"✅ 使用预设的重用章节结构：{len(imported_chapter_structure.get('nodes', {}))} 个章节"
                        )
                    else:
                        st.warning("⚠️ 没有找到可用的章节结构")

                    # 如果有导入的结构，显示简要预览
                    if imported_chapter_structure:
                        with st.expander("📋 预览导入的章节结构", expanded=False):
                            self._render_chapter_tree_compact(
                                imported_chapter_structure, "即将导入的章节"
                            )

            st.markdown("---")

            col1, col2 = st.columns(2)

            with col1:
                max_level = st.selectbox(
                    "最大章节层级",
                    options=[1, 2, 3, 4, 5],
                    index=2,  # 默认3级
                    help="章节结构的最大深度",
                )

                max_concurrent_llm = st.selectbox(
                    "最大并发LLM数量",
                    options=[1, 3, 5, 8, 10, 15, 20],
                    index=4,  # 默认8个
                    help="同时运行的LLM请求数量，影响处理速度",
                )

            with col2:
                overwrite_mode = st.radio(
                    "数据更新模式",
                    ["只更新空白字段", "覆盖所有字段"],
                    index=0,
                    help="选择如何处理已有的S、p数据",
                )

            st.markdown("**提示词内容配置**")
            include_cases_in_prompt = st.checkbox(
                "在提示词中包含章节关联案例",
                value=False,
                help="勾选后，P列除了包含章节提示词，还会包含该章节关联的所有QA案例作为参考"
            )

            if include_cases_in_prompt:
                max_cases_per_chapter = st.slider(
                    "每章节最大案例数量",
                    min_value=1,
                    max_value=20,
                    value=5,
                    help="限制每个章节在提示词中包含的案例数量，避免提示词过长"
                )
            else:
                max_cases_per_chapter = 0

            st.markdown("**提示词优化说明**")
            if use_existing_structure == "自动生成新结构":
                st.caption(
                    "Backward API会自动根据问答对的内容特征进行章节聚合，并为每个章节生成专业的提示词。"
                )
            else:
                st.caption(
                    "使用导入的章节结构对问答对进行分类，并为每个章节生成针对性的提示词。"
                )

            if include_cases_in_prompt:
                st.caption(
                    f"💡 将在每个章节的提示词中包含最多 {max_cases_per_chapter} 个相关案例，"
                    "帮助AI更好地理解章节内容和回答风格。"
                )

        col_c, col_d = st.columns(2)
        with col_c:
            if st.button(
                "↩️ 生成状态和提示词",
                type="secondary",
                key="run_backward_generation",
                disabled=valid_backward_count == 0,
            ):
                self._execute_backward_generation(
                    ospa_manager,
                    max_level,
                    max_concurrent_llm,
                    overwrite_mode,
                    imported_chapter_structure,
                    include_cases_in_prompt,
                    max_cases_per_chapter,
                )

        with col_d:
            if st.button("🔄 清空状态提示词", type="secondary"):
                ospa_manager.clear_field("S")
                ospa_manager.clear_field("p")
                st.rerun()
                st.success("✅ 已清空所有状态和提示词")

    def _execute_backward_generation(
        self,
        ospa_manager: OSPAManager,
        max_level: int,
        max_concurrent_llm: int,
        overwrite_mode: str,
        chapter_structure: Optional[dict] = None,
        include_cases_in_prompt: bool = False,
        max_cases_per_chapter: int = 0,
    ):
        """执行状态提示词生成"""
        status_placeholder = st.empty()

        if chapter_structure:
            status_placeholder.info("正在使用导入的章节结构调用 Backward API...")
        else:
            status_placeholder.info("正在调用 Backward API 进行章节聚合和提示词生成...")

        result = self.processor.process_backward_generation(
            ospa_manager,
            max_level,
            max_concurrent_llm,
            overwrite_mode,
            chapter_structure,
            include_cases_in_prompt,
            max_cases_per_chapter,
        )

        status_placeholder.empty()

        if result["success"]:
            if result.get("skipped_count", 0) > 0:
                st.success(
                    f"✅ 成功生成状态和提示词！更新了 {result['updated_count']} 条，"
                    f"跳过了 {result['skipped_count']} 条"
                )
            else:
                st.success(
                    f"✅ 成功生成状态和提示词！更新了 {result['updated_count']} 条"
                )

            # 显示章节结构信息
            if result.get("result") and result["result"].get("chapter_structure"):
                chapter_info = result["result"]["chapter_structure"]
                with st.expander("📊 生成的章节结构概览", expanded=False):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("总章节数", result["result"].get("total_chapters", 0))
                    with col2:
                        st.metric("总问答对", result["result"].get("total_qas", 0))
                    with col3:
                        st.metric("OSPA条目", result["result"].get("total_ospa", 0))

                    # 显示主章节列表
                    if chapter_info.get("root_ids"):
                        st.markdown("**主章节列表：**")
                        nodes = chapter_info.get("nodes", {})
                        for root_id in chapter_info["root_ids"]:
                            if root_id in nodes:
                                node = nodes[root_id]
                                st.markdown(
                                    f"- 📁 {node.get('title', '未命名章节')} ({len(node.get('related_qa_items', []))} 个问答)"
                                )

                    # 添加导出章节结构功能
                    if st.button(
                        "📥 导出章节结构为JSON", key="export_chapter_structure"
                    ):
                        import json
                        import time

                        chapter_json = json.dumps(
                            chapter_info, ensure_ascii=False, indent=2
                        )
                        st.download_button(
                            label="下载章节结构JSON文件",
                            data=chapter_json,
                            file_name=f"chapter_structure_{int(time.time())}.json",
                            mime="application/json",
                            key="download_chapter_structure",
                        )

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
                help="控制生成答案的创造性，0.0最确定，2.0最有创造性",
            )
            answer_generation_mode = st.radio(
                "A'字段更新模式",
                ["只更新空白字段", "覆盖所有字段"],
                index=0,
                help="选择如何处理已有的A'字段数据",
            )
            llm_enable_concurrent = st.checkbox(
                "启用并发处理", value=True, key="llm_concurrent_enabled"
            )
            llm_max_concurrent = st.selectbox(
                "并发请求数", [1, 3, 5, 8, 10], index=3, key="llm_concurrent_num"
            )

        col_e, col_f = st.columns(2)
        with col_e:
            if st.button(
                "🤖 智能生成答案",
                type="secondary",
                key="run_answer_generation",
                disabled=valid_llm_count == 0,
            ):
                self._execute_llm_generation(
                    ospa_manager,
                    answer_temperature,
                    answer_generation_mode,
                    llm_enable_concurrent,
                    llm_max_concurrent,
                )

        with col_f:
            if st.button("🔄 清空生成答案", type="secondary"):
                ospa_manager.clear_field("A_prime")
                st.rerun()
                st.success("✅ 已清空所有生成的答案")

    def _execute_llm_generation(
        self,
        ospa_manager: OSPAManager,
        temperature: float,
        generation_mode: str,
        enable_concurrent: bool,
        max_concurrent: int,
    ):
        """执行智能答案生成"""
        progress_bar = st.progress(0)
        status_placeholder = st.empty()

        result = self.processor.process_llm_generation(
            ospa_manager,
            temperature,
            generation_mode,
            enable_concurrent,
            max_concurrent,
            lambda p: progress_bar.progress(p),
            lambda s: status_placeholder.info(s),
        )

        progress_bar.empty()
        status_placeholder.empty()

        if result["success"]:
            if result.get("skipped_count", 0) > 0:
                st.success(
                    f"✅ 完成答案生成！生成了 {result['success_count']} 条新答案，"
                    f"跳过了 {result['skipped_count']} 条"
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

    def _render_consistency_check(self, ospa_manager: OSPAManager):
        """渲染一致性检测"""
        st.write("**一致性检测**")
        st.markdown("使用 Reward API 计算每行数据中 A 和 A' 的语义一致性")

        valid_reward_count = len(ospa_manager.get_valid_items_for_reward())

        with st.expander("🔧 一致性检测配置", expanded=False):
            reward_enable_concurrent = st.checkbox(
                "启用并发处理", value=True, key="reward_concurrent_enabled"
            )
            reward_max_concurrent = st.selectbox(
                "并发请求数", [1, 3, 5, 8, 10], index=3, key="reward_concurrent_num"
            )

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button(
                "🏆 执行一致性检测",
                type="primary",
                key="run_consistency_check",
                disabled=valid_reward_count == 0,
            ):
                self._execute_consistency_check(
                    ospa_manager, reward_enable_concurrent, reward_max_concurrent
                )

        with col_b:
            if st.button("🔄 清空一致性结果", type="secondary"):
                ospa_manager.clear_field("consistency")
                ospa_manager.clear_field("confidence_score")
                ospa_manager.clear_field("error")
                st.rerun()
                st.success("✅ 已清空所有一致性检测结果")

    def _execute_consistency_check(
        self, ospa_manager: OSPAManager, enable_concurrent: bool, max_concurrent: int
    ):
        """执行一致性检测"""
        progress_bar = st.progress(0)
        status_placeholder = st.empty()

        result = self.processor.process_reward_consistency(
            ospa_manager,
            enable_concurrent,
            max_concurrent,
            lambda p: progress_bar.progress(p),
            lambda s: status_placeholder.info(s),
        )

        progress_bar.empty()
        status_placeholder.empty()

        if result["success"]:
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

        # OSPA数据导出
        col_a, col_b = st.columns(2)

        with col_a:
            if st.button("💾 导出 OSPA 数据", key="export_ospa"):
                export_df = ospa_manager.to_dataframe()
                csv = export_df.to_csv(index=False)
                st.download_button(
                    label="下载 CSV 文件",
                    data=csv,
                    file_name=f"ospa_data_{int(time.time())}.csv",
                    mime="text/csv",
                )

        with col_b:
            if st.button("🗑️ 清空所有数据", key="clear_ospa"):
                st.session_state.ospa_manager = OSPAManager()
                st.rerun()

        # 章节结构导出
        st.write("**章节结构导出**")
        col_c, col_d, col_e = st.columns(3)

        with col_c:
            if st.button("📁 导出当前章节结构", key="export_current_chapter"):
                self._export_chapter_structure("current")

        with col_d:
            if st.button("📂 导出导入章节结构", key="export_imported_chapter"):
                self._export_chapter_structure("imported")

        with col_e:
            if st.button("📊 导出所有章节数据", key="export_all_chapters"):
                self._export_all_chapter_data()

    def _export_chapter_structure(self, structure_type: str):
        """导出指定类型的章节结构"""
        chapter_structure = None
        file_prefix = ""

        if structure_type == "current":
            if st.session_state.get("backward_generation_result"):
                result = st.session_state["backward_generation_result"]
                if result.get("success") and result.get("result"):
                    chapter_structure = result["result"].get("chapter_structure")
                    file_prefix = "current_chapter_structure"

            if not chapter_structure:
                st.warning("⚠️ 当前没有可导出的章节结构")
                return

        elif structure_type == "imported":
            chapter_structure = st.session_state.get("imported_chapter_for_reuse")
            file_prefix = "imported_chapter_structure"

            if not chapter_structure:
                st.warning("⚠️ 当前没有导入的章节结构")
                return

        # 执行导出
        if chapter_structure:
            import json

            chapter_json = json.dumps(chapter_structure, ensure_ascii=False, indent=2)
            st.download_button(
                label=f"下载 {file_prefix}.json",
                data=chapter_json,
                file_name=f"{file_prefix}_{int(time.time())}.json",
                mime="application/json",
                key=f"download_{structure_type}_structure",
            )

    def _export_all_chapter_data(self):
        """导出所有章节相关数据"""
        all_data = {}

        # 收集当前章节结构
        if st.session_state.get("backward_generation_result"):
            result = st.session_state["backward_generation_result"]
            if result.get("success") and result.get("result"):
                all_data["current_chapter_structure"] = result["result"].get(
                    "chapter_structure"
                )
                all_data["current_generation_result"] = {
                    "total_chapters": result["result"].get("total_chapters", 0),
                    "total_qas": result["result"].get("total_qas", 0),
                    "total_ospa": result["result"].get("total_ospa", 0),
                    "processing_time_ms": result["result"].get("processing_time_ms", 0),
                }

        # 收集导入章节结构
        if st.session_state.get("imported_chapter_for_reuse"):
            all_data["imported_chapter_structure"] = st.session_state[
                "imported_chapter_for_reuse"
            ]

        # 收集OSPA数据统计
        if (
            hasattr(st.session_state, "ospa_manager")
            and st.session_state.ospa_manager.items
        ):
            manager = st.session_state.ospa_manager
            all_data["ospa_statistics"] = manager.get_statistics()

        # 添加导出时间戳
        import datetime

        all_data["export_metadata"] = {
            "export_time": datetime.datetime.now().isoformat(),
            "total_items": len(all_data),
            "description": "Complete export of all chapter structures and OSPA data",
        }

        if not any(key.endswith("_structure") for key in all_data.keys()):
            st.warning("⚠️ 当前没有可导出的章节数据")
            return

        # 执行导出
        import json

        all_json = json.dumps(all_data, ensure_ascii=False, indent=2)
        st.download_button(
            label="下载完整章节数据.json",
            data=all_json,
            file_name=f"complete_chapter_data_{int(time.time())}.json",
            mime="application/json",
            key="download_all_chapter_data",
        )

    def _render_chapter_structure_visualization(self):
        """渲染章节结构可视化区域"""
        st.write("**📊 章节结构可视化**")

        # 创建选项卡来展示不同的章节结构
        tab1, tab2, tab3 = st.tabs(["📋 当前状态", "📂 导入预览", "📈 生成历史"])

        with tab1:
            self._render_current_chapter_status()

        with tab2:
            self._render_imported_chapter_preview()

        with tab3:
            self._render_generation_history()

    def _render_current_chapter_status(self):
        """渲染当前章节状态"""
        st.markdown("**当前章节结构状态**")

        # 检查是否有最新的生成结果
        if st.session_state.get("backward_generation_result"):
            result = st.session_state["backward_generation_result"]
            if (
                result.get("success")
                and result.get("result")
                and result["result"].get("chapter_structure")
            ):
                chapter_info = result["result"]["chapter_structure"]

                # 显示简要统计
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("总章节数", len(chapter_info.get("nodes", {})))
                with col2:
                    st.metric("根章节数", len(chapter_info.get("root_ids", [])))
                with col3:
                    st.metric(
                        "生成时间", f"{result['result'].get('processing_time_ms', 0)}ms"
                    )

                # 显示章节树结构
                self._render_chapter_tree_compact(chapter_info, "当前章节结构")

                # 提供管理操作
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("🔄 重新应用此结构", key="reapply_structure"):
                        st.session_state["imported_chapter_for_reuse"] = chapter_info
                        st.success("✅ 章节结构已设置为下次生成的导入结构")

                with col_b:
                    if st.button("🗑️ 清除当前结构", key="clear_current_structure"):
                        if "backward_generation_result" in st.session_state:
                            del st.session_state["backward_generation_result"]
                        st.rerun()
            else:
                st.info("💡 暂无生成的章节结构。使用'状态提示词生成'功能创建章节结构。")
        else:
            st.info("💡 暂无生成的章节结构。使用'状态提示词生成'功能创建章节结构。")

    def _render_imported_chapter_preview(self):
        """渲染导入章节预览"""
        st.markdown("**导入章节结构预览**")

        # 检查是否有待重用的结构
        if st.session_state.get("imported_chapter_for_reuse"):
            imported_structure = st.session_state["imported_chapter_for_reuse"]
            st.success("📂 检测到设置的重用章节结构")

            # 显示导入结构的统计信息
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("导入章节数", len(imported_structure.get("nodes", {})))
            with col2:
                st.metric("根章节数", len(imported_structure.get("root_ids", [])))
            with col3:
                st.metric("最大层级", imported_structure.get("max_level", 0))

            # 显示导入的章节树
            self._render_chapter_tree_compact(imported_structure, "导入的章节结构")

            # 管理操作
            if st.button("❌ 取消使用导入结构", key="cancel_imported"):
                if "imported_chapter_for_reuse" in st.session_state:
                    del st.session_state["imported_chapter_for_reuse"]
                st.rerun()
        else:
            st.info(
                "💡 当前没有设置要重用的章节结构。可以从文件导入或从历史结果中选择。"
            )

            # 提供快速导入选项
            st.markdown("**快速导入选项：**")
            if st.button("📄 从JSON文件导入", key="quick_import_json"):
                st.info("请在'状态提示词生成'区域中选择'导入已有章节结构'选项")

    def _render_generation_history(self):
        """渲染生成历史"""
        st.markdown("**章节生成历史**")

        # 检查会话状态中的历史记录
        history_keys = [
            key
            for key in st.session_state.keys()
            if isinstance(key, str) and key.startswith("backward_generation_result")
        ]

        if history_keys:
            st.info("📚 找到生成历史记录")

            # 显示最近的记录
            if st.session_state.get("backward_generation_result"):
                result = st.session_state["backward_generation_result"]
                if result.get("success"):
                    with st.expander("📋 最近一次生成结果", expanded=False):
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric(
                                "章节数",
                                result.get("result", {}).get("total_chapters", 0),
                            )
                        with col2:
                            st.metric(
                                "问答对数", result.get("result", {}).get("total_qas", 0)
                            )
                        with col3:
                            st.metric(
                                "OSPA条目",
                                result.get("result", {}).get("total_ospa", 0),
                            )
                        with col4:
                            processing_time = result.get("result", {}).get(
                                "processing_time_ms", 0
                            )
                            st.metric("处理时间", f"{processing_time}ms")

                        if st.button("🔄 恢复此次结果", key="restore_last_result"):
                            st.session_state["imported_chapter_for_reuse"] = result[
                                "result"
                            ]["chapter_structure"]
                            st.success("✅ 已恢复到导入结构预览")
                            st.rerun()
        else:
            st.info("💡 暂无生成历史。完成一次'状态提示词生成'后将显示历史记录。")

    def _render_chapter_tree_compact(self, chapter_structure: dict, title: str):
        """渲染紧凑的章节树显示"""
        st.markdown(f"**{title}**")

        nodes = chapter_structure.get("nodes", {})
        root_ids = chapter_structure.get("root_ids", [])

        if not nodes:
            st.warning("⚠️ 章节结构为空")
            return

        # 使用紧凑的树形显示
        def render_node_compact(node_id, level=0):
            if node_id not in nodes:
                return

            node = nodes[node_id]
            indent = "　" * level

            # 选择图标
            if level == 0:
                icon = "🏛️"
            elif level == 1:
                icon = "📁"
            elif level == 2:
                icon = "📂"
            else:
                icon = "📄"

            # 显示节点信息
            title = node.get("title", "未命名章节")
            qa_count = len(node.get("related_qa_items", []))
            chapter_number = node.get("chapter_number", "")

            # 紧凑显示格式
            node_text = f"{indent}{icon} **{chapter_number} {title}** ({qa_count} 问答)"
            st.markdown(node_text)

            # 递归显示子节点
            children = node.get("children", [])
            for child_id in children:
                render_node_compact(child_id, level + 1)

        # 渲染所有根节点
        for root_id in root_ids:
            render_node_compact(root_id)

        # 提供详细查看选项
        with st.expander(f"🔍 查看{title}详细信息"):
            st.json(chapter_structure)
