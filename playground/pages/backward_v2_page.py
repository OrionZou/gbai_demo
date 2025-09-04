"""
Backward V2 API测试页面
"""
import streamlit as st
import pandas as pd
import requests
import time
import json
from typing import Dict, Any
from components.common import PageHeader, ResultDisplay, DataPreview
from components.forms import BackwardV2TestForm
from config.examples import BACKWARD_V2_EXAMPLES


class BackwardV2Page:
    """Backward V2 API测试页面"""
    
    def __init__(self, service_manager):
        self.service_manager = service_manager
        self.api_url = service_manager.base_url
    
    def render(self):
        """渲染Backward V2页面"""
        st.header("↩️ Backward V2 API 测试")
        
        col1, col2 = st.columns([3, 2])
        
        with col1:
            self._render_test_form()
        
        with col2:
            self._render_results()
    
    def _render_test_form(self):
        """渲染测试表单"""
        test_data = BackwardV2TestForm.render(BACKWARD_V2_EXAMPLES)
        
        if test_data:
            self._execute_backward_v2_test(test_data)
    
    def _execute_backward_v2_test(self, test_data: Dict[str, Any]):
        """执行Backward V2测试"""
        try:
            with st.spinner("正在执行 Backward V2 处理..."):
                response = requests.post(
                    f"{self.api_url}/backward_v2",
                    json=test_data,
                    timeout=120
                )
            
            if response.status_code == 200:
                result = response.json()
                ResultDisplay.show_success("处理完成！")
                # 保存结果
                st.session_state.backward_v2_result = result
            else:
                ResultDisplay.show_error(
                    f"处理失败: {response.status_code}",
                    response.text
                )
        except Exception as e:
            ResultDisplay.show_error("请求失败", str(e))
    
    def _render_results(self):
        """渲染处理结果"""
        st.subheader("📊 处理结果")
        
        if 'backward_v2_result' in st.session_state:
            result = st.session_state.backward_v2_result
            
            # 基本统计信息
            self._render_metrics(result)
            
            # 操作日志
            self._render_operation_log(result)
            
            # 章节结构树状预览
            self._render_chapter_structure(result)
            
            # OSPA数据预览
            self._render_ospa_data(result)
            
            # 完整结果查看
            with st.expander("🔍 查看完整结果 JSON"):
                st.json(result)
            
            # 导出功能
            self._render_export_section(result)
        else:
            st.info("暂无处理结果")
    
    def _render_metrics(self, result: Dict[str, Any]):
        """渲染基本指标"""
        col_a, col_b = st.columns(2)
        with col_a:
            chapter_count = len(result.get("chapter_structure", {}).get("nodes", {}))
            st.metric("章节数", chapter_count)
        with col_b:
            ospa_count = len(result.get("ospa_list", []))
            st.metric("OSPA条目", ospa_count)
    
    def _render_operation_log(self, result: Dict[str, Any]):
        """渲染操作日志"""
        if result.get("operation_log"):
            st.write("**操作日志**:")
            for i, log in enumerate(result["operation_log"]):
                st.write(f"{i+1}. {log}")
    
    def _render_chapter_structure(self, result: Dict[str, Any]):
        """渲染章节结构"""
        if result.get("chapter_structure"):
            with st.expander("🗂️ 查看章节结构（树状视图）", expanded=True):
                chapter_nodes = result["chapter_structure"].get("nodes", {})
                root_ids = result["chapter_structure"].get("root_ids", [])
                
                if root_ids:
                    st.write("### 📊 章节层次结构")
                    for i, root_id in enumerate(root_ids):
                        root_node = chapter_nodes.get(root_id)
                        if root_node:
                            self._display_tree_node(
                                root_node, chapter_nodes, 0, 
                                i == len(root_ids) - 1, ""
                            )
                            if i < len(root_ids) - 1:
                                st.write("")
                    
                    # 章节统计信息
                    self._render_chapter_stats(result)
                else:
                    st.info("章节结构为空或格式不正确")
    
    def _display_tree_node(self, node: Dict[str, Any], all_nodes: Dict[str, Any], 
                          level: int = 0, is_last: bool = True, prefix: str = ""):
        """递归显示树状结构节点"""
        # 创建树状显示的前缀
        if level == 0:
            tree_prefix = ""
            current_prefix = ""
        else:
            tree_prefix = prefix + ("└── " if is_last else "├── ")
            current_prefix = prefix + ("    " if is_last else "│   ")
        
        # 显示当前节点
        title = node.get('title', 'Unknown')
        chapter_num = node.get('chapter_number', '')
        related_count = len(node.get('related_cqa_items', []))
        
        st.write(f"{tree_prefix}📁 **{chapter_num}{title}**")
        if node.get('description'):
            st.write(f"{current_prefix}   📝 {node['description']}")
        
        # 显示章节内容（生成的提示词）
        if node.get('content'):
            content = node['content']
            if len(content) > 80:
                content_preview = content[:80] + "..."
                st.write(f"{current_prefix}   🎯 提示词: {content_preview}")
                with st.expander(f"查看完整提示词 ({len(content)} 字符)", expanded=False):
                    st.code(content, language="text")
            else:
                st.write(f"{current_prefix}   🎯 提示词: {content}")
        
        if related_count > 0:
            st.write(f"{current_prefix}   💬 包含 {related_count} 个问答对")
        
        # 递归显示子节点
        children = node.get('children', [])
        if children:
            for i, child_id in enumerate(children):
                child_node = all_nodes.get(child_id)
                if child_node:
                    is_last_child = (i == len(children) - 1)
                    self._display_tree_node(
                        child_node, all_nodes, level + 1, 
                        is_last_child, current_prefix
                    )
    
    def _render_chapter_stats(self, result: Dict[str, Any]):
        """渲染章节统计信息"""
        st.write("---")
        chapter_nodes = result["chapter_structure"].get("nodes", {})
        total_nodes = len(chapter_nodes)
        total_qas = sum(len(node.get('related_cqa_items', [])) for node in chapter_nodes.values())
        max_level = result["chapter_structure"].get("max_level", 0)
        
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        with col_stat1:
            st.metric("总章节数", total_nodes)
        with col_stat2:
            st.metric("总问答数", total_qas)
        with col_stat3:
            st.metric("最大层级", max_level)
    
    def _render_ospa_data(self, result: Dict[str, Any]):
        """渲染OSPA数据"""
        if result.get("ospa_list"):
            with st.expander(f"📋 查看OSPA数据详情 ({len(result['ospa_list'])} 条)", expanded=False):
                # 显示模式选择
                display_mode = st.radio(
                    "显示模式",
                    ["表格概览", "详细展开"],
                    key="ospa_display_mode",
                    horizontal=True
                )
                
                if display_mode == "表格概览":
                    self._render_ospa_table(result["ospa_list"])
                else:
                    self._render_ospa_detailed(result["ospa_list"])
                
                # OSPA数据统计
                self._render_ospa_stats(result["ospa_list"])
    
    def _render_ospa_table(self, ospa_list: list):
        """渲染OSPA表格概览"""
        ospa_df = pd.DataFrame([
            {
                "序号": i+1,
                "观察(O)": ospa.get("o", "")[:60] + "..." if len(ospa.get("o", "")) > 60 else ospa.get("o", ""),
                "场景(S)": ospa.get("s", "")[:25] + "..." if len(ospa.get("s", "")) > 25 else ospa.get("s", ""),
                "提示词长度": f"{len(ospa.get('p', ''))} 字符",
                "回答(A)": ospa.get("a", "")[:60] + "..." if len(ospa.get("a", "")) > 60 else ospa.get("a", "")
            }
            for i, ospa in enumerate(ospa_list[:15])
        ])
        st.dataframe(ospa_df, use_container_width=True)
        
        if len(ospa_list) > 15:
            st.info(f"📋 共 {len(ospa_list)} 条OSPA数据，表格显示前15条")
    
    def _render_ospa_detailed(self, ospa_list: list):
        """渲染OSPA详细展开"""
        max_display = min(len(ospa_list), 10)
        num_to_display = st.slider(
            "显示条目数量",
            min_value=1,
            max_value=max_display,
            value=min(5, max_display),
            key="ospa_detail_count"
        )
        
        st.write(f"### 📋 详细OSPA内容 (显示前{num_to_display}条)")
        
        for i, ospa in enumerate(ospa_list[:num_to_display]):
            with st.container():
                st.write(f"#### 🔢 OSPA条目 {i+1}")
                
                # O - 观察
                st.write("**🔍 观察 (Observation)**")
                st.info(ospa.get("o", "未提供"))
                
                # S - 场景
                st.write("**🎭 场景 (Scenario)**")
                st.success(ospa.get("s", "未提供"))
                
                # P - 提示词
                st.write("**🎯 完整章节提示词 (Prompt)**")
                prompt_content = ospa.get("p", "未提供提示词")
                st.code(prompt_content, language="text")
                
                # A - 回答
                st.write("**💬 标准回答 (Answer)**")
                st.write(ospa.get("a", "未提供"))
                
                if i < num_to_display - 1:
                    st.markdown("---")
        
        if len(ospa_list) > num_to_display:
            remaining = len(ospa_list) - num_to_display
            st.info(f"📋 还有 {remaining} 条OSPA数据未显示")
    
    def _render_ospa_stats(self, ospa_list: list):
        """渲染OSPA统计信息"""
        st.write("---")
        st.write("### 📊 OSPA数据统计")
        
        total_ospa = len(ospa_list)
        avg_prompt_length = sum(len(ospa.get("p", "")) for ospa in ospa_list) / total_ospa if total_ospa > 0 else 0
        scenarios = list(set(ospa.get("s", "") for ospa in ospa_list))
        
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            st.metric("OSPA总数", total_ospa)
        with col_s2:
            st.metric("平均提示词长度", f"{int(avg_prompt_length)} 字符")
        with col_s3:
            st.metric("场景类型数", len(scenarios))
    
    def _render_export_section(self, result: Dict[str, Any]):
        """渲染导出区域"""
        st.write("### 📤 数据导出")
        col_export1, col_export2 = st.columns(2)
        
        with col_export1:
            # 导出OSPA数据
            if st.button("💾 导出 OSPA 数据", key="export_backward_v2_ospa"):
                if result.get("ospa_list"):
                    ospa_df = pd.DataFrame([
                        {
                            "O": ospa.get("o", ""),
                            "S": ospa.get("s", ""),
                            "P": ospa.get("p", ""),
                            "A": ospa.get("a", "")
                        }
                        for ospa in result["ospa_list"]
                    ])
                    csv = ospa_df.to_csv(index=False)
                    st.download_button(
                        label="📄 下载 OSPA CSV 文件",
                        data=csv,
                        file_name=f"backward_v2_ospa_data_{int(time.time())}.csv",
                        mime="text/csv",
                        key="download_ospa_csv"
                    )
        
        with col_export2:
            # 导出章节结构
            if st.button("🗂️ 导出章节结构", key="export_backward_v2_structure"):
                if result.get("chapter_structure"):
                    structure_json = json.dumps(
                        result["chapter_structure"], 
                        ensure_ascii=False, 
                        indent=2
                    )
                    st.download_button(
                        label="📋 下载章节结构 JSON",
                        data=structure_json,
                        file_name=f"chapter_structure_{int(time.time())}.json",
                        mime="application/json",
                        key="download_structure_json"
                    )