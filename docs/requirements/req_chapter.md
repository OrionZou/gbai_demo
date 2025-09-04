基于 baseagent，设计开发一个目录构建的agent, 他的作用是 如果没有已知的目录结构，基于多轮对话内容（格式为CQA List）内容，构建一个层数小于等于指定层数的目录结构；如果有已知的目录结构，基于多轮对话内容（格式为CQA List）内容合理归类到已知目录结构中，如果已知目录结构的章节与 CQA数据不匹配，则合理派生新章节或子章节。输入包含 章节目录字典，c & q & a 列表 和目录层数。



写一个backward_v2接口，设计一个service，利用 cqa_agent 、chapter_structure_agent、 chapter_classification_agent  和 gen_chpt_p_agent 这四个agent。输入是一个q & a 二维列表（表示 多个多轮对话） 和一个章节目录的可选参数，第一维 区分多个多轮对话，第二维区分多轮对话中 的 多个q & a。
首先 把 q & a 二维列表 使用cqa_agent转为 cpa 二维列表。
如果输入没有章节目录，则使用 chapter_structure_agent 基于 cpa 二维列表 生成一个章节目录，然后基于章节目录 使用gen_chpt_p_agent生成章节提示词。最后输出章节目录和ospa
如果输入有章节目录，则使用 chapter_classification_agent 基于 cpa 二维列表 更新已有章节目录，然后基于更新后章节目录 使用gen_chpt_p_agent生成章节提示词。最后输出更新后章节目录和ospa