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
        
        col1, col2 = st.columns([2, 2])
        
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
                    test_data.get("chapter_structure"),
                    test_data.get("max_level", 3),
                    test_data.get("max_concurrent_llm", 10)
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
            self._render_statistics(result)
            
            # 章节结构树形显示
            self._render_chapter_tree(result)
            
            # OSPA数据表格显示
            self._render_ospa_table(result)
            
            # 导出功能
            self._render_export_section(result)
        else:
            st.info("暂无处理结果")
    
    def _render_statistics(self, result: Dict[str, Any]):
        """渲染统计信息"""
        st.success("✅ 处理完成")
        
        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a:
            st.metric("章节数", result.get("total_chapters", 0))
        with col_b:
            st.metric("问答对数", result.get("total_qas", 0))
        with col_c:
            st.metric("OSPA条目", result.get("total_ospa", 0))
        with col_d:
            processing_time = result.get("processing_time_ms", 0)
            st.metric("处理耗时", f"{processing_time} ms")
        
        if result.get("message"):
            st.info(result["message"])
    
    def _render_chapter_tree(self, result: Dict[str, Any]):
        """渲染章节树形结构"""
        if not result.get("chapter_structure"):
            st.info("⚠️ 结果中没有章节结构数据")
            return
            
        st.subheader("🌳 章节结构")
        
        chapter_structure = result["chapter_structure"]
        nodes = chapter_structure.get("nodes", {})
        root_ids = chapter_structure.get("root_ids", [])
        
        if not nodes:
            st.info("⚠️ 章节结构为空")
            return
        
        if not root_ids:
            st.warning("⚠️ 没有找到根节点，显示所有章节：")
            root_ids = list(nodes.keys())
        
        # 显示简洁的统计信息
        st.caption(f"📊 共 {len(nodes)} 个章节，{len(root_ids)} 个主章节")
        
        # 使用streamlit原生组件创建层次化显示
        def render_chapter_tree_streamlit():
            """使用streamlit组件渲染章节树"""
            
            # 为每个根节点创建独立的展示区域
            for root_id in root_ids:
                if root_id not in nodes:
                    continue
                    
                root_node = nodes[root_id]
                title = root_node.get('title', '未命名章节')
                description = root_node.get("description", "")
                chapter_number = root_node.get("chapter_number", "")
                qa_items = root_node.get("related_qa_items", [])
                children = root_node.get("children", [])
                
                # 计算章节统计信息
                def get_chapter_stats(node_id, visited=None):
                    """递归计算章节及其子章节的统计信息"""
                    if visited is None:
                        visited = set()
                    if node_id in visited or node_id not in nodes:
                        return 0, 0, 0  # qa_count, child_count, total_depth
                    
                    visited.add(node_id)
                    node = nodes[node_id]
                    qa_count = len(node.get("related_qa_items", []))
                    children = node.get("children", [])
                    child_count = len(children)
                    max_depth = 0
                    
                    for child_id in children:
                        child_qa, child_nodes, child_depth = get_chapter_stats(child_id, visited)
                        qa_count += child_qa
                        child_count += child_nodes
                        max_depth = max(max_depth, child_depth + 1)
                    
                    return qa_count, child_count, max_depth
                
                total_qa, total_children, max_depth = get_chapter_stats(root_id)
                
                # 构建expander标题，显示层次统计
                if total_children > 0:
                    title_suffix = f" - {total_qa} 个问答，{total_children} 个子章节"
                else:
                    title_suffix = f" - {total_qa} 个问答"
                
                # 根节点使用expander
                with st.expander(f"🏛️ {chapter_number} {title}{title_suffix}", expanded=True):
                    if description:
                        st.info(description)
                    
                    # 显示根节点的问答对
                    if qa_items:
                        st.markdown("**📝 直属问答对：**")
                        for i, qa_item in enumerate(qa_items[:3]):
                            q_text = qa_item.get("question", qa_item.get("q", ""))
                            st.markdown(f"  `{i+1}.` {q_text}")
                        
                        if len(qa_items) > 3:
                            st.caption(f"  ... 还有 {len(qa_items) - 3} 个问答对")
                    
                    # 渲染子章节
                    if children:
                        st.markdown("**📂 子章节结构：**")
                        
                        # 先显示子章节概览
                        cols = st.columns(3)
                        for i, child_id in enumerate(children[:3]):
                            if child_id in nodes:
                                child_node = nodes[child_id]
                                child_title = child_node.get('title', '未命名')
                                child_qa_count = len(child_node.get("related_qa_items", []))
                                with cols[i % 3]:
                                    st.metric(
                                        label=f"📁 {child_node.get('chapter_number', '')} {child_title}",
                                        value=f"{child_qa_count} 问答"
                                    )
                        
                        if len(children) > 3:
                            st.caption(f"... 还有 {len(children) - 3} 个子章节")
                        
                        st.markdown("---")
                        render_children_recursive(children, level=1)
        
        def render_children_recursive(child_ids, level=1):
            """递归渲染子章节"""
            for child_id in child_ids:
                if child_id not in nodes:
                    continue
                    
                child_node = nodes[child_id]
                title = child_node.get('title', '未命名章节')
                description = child_node.get("description", "")
                chapter_number = child_node.get("chapter_number", "")
                qa_items = child_node.get("related_qa_items", [])
                grandchildren = child_node.get("children", [])
                
                # 根据层级选择缩进
                indent = "　　" * level
                
                if level == 1:
                    icon = "📁"
                    style = "**"
                elif level == 2:
                    icon = "📂"  
                    style = "*"
                else:
                    icon = "📄"
                    style = ""
                
                # 章节标题
                if style:
                    st.markdown(f"{indent}{icon} {style}{chapter_number} {title}{style}")
                else:
                    st.markdown(f"{indent}{icon} {chapter_number} {title}")
                
                if description:
                    st.markdown(f"{indent}　*{description}*")
                
                # 问答对
                if qa_items:
                    qa_count = len(qa_items)
                    st.markdown(f"{indent}　📝 {qa_count} 个问答对")
                    
                    for i, qa_item in enumerate(qa_items[:2]):
                        q_text = qa_item.get("question", qa_item.get("q", ""))
                        q_short = q_text[:45] + ("..." if len(q_text) > 45 else "")
                        st.markdown(f"{indent}　　• {q_short}")
                    
                    if qa_count > 2:
                        st.markdown(f"{indent}　　... 还有 {qa_count - 2} 个")
                
                # 递归显示更深层级的子章节
                if grandchildren and level < 3:
                    render_children_recursive(grandchildren, level + 1)
        
        # 调用渲染函数
        render_chapter_tree_streamlit()
        
        # 提供展开查看详细结构的选项
        with st.expander("🔍 查看详细章节结构"):
            st.json(chapter_structure)
    
    def _render_ospa_table(self, result: Dict[str, Any]):
        """渲染OSPA数据表格"""
        if not result.get("ospa"):
            return
            
        st.subheader("📋 OSPA 数据表格")
        
        ospa_data = result["ospa"]
        
        # 转换为DataFrame用于表格显示
        table_data = []
        for i, ospa in enumerate(ospa_data, 1):
            table_data.append({
                "序号": i,
                "问题 (O)": ospa.get("o", "")[:100] + ("..." if len(ospa.get("o", "")) > 100 else ""),
                "场景 (S)": ospa.get("s", "")[:50] + ("..." if len(ospa.get("s", "")) > 50 else ""),
                "提示词 (P)": ospa.get("p", "")[:80] + ("..." if len(ospa.get("p", "")) > 80 else ""),
                "答案 (A)": ospa.get("a", "")[:100] + ("..." if len(ospa.get("a", "")) > 100 else "")
            })
        
        df = pd.DataFrame(table_data)
        
        # 使用streamlit的数据表格组件
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "序号": st.column_config.NumberColumn("序号", width="small"),
                "问题 (O)": st.column_config.TextColumn("问题 (O)", width="large"),
                "场景 (S)": st.column_config.TextColumn("场景 (S)", width="medium"),
                "提示词 (P)": st.column_config.TextColumn("提示词 (P)", width="large"),
                "答案 (A)": st.column_config.TextColumn("答案 (A)", width="large")
            }
        )
        
        # 详细查看选项
        st.write("**💡 提示**: 点击下方展开查看完整OSPA条目详情")
        
        # 分页显示详细内容
        items_per_page = 5
        total_pages = (len(ospa_data) + items_per_page - 1) // items_per_page
        
        if total_pages > 1:
            page = st.selectbox(
                "选择页面",
                range(1, total_pages + 1),
                format_func=lambda x: f"第 {x} 页 (条目 {(x-1)*items_per_page + 1}-{min(x*items_per_page, len(ospa_data))})"
            )
            start_idx = (page - 1) * items_per_page
            end_idx = min(start_idx + items_per_page, len(ospa_data))
            page_data = ospa_data[start_idx:end_idx]
        else:
            page_data = ospa_data
        
        # 显示详细内容
        for i, ospa in enumerate(page_data):
            actual_idx = (page - 1) * items_per_page + i + 1 if total_pages > 1 else i + 1
            with st.expander(f"📄 OSPA 条目 {actual_idx}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**🎯 问题 (O):**")
                    st.write(ospa.get("o", ""))
                    st.write("**🏷️ 场景 (S):**")
                    st.write(ospa.get("s", ""))
                with col2:
                    st.write("**💡 提示词 (P):**")
                    st.write(ospa.get("p", ""))
                    st.write("**✅ 答案 (A):**")
                    st.write(ospa.get("a", ""))
    
    def _render_export_section(self, result: Dict[str, Any]):
        """渲染导出区域"""
        st.subheader("💾 导出数据")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📊 导出 OSPA 数据为 CSV"):
                if result.get("ospa"):
                    ospa_df = pd.DataFrame(result["ospa"])
                    csv = ospa_df.to_csv(index=False)
                    st.download_button(
                        label="下载 OSPA CSV 文件",
                        data=csv,
                        file_name=f"ospa_data_{int(time.time())}.csv",
                        mime="text/csv"
                    )
        
        with col2:
            if st.button("🌳 导出章节结构为 JSON"):
                if result.get("chapter_structure"):
                    import json
                    chapter_json = json.dumps(
                        result["chapter_structure"], 
                        ensure_ascii=False, 
                        indent=2
                    )
                    st.download_button(
                        label="下载章节结构 JSON 文件",
                        data=chapter_json,
                        file_name=f"chapter_structure_{int(time.time())}.json",
                        mime="application/json"
                    )