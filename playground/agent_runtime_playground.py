"""
Agent Runtime API Playground 启动入口
重构版本 - 使用模块化架构

使用方法:
streamlit run agent_runtime_playground.py
"""
import sys
import os

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 导入重构后的应用
from app import main

# 运行重构后的应用
if __name__ == "__main__":
    main()