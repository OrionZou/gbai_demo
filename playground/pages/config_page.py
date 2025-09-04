"""
LLM配置页面
"""
import streamlit as st
from components.common import PageHeader, ResultDisplay
from components.forms import ConfigForm


class ConfigPage:
    """LLM配置页面"""
    
    def __init__(self, service_manager):
        self.service_manager = service_manager
    
    def render(self):
        """渲染配置页面"""
        st.header("🔧 LLM 配置管理")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            self._render_current_config()
        
        with col2:
            self._render_config_form()
    
    def _render_current_config(self):
        """渲染当前配置显示"""
        st.subheader("📋 当前配置")
        
        if st.button("📥 获取当前配置", key="get_config"):
            try:
                config = self.service_manager.config_service.get_config()
                st.session_state.current_config = config
                ResultDisplay.show_success("配置获取成功！")
                st.json(config)
            except Exception as e:
                ResultDisplay.show_error("获取配置失败", str(e))
        
        # 显示已保存的配置
        if 'current_config' in st.session_state:
            st.json(st.session_state.current_config)
    
    def _render_config_form(self):
        """渲染配置表单"""
        st.subheader("⚙️ 更新配置")
        
        config_data = ConfigForm.render_llm_config()
        
        if config_data:
            try:
                result = self.service_manager.config_service.update_config(config_data)
                ResultDisplay.show_success("配置更新成功！", result)
                # 更新会话状态
                st.session_state.current_config = result.get("config", config_data)
            except Exception as e:
                ResultDisplay.show_error("配置更新失败", str(e))