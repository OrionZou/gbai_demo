在agent_runtime中 写一个 名为 backward 的 api，输入是 q & a 列表， q & a的内容是用于整理知识手册的素材，LLM 为输入的每个 q & a，生成一个章节名称 c，比较相关的 q & a 可以采用同一个章节名称，再为 每个 c 生成一个辅助提示词 p，使得 LLM 根据c、 q 和 p 容易生成 a。
