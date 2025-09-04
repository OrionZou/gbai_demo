"""
Reward API测试页面
"""
import streamlit as st
import requests
import time
from typing import Dict, Any
from components.common import PageHeader, ResultDisplay
from components.forms import RewardTestForm
from config.examples import REWARD_EXAMPLES


class RewardPage:
    """Reward API测试页面"""
    
    def __init__(self, service_manager):
        self.service_manager = service_manager
        self.api_url = service_manager.base_url
    
    def render(self):
        """渲染Reward页面"""
        st.header("🏆 Reward API 测试")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            self._render_test_form()
        
        with col2:
            self._render_results()
    
    def _render_test_form(self):
        """渲染测试表单"""
        test_data = RewardTestForm.render(REWARD_EXAMPLES)
        
        if test_data:
            self._execute_reward_test(test_data)
    
    def _execute_reward_test(self, test_data: Dict[str, Any]):
        """执行Reward测试"""
        try:
            with st.spinner("正在执行语义一致性分析..."):
                response = requests.post(
                    f"{self.api_url}/reward",
                    json=test_data,
                    timeout=30
                )
            
            if response.status_code == 200:
                result = response.json()
                ResultDisplay.show_success("测试完成！")
                
                # 保存到会话状态
                self._save_result(test_data["question"], result)
            else:
                ResultDisplay.show_error(
                    f"测试失败: {response.status_code}",
                    response.text
                )
        except Exception as e:
            ResultDisplay.show_error("请求失败", str(e))
    
    def _save_result(self, question: str, result: Dict[str, Any]):
        """保存测试结果"""
        if 'reward_results' not in st.session_state:
            st.session_state.reward_results = []
        
        st.session_state.reward_results.append({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "question": question,
            "result": result
        })
    
    def _render_results(self):
        """渲染测试结果"""
        st.subheader("📊 测试结果")
        
        if ('reward_results' in st.session_state and 
            st.session_state.reward_results):
            
            # 显示最新结果
            latest_result = st.session_state.reward_results[-1]
            st.write(f"**最新测试时间**: {latest_result['timestamp']}")
            st.write(f"**问题**: {latest_result['question'][:50]}...")
            
            with st.expander("查看详细结果", expanded=True):
                st.json(latest_result['result'])
            
            # 历史记录
            self._render_history()
            
            if st.button("🗑️ 清空历史", key="clear_reward_history"):
                st.session_state.reward_results = []
                st.rerun()
        else:
            st.info("暂无测试结果")
    
    def _render_history(self):
        """渲染历史记录"""
        if len(st.session_state.reward_results) > 1:
            with st.expander(
                f"历史记录 ({len(st.session_state.reward_results)-1} 条)"
            ):
                for i, result in enumerate(
                    reversed(st.session_state.reward_results[:-1])
                ):
                    st.write(f"**{i+1}.** {result['timestamp']}")
                    st.write(f"问题: {result['question'][:30]}...")
                    if st.button(
                        "查看",
                        key=f"view_result_{len(st.session_state.reward_results)-i-2}"
                    ):
                        st.json(result['result'])