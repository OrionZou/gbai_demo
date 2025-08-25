在agent_runtime中 写一个名为 backward 的 api，输入是 q & a 列表，输出是 多条[q, chapter_name, prompt, a]的列表。

backward 的作用是 q & a的内容是用于整理知识手册的素材，LLM 为输入的每个 q & a，生成一个章节名称 chapter_name ， 比较相关的 q & a 可以采用同一个章节名称，再为 每个 chapter_name 生成一个辅助提示词prompt，使得 LLM 根据chapter_name、 prompt 和 q 容易生成 a。

backward的过程分 2 步 LLM 调用：
1. 根据q & a 列表，生成 格式如下 {"chapter_name1":[q & a,q & a,q & a],"chapter_name2":[q & a,q & a,q & a]} 章节聚合结构，并给出聚合的原因。
2. 根据每个分组数据 "chapter_name1":[q & a,q & a,q & a] ，为 chapter_name1生成一个辅助提示词prompt，使得 LLM 根据chapter_name、 prompt 和 q 容易生成 a。

