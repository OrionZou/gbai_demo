"""
BQA Extract API测试页面 - 多轮对话解耦
"""
import streamlit as st
import pandas as pd
import time
from typing import Dict, Any, List
from components.common import PageHeader, ResultDisplay
from components.forms import BQAExtractTestForm
from config.examples import BQA_EXTRACT_EXAMPLES


class BQAExtractPage:
    """BQA Extract API测试页面"""

    def __init__(self, service_manager):
        self.service_manager = service_manager
        self.api_url = service_manager.base_url

    def render(self):
        """渲染BQA Extract页面"""
        st.header("🔧 BQA Extract API 测试 - 多轮对话解耦")

        col1, col2 = st.columns([2, 2])

        with col1:
            self._render_test_form()

        with col2:
            self._render_results()

    def _render_test_form(self):
        """渲染测试表单"""
        test_data = BQAExtractTestForm.render(BQA_EXTRACT_EXAMPLES)

        if test_data:
            self._execute_bqa_extract_test(test_data)

    def _execute_bqa_extract_test(self, test_data: Dict[str, Any]):
        """执行BQA Extract测试"""
        try:
            with st.spinner("正在执行多轮对话解耦处理..."):
                result = self.service_manager.bqa_extract_service.extract_conversations(
                    test_data["qa_lists"],
                    test_data.get("context_extraction_mode", "auto"),
                    test_data.get("preserve_session_info", True),
                    test_data.get("max_concurrent_processing", 3)
                )

            ResultDisplay.show_success("处理完成！")
            # 保存结果
            st.session_state.bqa_extract_result = result

        except Exception as e:
            ResultDisplay.show_error("处理失败", str(e))

    def _render_results(self):
        """渲染处理结果"""
        st.subheader("📊 处理结果")

        if 'bqa_extract_result' in st.session_state:
            result = st.session_state.bqa_extract_result

            # 基本统计信息
            self._render_statistics(result)

            # 会话结果展示
            self._render_session_results(result)

            # BQA数据表格显示
            self._render_bqa_table(result)

            # 导出功能
            self._render_export_section(result)
        else:
            st.info("暂无处理结果")

    def _render_statistics(self, result: Dict[str, Any]):
        """渲染统计信息"""
        st.success("✅ 处理完成") if result.get("success") else st.error("❌ 处理失败")

        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a:
            st.metric("会话数", result.get("total_sessions", 0))
        with col_b:
            st.metric("原始QA数", result.get("total_original_qas", 0))
        with col_c:
            st.metric("提取BQA数", result.get("total_extracted_bqas", 0))
        with col_d:
            processing_time = result.get("total_processing_time_ms", 0)
            st.metric("处理耗时", f"{processing_time} ms")

        # 处理摘要
        if result.get("processing_summary"):
            summary = result["processing_summary"]

            col_x, col_y, col_z = st.columns(3)
            with col_x:
                st.metric("提取模式", summary.get("mode", "auto"))
            with col_y:
                success_rate = summary.get("success_rate", 0) * 100
                st.metric("成功率", f"{success_rate:.1f}%")
            with col_z:
                stats = summary.get("stats", {})
                avg_dep = stats.get("avg_dependency_ratio", 0) * 100
                st.metric("平均依赖度", f"{avg_dep:.1f}%")

        if result.get("operation_log"):
            with st.expander("📋 操作日志"):
                for log_entry in result["operation_log"]:
                    st.text(log_entry)

    def _render_session_results(self, result: Dict[str, Any]):
        """渲染会话结果"""
        if not result.get("session_results"):
            return

        st.subheader("📁 会话处理结果")

        session_results = result["session_results"]

        # 会话概览
        col1, col2 = st.columns(2)
        with col1:
            # 成功处理的会话数
            successful_sessions = sum(1 for sr in session_results if sr.get("extracted_bqa_count", 0) > 0)
            st.metric("成功会话", f"{successful_sessions}/{len(session_results)}")

        with col2:
            # 平均处理时间
            avg_time = sum(sr.get("processing_time_ms", 0) for sr in session_results) / len(session_results)
            st.metric("平均处理时间", f"{avg_time:.0f} ms")

        # 详细会话列表
        for i, session_result in enumerate(session_results):
            session_id = session_result.get("session_id", f"session_{i+1}")
            original_count = session_result.get("original_qa_count", 0)
            extracted_count = session_result.get("extracted_bqa_count", 0)
            processing_time = session_result.get("processing_time_ms", 0)
            summary = session_result.get("extraction_summary", "")

            with st.expander(f"🗂️ 会话 {session_id} - {original_count} QA → {extracted_count} BQA"):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.write(f"**原始QA数:** {original_count}")
                    st.write(f"**提取BQA数:** {extracted_count}")
                with col_b:
                    st.write(f"**处理时间:** {processing_time} ms")
                    st.write(f"**提取摘要:** {summary}")

                # 显示BQA内容预览
                bqa_list = session_result.get("bqa_list", {})
                bqa_items = bqa_list.get("items", []) if isinstance(bqa_list, dict) else getattr(bqa_list, "items", [])

                if bqa_items:
                    st.write("**BQA预览:**")
                    for j, bqa in enumerate(bqa_items[:3]):  # 只显示前3个
                        background = bqa.get("background", "") if isinstance(bqa, dict) else getattr(bqa, "background", "")
                        question = bqa.get("question", "") if isinstance(bqa, dict) else getattr(bqa, "question", "")
                        answer = bqa.get("answer", "") if isinstance(bqa, dict) else getattr(bqa, "answer", "")

                        with st.container():
                            st.markdown(f"**BQA {j+1}:**")
                            if background:
                                st.markdown(f"*背景:* {background[:100]}{'...' if len(background) > 100 else ''}")
                            st.markdown(f"*问题:* {question[:100]}{'...' if len(question) > 100 else ''}")
                            st.markdown(f"*答案:* {answer[:100]}{'...' if len(answer) > 100 else ''}")
                            st.markdown("---")

                    if len(bqa_items) > 3:
                        st.caption(f"... 还有 {len(bqa_items) - 3} 个BQA")

    def _render_bqa_table(self, result: Dict[str, Any]):
        """渲染BQA数据表格"""
        if not result.get("session_results"):
            return

        st.subheader("📋 BQA 数据汇总表格")

        # 收集所有BQA数据
        all_bqas = []
        for session_result in result["session_results"]:
            session_id = session_result.get("session_id", "")
            bqa_list = session_result.get("bqa_list", {})
            bqa_items = bqa_list.get("items", []) if isinstance(bqa_list, dict) else getattr(bqa_list, "items", [])

            for bqa in bqa_items:
                background = bqa.get("background", "") if isinstance(bqa, dict) else getattr(bqa, "background", "")
                question = bqa.get("question", "") if isinstance(bqa, dict) else getattr(bqa, "question", "")
                answer = bqa.get("answer", "") if isinstance(bqa, dict) else getattr(bqa, "answer", "")

                all_bqas.append({
                    "会话ID": session_id,
                    "背景 (B)": background[:80] + ("..." if len(background) > 80 else ""),
                    "问题 (Q)": question[:100] + ("..." if len(question) > 100 else ""),
                    "答案 (A)": answer[:100] + ("..." if len(answer) > 100 else ""),
                    "有背景": "是" if background.strip() else "否"
                })

        if all_bqas:
            # 转换为DataFrame
            df = pd.DataFrame(all_bqas)
            df.insert(0, "序号", range(1, len(df) + 1))

            # 使用streamlit的数据表格组件
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "序号": st.column_config.NumberColumn("序号", width="small"),
                    "会话ID": st.column_config.TextColumn("会话ID", width="small"),
                    "背景 (B)": st.column_config.TextColumn("背景 (B)", width="large"),
                    "问题 (Q)": st.column_config.TextColumn("问题 (Q)", width="large"),
                    "答案 (A)": st.column_config.TextColumn("答案 (A)", width="large"),
                    "有背景": st.column_config.TextColumn("有背景", width="small")
                }
            )

            # 统计信息
            total_bqas = len(all_bqas)
            with_background = sum(1 for bqa in all_bqas if bqa["有背景"] == "是")
            background_ratio = with_background / total_bqas if total_bqas > 0 else 0

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("总BQA数", total_bqas)
            with col2:
                st.metric("带背景BQA", with_background)
            with col3:
                st.metric("背景比例", f"{background_ratio:.1%}")
        else:
            st.info("暂无BQA数据")

    def _render_export_section(self, result: Dict[str, Any]):
        """渲染导出区域"""
        st.subheader("💾 导出数据")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("📊 导出 BQA 数据为 CSV"):
                # 收集所有BQA数据用于导出
                all_bqas = []
                for session_result in result.get("session_results", []):
                    session_id = session_result.get("session_id", "")
                    bqa_list = session_result.get("bqa_list", {})
                    bqa_items = bqa_list.get("items", []) if isinstance(bqa_list, dict) else getattr(bqa_list, "items", [])

                    for bqa in bqa_items:
                        background = bqa.get("background", "") if isinstance(bqa, dict) else getattr(bqa, "background", "")
                        question = bqa.get("question", "") if isinstance(bqa, dict) else getattr(bqa, "question", "")
                        answer = bqa.get("answer", "") if isinstance(bqa, dict) else getattr(bqa, "answer", "")

                        all_bqas.append({
                            "session_id": session_id,
                            "background": background,
                            "question": question,
                            "answer": answer
                        })

                if all_bqas:
                    bqa_df = pd.DataFrame(all_bqas)
                    csv = bqa_df.to_csv(index=False)
                    st.download_button(
                        label="下载 BQA CSV 文件",
                        data=csv,
                        file_name=f"bqa_extract_data_{int(time.time())}.csv",
                        mime="text/csv"
                    )
                else:
                    st.error("没有可导出的BQA数据")

        with col2:
            if st.button("📁 导出会话结果为 JSON"):
                if result.get("session_results"):
                    import json
                    session_json = json.dumps(
                        result,
                        ensure_ascii=False,
                        indent=2,
                        default=str  # 处理不可序列化的对象
                    )
                    st.download_button(
                        label="下载会话结果 JSON 文件",
                        data=session_json,
                        file_name=f"bqa_extract_sessions_{int(time.time())}.json",
                        mime="application/json"
                    )
                else:
                    st.error("没有可导出的会话数据")