"""
重构后的 Agent Runtime API Playground 主应用
采用模块化架构，提升代码可维护性
"""

import os
import streamlit as st

# 导入配置
from config.settings import AppConfig, UIConfig

# 导入组件
from components.common import PageHeader, ConfigPanel

# 导入API服务
from api_services import ServiceManager
from ospa_models import OSPAManager
from ospa_utils import OSPAProcessor

# 导入页面
from pages.config_page import ConfigPage
from pages.reward_page import RewardPage
from pages.backward_page import BackwardPage
from pages.ospa_page import OSPAPage
from pages.agent_page import AgentPage


class PlaygroundApp:
    """Playground主应用类"""

    def __init__(self):
        self.setup_page_config()
        self.initialize_session_state()
        self.setup_services()

    def setup_page_config(self):
        """设置页面配置"""
        st.set_page_config(
            page_title=AppConfig.PAGE_TITLE,
            page_icon="🤖",
            layout="wide",
            initial_sidebar_state="expanded",
        )

    def initialize_session_state(self):
        """初始化会话状态"""
        # 初始化OSPA管理器
        if "ospa_manager" not in st.session_state:
            st.session_state.ospa_manager = OSPAManager()

        # 初始化服务管理器
        if "service_manager" not in st.session_state:
            st.session_state.service_manager = None

        # 初始化处理器
        if "processor" not in st.session_state:
            st.session_state.processor = None

    def setup_services(self):
        """设置服务"""
        # API URL配置
        api_url = ConfigPanel.render_api_config(AppConfig.get_api_url())

        # 更新服务管理器
        if (
            st.session_state.service_manager is None
            or st.session_state.service_manager.base_url != api_url
        ):
            st.session_state.service_manager = ServiceManager(api_url)
            st.session_state.processor = OSPAProcessor(st.session_state.service_manager)

        self.service_manager = st.session_state.service_manager
        self.processor = st.session_state.processor

    def render_header(self):
        """渲染页面头部"""
        PageHeader.render(
            title=AppConfig.PAGE_TITLE,
            description="",
            show_connection_status=True,
            api_url=self.service_manager.base_url,
        )

    def render_tabs(self):
        """渲染标签页"""
        # 创建标签页
        tab_names = [tab["name"] for tab in UIConfig.TAB_CONFIG]
        tabs = st.tabs(tab_names)

        # 渲染各个标签页
        for i, tab_config in enumerate(UIConfig.TAB_CONFIG):
            with tabs[i]:
                self.render_tab_content(tab_config["key"])

    def render_tab_content(self, tab_key: str):
        """渲染标签页内容"""
        try:
            if tab_key == "config":
                page = ConfigPage(self.service_manager)
                page.render()
            elif tab_key == "reward":
                page = RewardPage(self.service_manager)
                page.render()
            elif tab_key == "backward":
                page = BackwardPage(self.service_manager)
                page.render()
            elif tab_key == "ospa":
                page = OSPAPage(self.service_manager)
                page.render()
            elif tab_key == "agent":
                page = AgentPage(self.service_manager)
                page.render()
            else:
                st.error(f"未知的页面类型: {tab_key}")
        except Exception as e:
            st.error(f"页面渲染失败: {str(e)}")
            st.exception(e)

    def render_footer(self):
        """渲染页面底部"""
        st.markdown("---")
        st.markdown(f"🤖 **{AppConfig.PAGE_TITLE}** | {AppConfig.PAGE_DESCRIPTION}")

    def run(self):
        """运行应用"""
        try:
            self.render_header()
            self.render_tabs()
            self.render_footer()
        except Exception as e:
            st.error(f"应用运行失败: {str(e)}")
            st.exception(e)


def main():
    """主函数"""
    app = PlaygroundApp()
    app.run()


if __name__ == "__main__":
    main()
