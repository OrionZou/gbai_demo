"""
OSPA相关工具函数
提供数据处理、验证和转换功能
"""
import io
import pandas as pd
import streamlit as st
from pathlib import Path
from charset_normalizer import from_path, from_bytes
from typing import List, Dict, Any, Callable, Optional, Union, IO
from ospa_models import OSPAItem, OSPAManager
from api_services import ServiceManager, run_async_in_streamlit


class OSPADataLoader:
    """OSPA数据加载器"""

    @staticmethod
    def load_from_csv_file(uploaded_file: Union[str, Path, IO[bytes]]) -> OSPAManager:
        """
        从上传的 CSV 文件加载数据（自动探测编码）。
        支持:
        - 文件路径 (str/Path)
        - 二进制文件流 (e.g., FastAPI UploadFile.file / Flask/Django 上传对象)
        """
        tried_encodings = []  # 记录尝试过的编码，便于报错时提示

        def _process_df_from_bytes(raw: bytes) -> pd.DataFrame:
            # 1) 用 charset-normalizer 从字节流探测
            probe = from_bytes(raw).best()
            detected = (probe.encoding if probe else None) or "utf-8"
            tried_encodings.append(f"detected:{detected}")

            # 2) 先用探测到的编码尝试
            try:
                return pd.read_csv(io.BytesIO(raw), encoding=detected)
            except Exception:
                # 3) 常见中文/西文编码回退
                fallbacks = ["utf-8-sig", "gbk", "gb18030", "latin1"]
                for enc in fallbacks:
                    if enc not in tried_encodings:
                        try:
                            tried_encodings.append(enc)
                            return pd.read_csv(io.BytesIO(raw), encoding=enc)
                        except Exception:
                            continue
                # 4) 最后再试一次严格 utf-8（便于给出更可读的错误）
                tried_encodings.append("utf-8(strict)")
                return pd.read_csv(io.BytesIO(raw), encoding="utf-8")

        try:
            # 情况 A：文件流 / 二进制缓冲区
            if hasattr(uploaded_file, "read"):
                # 读取全部字节做检测；若是 FastAPI UploadFile，传入的是 .file 或整个对象
                raw = uploaded_file.read() if hasattr(uploaded_file, "read") else uploaded_file.file.read()
                # 读完后，光标在末尾；后续不要再对同一对象重复 read
                df = _process_df_from_bytes(raw)

            # 情况 B：字符串/Path 路径
            else:
                path = Path(uploaded_file)
                if not path.exists():
                    raise FileNotFoundError(f"文件不存在: {path}")

                # 优先用 from_path 探测编码
                probe = from_path(str(path)).best()
                detected = (probe.encoding if probe else None) or "utf-8"
                tried_encodings.append(f"detected:{detected}")

                try:
                    df = pd.read_csv(path, encoding=detected)
                except Exception:
                    # 读原始字节再走统一回退逻辑，鲁棒一些
                    raw = path.read_bytes()
                    df = _process_df_from_bytes(raw)

            return OSPADataLoader._process_dataframe(df)

        except Exception as e:
            tried = ", ".join(tried_encodings) if tried_encodings else "none"
            raise Exception(f"CSV文件读取失败: {e}（已尝试编码: {tried}）")

    @staticmethod
    def load_from_example_file(file_path: str) -> OSPAManager:
        """从示例文件加载数据"""
        try:
            # 首先尝试逗号分隔，如果失败则尝试制表符分隔
            try:
                df = pd.read_csv(file_path)
            except Exception:
                df = pd.read_csv(file_path, sep='\t')

            return OSPADataLoader._process_dataframe(df)
        except Exception as e:
            raise Exception(f"示例数据加载失败: {str(e)}")

    @staticmethod
    def _process_dataframe(df: pd.DataFrame) -> OSPAManager:
        """处理DataFrame并创建OSPAManager"""
        manager = OSPAManager()

        # 智能识别列名映射
        column_mapping = OSPADataLoader._auto_detect_columns(df.columns)

        # 检查是否找到了必需的O和A列
        if 'O' not in column_mapping or 'A' not in column_mapping:
            raise Exception("无法识别必要的列。请确保CSV文件包含观察(O)和行动(A)列")

        # 转换数据
        items = []
        for idx, row in df.iterrows():
            o_col = column_mapping.get('O', '')
            s_col = column_mapping.get('S', '')
            p_col = column_mapping.get('p', '')
            a_col = column_mapping.get('A', '')

            # 只添加有效的O和A数据
            o_val = (str(row.get(o_col, ''))
                     if pd.notna(row.get(o_col, '')) else '')
            a_val = (str(row.get(a_col, ''))
                     if pd.notna(row.get(a_col, '')) else '')

            if o_val and a_val:
                s_val = (str(row.get(s_col, '')) if pd.notna(row.get(
                    s_col, '')) else '')
                p_val = (str(row.get(p_col, '')) if pd.notna(row.get(
                    p_col, '')) else '')

                item_data = {
                    'no': idx + 1,
                    'O': o_val,
                    'S': s_val,
                    'p': p_val,
                    'A': a_val,
                    'A_prime': '',
                    'consistency': '',
                    'confidence_score': '',
                    'error': ''
                }
                items.append(OSPAItem.from_dict(item_data))

        manager.items = items
        return manager

    @staticmethod
    def _auto_detect_columns(columns: List[str]) -> Dict[str, str]:
        """自动检测列名映射"""
        mapping = {}

        for col in columns:
            col_lower = col.lower().strip()
            if col_lower in [
                    'o', 'observation', 'user input', 'user_input', 'question',
                    'q'
            ]:
                mapping['O'] = col
            elif col_lower in [
                    'a', 'action', 'agent output', 'agent_output', 'answer',
                    'response'
            ]:
                mapping['A'] = col
            elif col_lower in ['s', 'state', 'scenario', 'status']:
                mapping['S'] = col
            elif col_lower in ['p', 'prompt', 'instruction']:
                mapping['p'] = col

        return mapping


class OSPAProcessor:
    """OSPA数据处理器"""

    def __init__(self, service_manager: ServiceManager):
        self.service_manager = service_manager

    def process_reward_consistency(
            self,
            manager: OSPAManager,
            enable_concurrent: bool = True,
            max_concurrent: int = 5,
            progress_callback: Optional[Callable] = None,
            status_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """处理一致性检测"""
        valid_items = manager.get_valid_items_for_reward()

        if not valid_items:
            return {
                'success': False,
                'error': '没有有效的数据进行一致性检测',
                'processed_count': 0,
                'success_count': 0
            }

        # 清空之前的错误信息
        for item in valid_items:
            manager.update_item_by_no(item.no, error='')

        try:
            if enable_concurrent and len(valid_items) > 1:
                # 并发处理
                results = run_async_in_streamlit(
                    self.service_manager.reward_service.
                    process_multiple_items_concurrent, valid_items,
                    max_concurrent, progress_callback, status_callback)
            else:
                # 顺序处理
                results = (self.service_manager.reward_service.
                           process_multiple_items_sequential(
                               valid_items, progress_callback,
                               status_callback))

            # 更新管理器中的数据
            success_count = 0
            for item_no, result in results.items():
                if result.success:
                    consistency = result.data["results"][0]["label"]
                    confidence = result.data["results"][0]["confidence"]
                    consistency_str = (f"{consistency}"
                                       if consistency is not None else 'N/A')
                    confidence_str = (f"{confidence}" if
                                      confidence is not None else 'N/A')
                    manager.update_item_by_no(item_no,
                                              consistency=consistency_str,
                                              confidence_score=confidence_str,
                                              error='')
                    success_count += 1
                else:
                    manager.update_item_by_no(item_no,
                                              consistency='',
                                              confidence_score='',
                                              error=result.error)

            return {
                'success': True,
                'processed_count': len(valid_items),
                'success_count': success_count,
                'results': results
            }

        except Exception as e:
            return {
                'success': False,
                'error': f"一致性检测失败: {str(e)}",
                'processed_count': len(valid_items),
                'success_count': 0
            }

    def process_backward_generation(
            self,
            manager: OSPAManager,
            chapters_extra_instructions: str = "",
            gen_p_extra_instructions: str = "",
            overwrite_mode: str = "只更新空白字段") -> Dict[str, Any]:
        """处理状态和提示词生成"""
        valid_items = manager.get_valid_items_for_backward()

        if not valid_items:
            return {
                'success': False,
                'error': '没有有效的问答对数据',
                'processed_count': 0
            }

        try:
            # 准备问答对数据
            qas = [{"q": item.O, "a": item.A} for item in valid_items]

            # 调用backward服务
            result = self.service_manager.backward_service.process_qas(
                qas, chapters_extra_instructions, gen_p_extra_instructions)

            # 更新管理器中的数据
            if result.get("ospa"):
                generated_ospa = result["ospa"]
                updated_count = 0
                skipped_count = 0

                for item in manager.items:
                    # 寻找匹配的生成数据
                    for gen_item in generated_ospa:
                        gen_o = gen_item.get('o', '').strip()
                        gen_a = gen_item.get('a', '').strip()
                        if (gen_o == item.O.strip()
                                and gen_a == item.A.strip()):

                            # 根据覆盖模式决定是否更新
                            if overwrite_mode == "覆盖所有字段":
                                # 直接覆盖
                                manager.update_item_by_no(
                                    item.no,
                                    S=gen_item.get('s', ''),
                                    p=gen_item.get('p', ''))
                                updated_count += 1
                            else:  # "只更新空白字段"
                                # 只更新空白字段
                                updates = {}
                                if not item.S.strip():
                                    updates['S'] = gen_item.get('s', '')
                                if not item.p.strip():
                                    updates['p'] = gen_item.get('p', '')

                                if updates:
                                    manager.update_item_by_no(
                                        item.no, **updates)
                                    updated_count += 1
                                else:
                                    skipped_count += 1
                            break

                return {
                    'success': True,
                    'processed_count': len(valid_items),
                    'updated_count': updated_count,
                    'skipped_count': skipped_count,
                    'result': result
                }
            else:
                return {
                    'success': False,
                    'error': 'API调用成功，但未返回OSPA数据',
                    'processed_count': len(valid_items)
                }

        except Exception as e:
            return {
                'success': False,
                'error': f"状态提示词生成失败: {str(e)}",
                'processed_count': len(valid_items)
            }

    def process_llm_generation(
            self,
            manager: OSPAManager,
            temperature: float = 0.3,
            generation_mode: str = "只更新空白字段",
            enable_concurrent: bool = True,
            max_concurrent: int = 5,
            progress_callback: Optional[Callable] = None,
            status_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """处理LLM答案生成"""
        valid_items = manager.get_valid_items_for_llm()

        if not valid_items:
            return {
                'success': False,
                'error': '没有有效的O&p数据进行答案生成',
                'processed_count': 0,
                'success_count': 0
            }

        # 筛选需要生成的项目
        items_to_process = []
        skipped_count = 0

        for item in valid_items:
            should_generate = (generation_mode == "覆盖所有字段"
                               or not item.A_prime.strip())

            if should_generate:
                items_to_process.append(item)
            else:
                skipped_count += 1

        if not items_to_process:
            return {
                'success': True,
                'processed_count': 0,
                'success_count': 0,
                'skipped_count': skipped_count,
                'message': '没有需要生成的数据'
            }

        # 清空之前的错误信息
        for item in items_to_process:
            manager.update_item_by_no(item.no, error='')

        try:
            if enable_concurrent and len(items_to_process) > 1:
                # 并发处理
                results = run_async_in_streamlit(
                    self.service_manager.llm_service.
                    generate_answers_concurrent, items_to_process, temperature,
                    max_concurrent, progress_callback, status_callback)
            else:
                # 顺序处理
                results = (self.service_manager.llm_service.
                           generate_answers_sequential(items_to_process,
                                                       temperature,
                                                       progress_callback,
                                                       status_callback))

            # 更新管理器中的数据
            success_count = 0
            for item_no, result in results.items():
                if result.success:
                    manager.update_item_by_no(item_no,
                                              A_prime=result.generated_answer,
                                              error='')
                    success_count += 1
                else:
                    manager.update_item_by_no(item_no, error=result.error)

            return {
                'success': True,
                'processed_count': len(items_to_process),
                'success_count': success_count,
                'skipped_count': skipped_count,
                'results': results
            }

        except Exception as e:
            return {
                'success': False,
                'error': f"答案生成失败: {str(e)}",
                'processed_count': len(items_to_process),
                'success_count': 0,
                'skipped_count': skipped_count
            }


class StreamlitUtils:
    """Streamlit相关工具函数"""

    @staticmethod
    def display_ospa_table(manager: OSPAManager, key: str = "ospa_editor"):
        """显示可编辑的OSPA表格"""
        if not manager.items:
            st.info("暂无数据")
            return None

        # 创建显示用的DataFrame
        display_df = manager.to_dataframe()

        # 确保所有必需的列都存在
        required_columns = [
            'no', 'O', 'S', 'p', 'A', 'A_prime', 'consistency',
            'confidence_score', 'error'
        ]
        for col in required_columns:
            if col not in display_df.columns:
                display_df[col] = ''

        display_df = display_df[required_columns]
        display_df.columns = [
            '序号', 'O', 'S', 'p', 'A', "A'", "consistency",
            "confidence_score", "error"
        ]

        # 使用可编辑的数据编辑器
        edited_df = st.data_editor(
            display_df,
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "序号": st.column_config.NumberColumn(
                    "序号", width="small", disabled=True
                ),
                "O": st.column_config.TextColumn(
                    "O", width="medium", help="观察/用户输入"
                ),
                "S": st.column_config.TextColumn(
                    "S", width="small", help="状态/场景"
                ),
                "p": st.column_config.TextColumn(
                    "p", width="large", help="提示词"
                ),
                "A": st.column_config.TextColumn(
                    "A", width="medium", help="Agent输出/标准答案"
                ),
                "A'": st.column_config.TextColumn(
                    "A'", width="medium", help="候选答案（用于一致性比较）"
                ),
                "consistency": st.column_config.NumberColumn(
                    "consistency", width="small", help="一致性得分", format="%.3f"
                ),
                "confidence_score": st.column_config.NumberColumn(
                    "confidence_score", width="small", help="置信度",
                    format="%.3f"
                ),
                "error": st.column_config.TextColumn(
                    "error", width="medium", help="错误信息"
                ),
            },
            key=key
        )

        return edited_df

    @staticmethod
    def update_manager_from_edited_df(
        manager: OSPAManager,
        edited_df: pd.DataFrame
    ) -> bool:
        """从编辑后的DataFrame更新管理器数据"""
        try:
            updated_items = []
            for _, row in edited_df.iterrows():
                item_data = {
                    'no': int(row['序号']),
                    'O': str(row['O']),
                    'S': str(row['S']),
                    'p': str(row['p']),
                    'A': str(row['A']),
                    'A_prime': str(row["A'"]),
                    'consistency': str(row["consistency"]),
                    'confidence_score': str(row["confidence_score"]),
                    'error': str(row["error"]),
                }
                updated_items.append(OSPAItem.from_dict(item_data))

            manager.items = updated_items
            return True
        except Exception:
            return False

    @staticmethod
    def show_statistics(manager: OSPAManager):
        """显示数据统计信息"""
        stats = manager.get_statistics()

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("总数据", stats['total_items'])
        with col2:
            st.metric("可检测一致性", stats['valid_for_reward'])
        with col3:
            st.metric("可生成S&p", stats['valid_for_backward'])
        with col4:
            st.metric("可生成答案", stats['valid_for_llm'])

        if stats['has_errors'] > 0:
            st.warning(f"⚠️ 有 {stats['has_errors']} 条数据存在错误")
