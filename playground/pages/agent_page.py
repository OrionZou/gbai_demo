"""
Agent管理页面
"""

import streamlit as st
import requests
import json
import random
from typing import Dict, Any, Optional, List
from components.common import PageHeader, ResultDisplay, StatusIndicator


class AgentPage:
    """Agent管理页面"""

    def __init__(self, service_manager):
        self.service_manager = service_manager
        self.api_url = service_manager.base_url

    def render(self):
        """渲染Agent管理页面"""
        st.markdown("## 🤖 Agent 提示词管理")

        # 获取支持的Agent名称
        if not self._load_agent_names():
            st.error("无法获取Agent名称列表，请检查API连接")
            return

        # Agent选择和信息显示
        selected_agent = self._render_agent_selection()

        if selected_agent:
            # 自动获取Agent详细信息
            if self._load_agent_info(selected_agent):
                # 显示Agent信息和编辑界面
                self._render_agent_editor()

                # 模板变量验证区域
                self._render_template_validation()

    def _load_agent_names(self) -> bool:
        """加载Agent名称列表"""
        if "agent_names" not in st.session_state:
            try:
                response = requests.get(
                    f"{self.api_url}/agent/agents/names", timeout=10
                )
                if response.status_code == 200:
                    agent_names = response.json()
                    st.session_state.agent_names = agent_names
                    return True
                else:
                    st.error(f"🚫 获取Agent名称失败: {response.status_code}")
                    return False
            except Exception as e:
                st.error(f"🚫 请求失败: {e}")
                return False
        return True

    def _render_agent_selection(self) -> Optional[str]:
        """渲染Agent选择区域"""
        if not st.session_state.agent_names:
            return None

        col_select, col_info = st.columns([2, 3])

        with col_select:
            selected_agent = st.selectbox(
                "🎯 选择Agent",
                st.session_state.agent_names,
                key="selected_agent_name",
                help="选择后自动加载提示词",
            )

        with col_info:
            if selected_agent:
                st.info(f"📋 正在管理: **{selected_agent}**")

        return selected_agent

    def _load_agent_info(self, selected_agent: str) -> bool:
        """加载Agent详细信息"""
        try:
            response = requests.get(
                f"{self.api_url}/agent/agents/{selected_agent}/prompts", timeout=10
            )
            if response.status_code == 200:
                agent_info = response.json()
                # 只在Agent变更时更新信息，避免重复请求
                if (
                    "current_agent_info" not in st.session_state
                    or st.session_state.current_agent_info.get("agent_name")
                    != selected_agent
                ):
                    st.session_state.current_agent_info = agent_info
                    st.session_state.original_system_prompt = agent_info.get(
                        "system_prompt", ""
                    )
                    st.session_state.original_user_template = agent_info.get(
                        "user_prompt_template", ""
                    )
                return True
            else:
                st.error(f"🚫 获取Agent信息失败: {response.status_code}")
                return False
        except Exception as e:
            st.error(f"🚫 请求失败: {e}")
            return False

    def _render_agent_editor(self):
        """渲染Agent编辑器"""
        agent_info = st.session_state.current_agent_info

        # 基本信息展示
        self._render_agent_metrics(agent_info)

        # 主编辑区域
        main1_col, main2_col, side_col = st.columns([3, 3, 2])

        with main1_col:
            current_system_prompt = self._render_system_prompt_editor(agent_info)

        with main2_col:
            current_user_template = self._render_user_template_editor(agent_info)

        with side_col:
            self._render_operation_panel(current_system_prompt, current_user_template)

    def _render_agent_metrics(self, agent_info: Dict[str, Any]):
        """渲染Agent指标信息"""
        template_vars = agent_info.get("template_variables", [])

        with st.container():
            col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
            with col1:
                st.metric("Agent名称", agent_info.get("agent_name", "N/A"))
            with col2:
                st.metric("模板变量", f"{len(template_vars)} 个")
            with col3:
                sys_len = len(agent_info.get("system_prompt", ""))
                st.metric("系统提示词", f"{sys_len} 字符")
            with col4:
                tpl_len = len(agent_info.get("user_prompt_template", ""))
                st.metric("用户模板", f"{tpl_len} 字符")

        if template_vars:
            st.info(f"🔧 **模板变量**: {', '.join(template_vars)}")

    def _render_system_prompt_editor(self, agent_info: Dict[str, Any]) -> str:
        """渲染系统提示词编辑器"""
        with st.expander("📝 系统提示词编辑", expanded=True):
            current_system_prompt = st.text_area(
                "系统提示词内容",
                value=agent_info.get("system_prompt", ""),
                height=360,
                key="edit_system_prompt",
                label_visibility="collapsed",
                help="编辑系统提示词内容",
            )
        return current_system_prompt

    def _render_user_template_editor(self, agent_info: Dict[str, Any]) -> str:
        """渲染用户模板编辑器"""
        with st.expander("📄 用户提示词模板编辑", expanded=True):
            current_user_template = st.text_area(
                "用户模板内容",
                value=agent_info.get("user_prompt_template", ""),
                height=360,
                key="edit_user_template",
                label_visibility="collapsed",
                help="支持Jinja2模板语法",
            )
        return current_user_template

    def _render_operation_panel(
        self, current_system_prompt: str, current_user_template: str
    ):
        """渲染操作面板"""
        st.markdown("#### 🔧 操作中心")

        # 检查是否有修改
        has_system_changes = current_system_prompt != st.session_state.get(
            "original_system_prompt", ""
        )
        has_template_changes = current_user_template != st.session_state.get(
            "original_user_template", ""
        )
        has_changes = has_system_changes or has_template_changes

        # 状态指示器
        self._render_change_status(
            has_changes, has_system_changes, has_template_changes
        )

        # 主要操作按钮
        self._render_main_operations(
            has_changes, current_system_prompt, current_user_template
        )

        # 辅助操作按钮
        self._render_auxiliary_operations()

        # 内容统计
        self._render_content_stats(
            current_system_prompt, current_user_template, has_changes
        )

    def _render_change_status(
        self, has_changes: bool, has_system_changes: bool, has_template_changes: bool
    ):
        """渲染变更状态"""
        if has_changes:
            st.warning("⚠️ 有未保存修改")
            changes_info = []
            if has_system_changes:
                changes_info.append("系统提示词")
            if has_template_changes:
                changes_info.append("用户模板")
            st.caption(f"修改: {', '.join(changes_info)}")
        else:
            st.success("✅ 内容已保存")

    def _render_main_operations(
        self, has_changes: bool, current_system_prompt: str, current_user_template: str
    ):
        """渲染主要操作按钮"""
        update_clicked = st.button(
            "💾 保存修改",
            type="primary" if has_changes else "secondary",
            disabled=not has_changes,
            key="update_prompts_btn",
            use_container_width=True,
            help="保存当前修改的提示词内容",
        )

        if update_clicked and has_changes:
            self._execute_update(current_system_prompt, current_user_template)

    def _execute_update(self, current_system_prompt: str, current_user_template: str):
        """执行更新操作"""
        selected_agent = st.session_state.selected_agent_name

        # 构建更新数据
        update_data = {}
        if current_system_prompt != st.session_state.get("original_system_prompt", ""):
            update_data["system_prompt"] = current_system_prompt.strip()
        if current_user_template != st.session_state.get("original_user_template", ""):
            update_data["user_prompt_template"] = current_user_template.strip()

        try:
            with st.spinner("正在保存..."):
                response = requests.put(
                    f"{self.api_url}/agent/agents/{selected_agent}/prompts",
                    json=update_data,
                    timeout=30,
                )

            if response.status_code == 200:
                updated_info = response.json()
                st.session_state.current_agent_info = updated_info
                st.session_state.original_system_prompt = updated_info.get(
                    "system_prompt", ""
                )
                st.session_state.original_user_template = updated_info.get(
                    "user_prompt_template", ""
                )
                st.success("✅ 保存成功！")
                st.rerun()
            else:
                st.error(f"保存失败: {response.status_code}")
        except Exception as e:
            st.error(f"请求失败: {e}")

    def _render_auxiliary_operations(self):
        """渲染辅助操作按钮"""
        col_reset, col_refresh = st.columns(2)

        with col_reset:
            reset_clicked = st.button(
                "🔄默认",
                key="reset_to_default",
                help="重置为默认",
                use_container_width=True,
            )

        with col_refresh:
            refresh_clicked = st.button(
                "🔃刷新", key="refresh_agent", help="刷新内容", use_container_width=True
            )

        if reset_clicked:
            self._execute_reset()

        if refresh_clicked:
            self._execute_refresh()

    def _execute_reset(self):
        """执行重置操作"""
        selected_agent = st.session_state.selected_agent_name
        try:
            response = requests.post(
                f"{self.api_url}/agent/agents/{selected_agent}/prompts/reset",
                timeout=30,
            )
            if response.status_code == 200:
                reset_info = response.json()
                st.session_state.current_agent_info = reset_info
                st.session_state.original_system_prompt = reset_info.get(
                    "system_prompt", ""
                )
                st.session_state.original_user_template = reset_info.get(
                    "user_prompt_template", ""
                )
                st.success("✅ 已重置")
                st.rerun()
            else:
                st.error("重置失败")
        except Exception as e:
            st.error(f"重置失败: {e}")

    def _execute_refresh(self):
        """执行刷新操作"""
        selected_agent = st.session_state.selected_agent_name
        try:
            response = requests.get(
                f"{self.api_url}/agent/agents/{selected_agent}/prompts", timeout=10
            )
            if response.status_code == 200:
                fresh_info = response.json()
                st.session_state.current_agent_info = fresh_info
                st.session_state.original_system_prompt = fresh_info.get(
                    "system_prompt", ""
                )
                st.session_state.original_user_template = fresh_info.get(
                    "user_prompt_template", ""
                )
                st.success("✅ 已刷新")
                st.rerun()
            else:
                st.error("刷新失败")
        except Exception as e:
            st.error(f"刷新失败: {e}")

    def _render_content_stats(
        self, current_system_prompt: str, current_user_template: str, has_changes: bool
    ):
        """渲染内容统计"""
        st.markdown("---")
        st.markdown("##### 📊 内容统计")

        if has_changes:
            # 显示修改前后对比
            orig_sys_len = len(st.session_state.get("original_system_prompt", ""))
            curr_sys_len = len(current_system_prompt)
            orig_tpl_len = len(st.session_state.get("original_user_template", ""))
            curr_tpl_len = len(current_user_template)

            st.caption(f"系统提示词: {orig_sys_len} → {curr_sys_len} 字符")
            st.caption(f"用户模板: {orig_tpl_len} → {curr_tpl_len} 字符")
        else:
            sys_len = len(current_system_prompt)
            tpl_len = len(current_user_template)
            st.caption(f"系统提示词: {sys_len} 字符")
            st.caption(f"用户模板: {tpl_len} 字符")

    def _render_template_validation(self):
        """渲染模板验证区域"""
        st.markdown("---")

        col_validate, col_preview = st.columns([1, 1])

        with col_validate:
            self._render_validation_form()

        with col_preview:
            self._render_validation_preview()

    def _render_validation_form(self):
        """渲染验证表单"""
        st.subheader("🧪 模板变量验证")
        agent_info = st.session_state.current_agent_info
        template_vars = agent_info.get("template_variables", [])

        if template_vars:
            st.write(f"**需要变量**: {', '.join(template_vars)}")

            # 验证表单
            with st.form("quick_validate_form"):
                test_vars = self._render_variable_inputs(template_vars)

                # 按钮组
                col_validate, col_clear, col_default, col_random = st.columns(4)

                with col_validate:
                    validate_clicked = st.form_submit_button("✅ 验证", type="primary")
                with col_clear:
                    clear_clicked = st.form_submit_button("🗑️ 清空")
                with col_default:
                    default_clicked = st.form_submit_button("🎯 默认值")
                with col_random:
                    random_clicked = st.form_submit_button("🎲 随机")

                # 处理按钮点击
                self._handle_validation_buttons(
                    validate_clicked,
                    clear_clicked,
                    default_clicked,
                    random_clicked,
                    test_vars,
                )

            # 验证统计
            self._render_validation_stats(template_vars)
        else:
            st.info("✨ 此Agent无需模板变量，可直接使用")

    def _render_variable_inputs(self, template_vars: List[str]) -> Dict[str, Any]:
        """渲染变量输入表单"""
        test_vars = {}
        use_random = st.session_state.get("use_random_data", False)

        for var in template_vars:
            if var == "candidates":
                # 候选答案特殊处理
                display_value = self._get_display_value(var, use_random, is_list=True)
                candidates_input = st.text_input(
                    f"{var} (用逗号分隔)",
                    value=display_value,
                    key=f"quick_test_{var}",
                    help="已填入测试数据，可直接使用或修改",
                )
                if candidates_input.strip():
                    test_vars[var] = [
                        item.strip()
                        for item in candidates_input.split(",")
                        if item.strip()
                    ]
            else:
                # 普通变量
                display_value = self._get_display_value(var, use_random)
                var_input = st.text_input(
                    var,
                    value=str(display_value),
                    key=f"quick_test_{var}",
                    help="已填入测试数据，可直接使用或修改",
                )
                if var_input.strip():
                    test_vars[var] = var_input.strip()

        return test_vars

    def _get_display_value(self, var: str, use_random: bool, is_list: bool = False):
        """获取变量的显示值"""
        if use_random and "random_data" in st.session_state:
            value = st.session_state.random_data.get(var, self._get_default_value(var))
            if is_list and isinstance(value, list):
                return ",".join(value)
            return str(value)
        return self._get_default_value(var)

    def _get_default_value(self, var_name: str) -> str:
        """获取变量的默认测试值"""
        defaults = {
            "question": "什么是人工智能？",
            "target_answer": "人工智能是计算机科学的一个分支，致力于创建能够执行通常需要人类智能的任务的系统。",
            "candidates": "人工智能是机器学习,AI是计算机技术,人工智能模拟人类思维,AI用于自动化任务",
            "query": "请解释机器学习的基本概念",
            "context": "机器学习是人工智能的重要组成部分",
            "input": "请分析以下文本内容",
            "text": "这是一段需要分析的示例文本内容",
            "prompt": "请根据以下信息进行分析",
            "content": "这里是需要处理的内容示例",
            "task": "文本分类任务",
            "examples": "示例1,示例2,示例3",
            "instructions": "请按照以下步骤进行操作",
            "format": "JSON格式输出",
            "language": "中文",
            "topic": "科技发展",
            "style": "正式学术风格",
        }
        return defaults.get(var_name, f"{var_name}的测试值")

    def _handle_validation_buttons(
        self,
        validate_clicked: bool,
        clear_clicked: bool,
        default_clicked: bool,
        random_clicked: bool,
        test_vars: Dict[str, Any],
    ):
        """处理验证按钮点击"""
        if validate_clicked:
            self._execute_validation(test_vars)
        elif clear_clicked:
            self._clear_validation()
        elif default_clicked:
            self._reset_to_default()
        elif random_clicked:
            self._generate_random_data()

    def _execute_validation(self, test_vars: Dict[str, Any]):
        """执行模板验证"""
        if test_vars:
            try:
                selected_agent = st.session_state.selected_agent_name
                with st.spinner("正在验证模板..."):
                    response = requests.post(
                        f"{self.api_url}/agent/agents/{selected_agent}/prompts/validate",
                        json=test_vars,
                        timeout=30,
                    )

                if response.status_code == 200:
                    validation_result = response.json()
                    st.session_state.validation_result = validation_result
                    st.session_state.last_test_vars = test_vars

                    if validation_result.get("valid"):
                        st.success("✅ 模板验证通过！")
                    else:
                        st.error("❌ 模板验证失败")
                else:
                    st.error(f"验证失败: {response.status_code}")
            except Exception as e:
                st.error(f"请求失败: {e}")
        else:
            st.warning("请至少提供一个变量值")

    def _clear_validation(self):
        """清空验证结果"""
        for key in ["validation_result", "use_random_data", "random_data"]:
            if key in st.session_state:
                del st.session_state[key]
        st.info("已清空验证结果")
        st.rerun()

    def _reset_to_default(self):
        """重置为默认值"""
        for key in ["use_random_data", "random_data"]:
            if key in st.session_state:
                del st.session_state[key]
        st.success("✅ 已重置为默认值")
        st.rerun()

    def _generate_random_data(self):
        """生成随机数据"""
        random_data = {
            "question": random.choice(
                [
                    "什么是深度学习？",
                    "如何理解神经网络？",
                    "机器学习有哪些应用？",
                    "什么是自然语言处理？",
                ]
            ),
            "target_answer": random.choice(
                [
                    "深度学习是机器学习的一个子领域。",
                    "神经网络是模仿人脑结构的计算模型。",
                    "机器学习广泛应用于各个领域。",
                    "自然语言处理让计算机理解人类语言。",
                ]
            ),
            "candidates": random.sample(
                [
                    "这是第一个候选答案",
                    "这是另一个可能的答案",
                    "还有这个备选方案",
                    "最后一个候选答案",
                    "额外的答案选项",
                    "补充的候选内容",
                ],
                3,
            ),
            "query": random.choice(
                [
                    "请解释机器学习的基本概念",
                    "分析深度学习的应用场景",
                    "描述神经网络的工作原理",
                ]
            ),
            "context": random.choice(
                [
                    "机器学习是人工智能的重要组成部分",
                    "深度学习推动了AI技术的发展",
                    "神经网络模拟人类大脑的学习过程",
                ]
            ),
        }
        st.session_state.random_data = random_data
        st.session_state.use_random_data = True
        st.success("🎲 已生成随机测试数据")
        st.rerun()

    def _render_validation_stats(self, template_vars: List[str]):
        """渲染验证统计"""
        st.write("**验证统计**")
        st.info(f"📊 共需 {len(template_vars)} 个变量")

        if st.session_state.get("use_random_data", False):
            st.success("🎲 当前使用随机数据")
        else:
            st.info("🎯 当前使用默认数据")

        # 显示上次验证统计
        if "last_test_vars" in st.session_state:
            st.write("**上次验证:**")
            for var, value in st.session_state.last_test_vars.items():
                if isinstance(value, list):
                    st.write(f"• {var}: {len(value)} 项")
                else:
                    st.write(f"• {var}: {len(str(value))} 字符")

    def _render_validation_preview(self):
        """渲染验证预览"""
        st.subheader("🔍 渲染预览")

        if "validation_result" in st.session_state:
            result = st.session_state.validation_result

            # 验证状态指示
            if result.get("valid"):
                st.success("✅ 验证通过")
            else:
                st.error("❌ 验证失败")

            # 显示详细信息
            col_stats1, col_stats2 = st.columns(2)

            with col_stats1:
                missing = result.get("missing_variables", [])
                if missing:
                    st.error(f"**缺失变量**: {len(missing)}")
                    for var in missing:
                        st.write(f"• {var}")
                else:
                    st.success("**变量完整**: 无缺失")

            with col_stats2:
                extra = result.get("extra_variables", [])
                if extra:
                    st.warning(f"**多余变量**: {len(extra)}")
                    for var in extra:
                        st.write(f"• {var}")
                else:
                    st.success("**变量准确**: 无多余")

            # 显示渲染结果
            if result.get("rendered_preview"):
                st.markdown("**渲染结果**:")
                preview_text = result["rendered_preview"]

                # 显示渲染统计
                lines_count = len(preview_text.split("\n"))
                chars_count = len(preview_text)
                st.caption(f"📊 {lines_count} 行, {chars_count} 字符")

                # 渲染结果文本框
                st.text_area(
                    "完整渲染内容:",
                    value=preview_text,
                    height=500,
                    disabled=True,
                    label_visibility="collapsed",
                )

                st.caption("💡 提示: 可以从上方文本框复制渲染结果")
            else:
                st.info("模板验证失败，无法生成预览")

            # 显示错误信息
            if result.get("error"):
                st.error(f"**错误**: {result['error']}")
        else:
            st.info("🚀 进行模板验证后将显示预览结果")

            # 显示说明信息
            st.markdown(
                """
            **验证说明**:
            - ✅ **验证通过**: 所有变量都已正确提供
            - ❌ **验证失败**: 存在缺失或多余变量
            - 📄 **渲染预览**: 显示模板的最终输出效果
            - 📊 **统计信息**: 显示内容行数和字符数
            """
            )

            # 快速测试提示
            agent_info = st.session_state.current_agent_info
            template_vars = agent_info.get("template_variables", [])
            if template_vars and "validation_result" not in st.session_state:
                st.info("💡 左侧已自动填入测试值，点击'验证'按钮开始测试")
