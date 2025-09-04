"""
Backward API测试页面
"""
import streamlit as st
import pandas as pd
import time
from typing import Dict, Any
from components.common import PageHeader, ResultDisplay
from components.forms import BackwardTestForm
from config.examples import BACKWARD_EXAMPLES


class BackwardPage:
    """Backward API测试页面"""
    
    def __init__(self, service_manager):
        self.service_manager = service_manager
        self.api_url = service_manager.base_url
    
    def render(self):
        """渲染Backward页面"""
        st.header("↩️ Backward API 测试")
        
        col1, col2 = st.columns([3, 2])
        
        with col1:
            self._render_test_form()
        
        with col2:
            self._render_results()
    
    def _render_test_form(self):
        """渲染测试表单"""
        test_data = BackwardTestForm.render(BACKWARD_EXAMPLES)
        
        if test_data:
            self._execute_backward_test(test_data)
    
    def _execute_backward_test(self, test_data: Dict[str, Any]):
        """执行Backward测试"""
        try:
            with st.spinner("正在执行问答对聚合处理..."):
                result = self.service_manager.backward_service.process_qas(
                    test_data["qas"],
                    test_data["chapters_extra_instructions"],
                    test_data["gen_p_extra_instructions"]
                )
            
            ResultDisplay.show_success("处理完成！")
            # 保存结果
            st.session_state.backward_result = result
            
        except Exception as e:
            ResultDisplay.show_error("处理失败", str(e))
    
    def _render_results(self):
        """渲染处理结果"""
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
            self._render_export_section(result)
        else:
            st.info("暂无处理结果")
    
    def _render_export_section(self, result: Dict[str, Any]):
        """渲染导出区域"""
        if st.button("💾 导出 OSPA 数据为 CSV"):
            if result.get("ospa"):
                ospa_df = pd.DataFrame(result["ospa"])
                csv = ospa_df.to_csv(index=False)
                st.download_button(
                    label="下载 CSV 文件",
                    data=csv,
                    file_name=f"ospa_data_{int(time.time())}.csv",
                    mime="text/csv"
                )