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


def _detect_encoding(raw: bytes, path: Path | None = None) -> str:
    """优先用 charset-normalizer 探测；否则按常见编码回退。"""
    if from_bytes and raw:
        probe = from_bytes(raw).best()
        if probe and probe.encoding:
            return probe.encoding
    if path and from_path:
        probe = from_path(str(path)).best()
        if probe and probe.encoding:
            return probe.encoding

    # 回退顺序：UTF-8 BOM → UTF-8 → GBK → GB18030 → Latin1
    for enc in ("utf-8-sig", "utf-8", "gbk", "gb18030", "latin1"):
        try:
            raw.decode(enc)
            return enc
        except Exception:
            pass
    return "utf-8"


class OSPADataLoader:
    """OSPA数据加载器"""

    @staticmethod
    def load_from_csv_file(
            uploaded_file: Union[str, Path, IO[bytes]]) -> OSPAManager:
        """
        自动探测 CSV 原始编码 → 统一转 UTF-8 后读取为 DataFrame。
        支持文件路径(str/Path)与二进制文件流(如 FastAPI UploadFile.file)。
        """
        try:
            # 读取原始字节
            if hasattr(uploaded_file, "read"):  # 文件流
                raw = uploaded_file.read()  # 读全；后续勿重复 read
                src_path = None
            else:  # 路径
                src_path = Path(uploaded_file)  # type: ignore[arg-type]
                if not src_path.exists():
                    raise FileNotFoundError(f"文件不存在: {src_path}")
                raw = src_path.read_bytes()

            # 探测编码
            enc = _detect_encoding(raw, src_path)

            # 统一转为 UTF-8 文本
            text = raw.decode(enc, errors="strict")
            text = text.replace("\r\n", "\n").replace("\r", "\n")  # 规范换行

            # 以 UTF-8 读取
            df = pd.read_csv(io.StringIO(text))

            # 下游处理
            return OSPADataLoader._process_dataframe(df)

        except Exception as e:
            raise Exception(f"CSV文件读取失败: {e}")

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
                    confidence_str = (f"{confidence}"
                                      if confidence is not None else 'N/A')
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
            max_level: int = 3,
            max_concurrent_llm: int = 10,
            overwrite_mode: str = "只更新空白字段",
            chapter_structure: Optional[Dict[str, Any]] = None,
            include_cases_in_prompt: bool = False,
            max_cases_per_chapter: int = 0) -> Dict[str, Any]:
        """处理状态和提示词生成"""
        valid_items = manager.get_valid_items_for_backward()

        if not valid_items:
            return {
                'success': False,
                'error': '没有有效的问答对数据',
                'processed_count': 0
            }

        try:
            # 准备问答对数据 - 使用正确的格式
            qas = [{"question": item.O, "answer": item.A} for item in valid_items]

            # 调用backward API - 使用正确的参数
            result = self.service_manager.backward_service.process_qas(
                qas,  # 第一个参数是位置参数
                chapter_structure=chapter_structure,  # 使用传入的章节结构，None表示创建新的
                max_level=max_level,
                max_concurrent_llm=max_concurrent_llm
            )

            # 更新管理器中的数据
            if result.get("ospa"):
                generated_ospa = result["ospa"]
                chapter_structure_data = result.get("chapter_structure")
                updated_count = 0
                skipped_count = 0

                for item in manager.items:
                    # 寻找匹配的生成数据 - 改进匹配逻辑
                    matched = False
                    for gen_item in generated_ospa:
                        gen_o = gen_item.get('o', '').strip()
                        gen_a = gen_item.get('a', '').strip()
                        item_o = item.O.strip()
                        item_a = item.A.strip()

                        # 尝试多种匹配方式
                        exact_match = (gen_o == item_o and gen_a == item_a)
                        normalized_match = (
                            gen_o.replace('\n', ' ').replace('\r', ' ')
                            == item_o.replace('\n', ' ').replace('\r', ' ')
                            and gen_a.replace('\n', ' ').replace('\r', ' ')
                            == item_a.replace('\n', ' ').replace('\r', ' '))
                        contains_match = (
                            gen_o in item_o or item_o in gen_o
                            or gen_a in item_a or item_a in gen_a
                        ) and len(gen_o) > 10 and len(gen_a) > 10  # 避免短文本误匹配

                        if exact_match or normalized_match or contains_match:
                            print(f"[DEBUG] Found match for item {item.no}: exact={exact_match}, normalized={normalized_match}, contains={contains_match}")

                            # 获取原始提示词
                            original_prompt = gen_item.get('p', '')

                            # 如果需要包含案例，增强提示词
                            enhanced_prompt = original_prompt
                            if include_cases_in_prompt and chapter_structure_data:
                                enhanced_prompt = self._enhance_prompt_with_cases(
                                    original_prompt,
                                    gen_item.get('s', ''),  # 章节名称
                                    chapter_structure_data,
                                    max_cases_per_chapter
                                )

                            # 根据覆盖模式决定是否更新
                            if overwrite_mode == "覆盖所有字段":
                                # 直接覆盖所有字段
                                manager.update_item_by_no(
                                    item.no,
                                    S=gen_item.get('s', ''),
                                    p=enhanced_prompt)
                                updated_count += 1
                                print(f"[DEBUG] Updated item {item.no} (覆盖所有字段): S='{gen_item.get('s', '')[:50]}...', p='{enhanced_prompt[:50]}...'")
                            else:  # "只更新空白字段"
                                # 只更新空白字段
                                updates = {}

                                # 检查S字段是否为空
                                if not item.S.strip():
                                    updates['S'] = gen_item.get('s', '')
                                    print(f"[DEBUG] Item {item.no} S field is empty, will update with: '{gen_item.get('s', '')[:50]}...'")
                                else:
                                    print(f"[DEBUG] Item {item.no} S field already has value: '{item.S[:50]}...', skipping")

                                # 检查p字段是否为空
                                if not item.p.strip():
                                    updates['p'] = enhanced_prompt
                                    print(f"[DEBUG] Item {item.no} p field is empty, will update with: '{enhanced_prompt[:50]}...'")
                                else:
                                    print(f"[DEBUG] Item {item.no} p field already has value: '{item.p[:50]}...', skipping")

                                if updates:
                                    manager.update_item_by_no(item.no, **updates)
                                    updated_count += 1
                                    print(f"[DEBUG] Updated item {item.no} (只更新空白字段): {list(updates.keys())}")
                                else:
                                    skipped_count += 1
                                    print(f"[DEBUG] Skipped item {item.no} (只更新空白字段): no empty fields to update")

                            matched = True
                            break

                    # 如果没有找到匹配项，记录调试信息
                    if not matched:
                        print(f"[DEBUG] No match found for item {item.no}: O='{item.O[:50]}...', A='{item.A[:50]}...'")
                        skipped_count += 1

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

    def _enhance_prompt_with_cases(
            self,
            original_prompt: str,
            chapter_name: str,
            chapter_structure: Dict[str, Any],
            max_cases: int) -> str:
        """使用章节案例增强提示词"""
        if not chapter_structure or max_cases <= 0:
            return original_prompt

        # 查找匹配的章节节点
        nodes = chapter_structure.get("nodes", {})
        matching_node = None

        # 通过章节名称查找节点
        for node_id, node_data in nodes.items():
            if node_data.get("title", "") == chapter_name:
                matching_node = node_data
                break

        if not matching_node or not matching_node.get("related_qa_items"):
            return original_prompt

        # 获取相关案例
        qa_items = matching_node.get("related_qa_items", [])
        selected_cases = qa_items[:max_cases]  # 限制案例数量

        if not selected_cases:
            return original_prompt

        # 构建增强的提示词
        enhanced_prompt = original_prompt

        # 添加分隔符和案例说明
        enhanced_prompt += "\n\n## 相关案例参考\n"
        enhanced_prompt += f"以下是{chapter_name}章节的相关案例，供参考理解：\n\n"

        # 添加每个案例
        for i, qa_item in enumerate(selected_cases, 1):
            question = qa_item.get("question", "")
            answer = qa_item.get("answer", "")

            if question and answer:
                enhanced_prompt += f"**案例 {i}：**\n"
                enhanced_prompt += f"问题：{question}\n"
                enhanced_prompt += f"答案：{answer}\n\n"

        # 添加使用说明
        enhanced_prompt += "请参考以上案例的回答风格和内容深度来回答用户问题。"

        return enhanced_prompt

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
            '序号', 'O', 'S', 'p', 'A', "A'", "consistency", "confidence_score",
            "error"
        ]

        # 使用可编辑的数据编辑器
        edited_df = st.data_editor(
            display_df,
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "序号":
                st.column_config.NumberColumn("序号",
                                              width="small",
                                              disabled=True),
                "O":
                st.column_config.TextColumn("O",
                                            width="medium",
                                            help="观察/用户输入"),
                "S":
                st.column_config.TextColumn("S", width="small", help="状态/场景"),
                "p":
                st.column_config.TextColumn("p", width="large", help="提示词"),
                "A":
                st.column_config.TextColumn("A",
                                            width="medium",
                                            help="Agent输出/标准答案"),
                "A'":
                st.column_config.TextColumn("A'",
                                            width="medium",
                                            help="候选答案（用于一致性比较）"),
                "consistency":
                st.column_config.NumberColumn("consistency",
                                              width="small",
                                              help="一致性得分",
                                              format="%.3f"),
                "confidence_score":
                st.column_config.NumberColumn("confidence_score",
                                              width="small",
                                              help="置信度",
                                              format="%.3f"),
                "error":
                st.column_config.TextColumn("error",
                                            width="medium",
                                            help="错误信息"),
            },
            key=key)

        return edited_df

    @staticmethod
    def update_manager_from_edited_df(manager: OSPAManager,
                                      edited_df: pd.DataFrame) -> bool:
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
            st.metric("可生成S&p", stats['valid_for_backward'])
        with col3:
            st.metric("可生成答案", stats['valid_for_llm'])
        with col4:
            st.metric("可检测一致性", stats['valid_for_reward'])

        if stats['has_errors'] > 0:
            st.warning(f"⚠️ 有 {stats['has_errors']} 条数据存在错误")
