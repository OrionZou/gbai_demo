"""
通用UI组件
提供常用的界面元素和工具函数
"""
import streamlit as st
from typing import Dict, Any, Optional, List, Tuple
import time


class PageHeader:
    """页面头部组件"""
    
    @staticmethod
    def render(title: str, description: str = "", show_connection_status: bool = True, api_url: str = ""):
        """渲染页面头部"""
        st.title(title)
        if description:
            st.markdown(description)
        
        if show_connection_status and api_url:
            PageHeader._render_connection_status(api_url)
    
    @staticmethod
    def _render_connection_status(api_url: str):
        """渲染连接状态"""
        col1, col2 = st.columns([3, 1])
        
        with col1:
            try:
                import requests
                response = requests.get(f"{api_url}/docs", timeout=5)
                if response.status_code == 200:
                    st.success("✅ API 连接正常")
                else:
                    st.error("❌ API 连接失败")
            except Exception:
                st.error("❌ API 连接失败，请检查 URL 或启动 Agent Runtime 服务")
        
        with col2:
            if st.button("🔄 重新检查", help="重新检查 API 连接状态"):
                st.rerun()


class ResultDisplay:
    """结果显示组件"""
    
    @staticmethod
    def show_success(message: str, details: Optional[Dict[str, Any]] = None):
        """显示成功消息"""
        st.success(f"✅ {message}")
        if details:
            with st.expander("查看详细信息"):
                st.json(details)
    
    @staticmethod
    def show_error(error: str, details: Optional[str] = None):
        """显示错误消息"""
        st.error(f"❌ {error}")
        if details:
            with st.expander("错误详情"):
                st.code(details)
    
    @staticmethod
    def show_metrics(metrics: Dict[str, Any], columns: int = 4):
        """显示指标"""
        cols = st.columns(columns)
        
        for i, (label, value) in enumerate(metrics.items()):
            with cols[i % columns]:
                if isinstance(value, (int, float)):
                    st.metric(label, value)
                else:
                    st.metric(label, str(value))
    
    @staticmethod
    def show_processing_time(start_time: float, end_time: float):
        """显示处理时间"""
        processing_time = end_time - start_time
        st.info(f"⏱️ 处理耗时: {processing_time:.2f} 秒")


class FormHelpers:
    """表单辅助组件"""
    
    @staticmethod
    def render_text_input_with_example(
        label: str, 
        key: str, 
        example_value: str = "",
        help_text: str = "",
        placeholder: str = ""
    ) -> str:
        """渲染带示例的文本输入"""
        value = st.text_input(
            label, 
            value=example_value, 
            key=key, 
            help=help_text,
            placeholder=placeholder
        )
        return value
    
    @staticmethod
    def render_text_area_with_example(
        label: str, 
        key: str, 
        example_value: str = "",
        height: int = 100,
        help_text: str = ""
    ) -> str:
        """渲染带示例的文本区域"""
        value = st.text_area(
            label, 
            value=example_value, 
            key=key, 
            height=height,
            help=help_text
        )
        return value
    
    @staticmethod
    def render_file_uploader_with_example(
        label: str,
        file_types: List[str],
        help_text: str = "",
        example_download_data: Optional[str] = None,
        example_filename: str = "example.csv"
    ) -> Optional[Any]:
        """渲染带示例下载的文件上传器"""
        col1, col2 = st.columns([3, 1])
        
        with col1:
            uploaded_file = st.file_uploader(label, type=file_types, help=help_text)
        
        with col2:
            if example_download_data:
                st.download_button(
                    label="📥 下载示例",
                    data=example_download_data,
                    file_name=example_filename,
                    mime="text/csv" if example_filename.endswith('.csv') else "application/json"
                )
        
        return uploaded_file
    
    @staticmethod
    def render_number_input_with_range(
        label: str,
        min_value: float,
        max_value: float,
        default_value: float,
        step: float = 0.1,
        key: Optional[str] = None,
        help_text: str = ""
    ) -> float:
        """渲染带范围的数字输入"""
        return st.number_input(
            label,
            min_value=min_value,
            max_value=max_value,
            value=default_value,
            step=step,
            key=key,
            help=help_text
        )


class ProgressTracker:
    """进度跟踪组件"""
    
    def __init__(self, title: str = "处理进度"):
        self.title = title
        self.progress_bar = None
        self.status_placeholder = None
        
    def start(self):
        """开始进度跟踪"""
        st.write(f"**{self.title}**")
        self.progress_bar = st.progress(0)
        self.status_placeholder = st.empty()
        
    def update(self, progress: float, status: str = ""):
        """更新进度"""
        if self.progress_bar:
            self.progress_bar.progress(progress)
        if self.status_placeholder and status:
            self.status_placeholder.info(status)
            
    def finish(self, success_message: str = "处理完成"):
        """完成进度跟踪"""
        if self.progress_bar:
            self.progress_bar.empty()
        if self.status_placeholder:
            self.status_placeholder.empty()
        st.success(success_message)


class DataPreview:
    """数据预览组件"""
    
    @staticmethod
    def show_dataframe_preview(
        df,
        title: str = "数据预览",
        max_rows: int = 10,
        show_stats: bool = True
    ):
        """显示DataFrame预览"""
        with st.expander(f"📋 {title}", expanded=False):
            if show_stats:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("总行数", len(df))
                with col2:
                    st.metric("列数", len(df.columns))
                with col3:
                    st.metric("预览行数", min(max_rows, len(df)))
            
            st.dataframe(df.head(max_rows), use_container_width=True)
            
            if len(df) > max_rows:
                st.info(f"显示前 {max_rows} 行，共 {len(df)} 行")
    
    @staticmethod
    def show_list_preview(
        data_list: List[Dict[str, Any]],
        title: str = "数据预览",
        max_items: int = 5,
        key_fields: List[str] = None
    ):
        """显示列表数据预览"""
        with st.expander(f"📋 {title}", expanded=False):
            st.write(f"**总条目数**: {len(data_list)}")
            
            for i, item in enumerate(data_list[:max_items]):
                st.write(f"**条目 {i+1}**:")
                if key_fields:
                    for field in key_fields:
                        if field in item:
                            value = str(item[field])
                            if len(value) > 100:
                                value = value[:100] + "..."
                            st.write(f"  - {field}: {value}")
                else:
                    st.json(item)
                
            if len(data_list) > max_items:
                st.info(f"显示前 {max_items} 条，共 {len(data_list)} 条")


class ExportHelpers:
    """导出辅助组件"""
    
    @staticmethod
    def render_download_button(
        data: str,
        filename: str,
        label: str = "下载文件",
        mime_type: str = "text/plain",
        key: Optional[str] = None
    ):
        """渲染下载按钮"""
        return st.download_button(
            label=label,
            data=data,
            file_name=filename,
            mime=mime_type,
            key=key
        )
    
    @staticmethod
    def render_export_section(export_options: Dict[str, Dict[str, Any]]):
        """渲染导出区域"""
        st.write("### 📤 数据导出")
        
        if len(export_options) <= 2:
            cols = st.columns(len(export_options))
        else:
            cols = st.columns(3)
        
        for i, (option_name, config) in enumerate(export_options.items()):
            with cols[i % len(cols)]:
                if st.button(f"💾 {option_name}", key=f"export_{option_name.lower()}"):
                    ExportHelpers.render_download_button(
                        data=config['data'],
                        filename=config['filename'],
                        label=config.get('label', f"下载 {option_name}"),
                        mime_type=config.get('mime_type', 'text/plain'),
                        key=f"download_{option_name.lower()}"
                    )


class StatusIndicator:
    """状态指示器组件"""
    
    @staticmethod
    def show_connection_status(is_connected: bool, service_name: str = "API"):
        """显示连接状态"""
        if is_connected:
            st.success(f"✅ {service_name} 连接正常")
        else:
            st.error(f"❌ {service_name} 连接失败")
    
    @staticmethod
    def show_data_status(
        total_items: int,
        valid_items: int,
        processed_items: int = 0,
        error_items: int = 0
    ):
        """显示数据状态"""
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("总数据", total_items)
        with col2:
            st.metric("有效数据", valid_items)
        with col3:
            if processed_items > 0:
                st.metric("已处理", processed_items, delta=processed_items - valid_items)
            else:
                st.metric("待处理", valid_items)
        with col4:
            if error_items > 0:
                st.metric("错误数", error_items, delta=-error_items)
            else:
                st.metric("错误数", 0)


class ConfigPanel:
    """配置面板组件"""
    
    @staticmethod
    def render_api_config(default_url: str = "http://localhost:8011/agent") -> str:
        """渲染API配置"""
        api_url = st.text_input(
            "Agent Runtime API URL",
            value=default_url,
            key="api_url_input",
            help="Agent Runtime API 的基础URL"
        )
        return api_url
    
    @staticmethod
    def render_processing_config() -> Dict[str, Any]:
        """渲染处理配置"""
        with st.expander("🔧 处理配置", expanded=False):
            enable_concurrent = st.checkbox("启用并发处理", value=True)
            max_concurrent = st.selectbox(
                "最大并发数", 
                [1, 3, 5, 8, 10, 15], 
                index=3
            )
            temperature = st.slider(
                "生成温度", 
                min_value=0.0, 
                max_value=2.0, 
                value=0.3, 
                step=0.1
            )
            
        return {
            'enable_concurrent': enable_concurrent,
            'max_concurrent': max_concurrent,
            'temperature': temperature
        }