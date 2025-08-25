import streamlit as st

# 配置页面设置
st.set_page_config(
    page_title="Agent Runtime Playground",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 导入并运行主要功能页面
agent_runtime_playground = st.Page(
    "agent_runtime_playground.py", 
    title="Agent Runtime API", 
    icon="🤖"
)

# 创建导航
pg = st.navigation([agent_runtime_playground])
pg.run()