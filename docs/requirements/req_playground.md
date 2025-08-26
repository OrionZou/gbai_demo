使用streamlit 为 agent_runtime 的 api 实现一个 前端的 playground，可以参考 ./agent-streamlit的实现。


在 playground 中，优化OSPA 表格的选项卡，显示一个包含 O、A、S、p、A'、consistency、 confidence_score、error 的表格。有一个按钮可以控制使用 reward api 计算每行数据A、A'的一致性结果填写在consistency、 confidence_score、error，有一个按钮可以控制 backward api 计算O、A 对应S、P填写在S、p