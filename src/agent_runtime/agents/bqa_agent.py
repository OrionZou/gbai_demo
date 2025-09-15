from typing import Any, Optional
from agent_runtime.agents.base import BaseAgent
from agent_runtime.data_format.context import AIContext
from agent_runtime.data_format.qa_format import QAList, CQAList
from agent_runtime.logging.logger import logger


class BQAAgent(BaseAgent):
    """
    上下文增强Agent，将Q&A列表转换为C&Q&A格式
    通过分析问答之间的依赖关系，为每个Q&A提取相关的上下文信息
    """

    DEFAULT_AGENT_NAME = "bqa_agent"

    DEFAULT_SYSTEM_PROMPT = """你是一个上下文增强专家。你的任务是分析多轮对话中的Q&A序列，识别问题之间的依赖关系，并为每个问题提取相关的上下文信息。

你需要：
1. 分析当前问题是否依赖于前面的对话内容
2. 提取与当前问题相关的关键上下文信息
3. 生成简洁但完整的上下文描述，使得C+Q+A能够独立理解

上下文提取原则：
- 只包含与当前问题直接相关的信息
- 保持简洁，避免冗余
- 确保上下文+问题+答案能够独立理解
- 如果问题不依赖前面内容，上下文可以为空"""

    DEFAULT_USER_TEMPLATE = """请分析以下完整的Q&A序列，为每个问题提取相关上下文信息：

Q&A序列：
{{qa_sequence}}

要求：
1. 为每个问题分析是否依赖于前面的对话内容
2. 如果依赖，提取相关的关键上下文信息
3. 如果不依赖，上下文为空
4. 确保上下文+问题+答案能够独立理解

请按以下JSON格式返回结果：
[
  {
    "index": 0,
    "context": "上下文内容或空字符串",
  },
  ...
]"""

    def __init__(self, **kwargs):
        super().__init__(
            system_prompt=self.DEFAULT_SYSTEM_PROMPT,
            user_prompt_template=self.DEFAULT_USER_TEMPLATE,
            **kwargs,
        )

    async def step(self, context: AIContext = None, **kwargs) -> str:
        """执行一步推理，提取上下文"""
        if context is None:
            working_context = AIContext()
        else:
            working_context = context
        
        # 添加系统提示词
        working_context.add_system_prompt(self.system_prompt)

        if not self.user_template:
            raise ValueError("User template is not set")

        user_prompt = self._render_user_prompt(**kwargs)
        working_context.add_user_prompt(user_prompt)

        try:
            response = await self.llm_engine.ask(working_context.to_openai_format())
            working_context.add_assistant(response)
            return response
        except Exception as e:
            logger.error(f"Context extraction failed: {e}")
            raise

    async def transform_qa_to_cqa(self, qa_list: QAList, context: Optional[AIContext] = None) -> CQAList:
        """
        将Q&A列表转换为C&Q&A列表（批量处理，一次LLM调用）

        Args:
            qa_list: 原始Q&A列表

        Returns:
            转换后的C&Q&A列表
        """
        if not qa_list.items:
            return CQAList(session_id=qa_list.session_id)

        # 构建完整的Q&A序列文本
        qa_sequence_parts = []
        for i, qa_item in enumerate(qa_list.items):
            qa_sequence_parts.append(f"{i}. Q: {qa_item.question}")
            qa_sequence_parts.append(f"   A: {qa_item.answer}")

        qa_sequence = "\n".join(qa_sequence_parts)

        # 一次LLM调用处理整个序列
        try:
            response = await self.step(context=context, qa_sequence=qa_sequence)
            result_data = self._parse_batch_response(response)

            # 构建BQA列表
            bqa_list = BQAList(session_id=qa_list.session_id)

            for item_data in result_data:
                index = item_data.get("index", 0)
                # Try both old "context" and new "background" for compatibility
                background = item_data.get("background", item_data.get("context", "")).strip()

                # 使用原始数据或解析结果
                if index < len(qa_list.items):
                    original_qa = qa_list.items[index]
                    cqa_list.add_cqa(
                        context=context,
                        question=original_qa.question,
                        answer=original_qa.answer,
                        metadata=original_qa.metadata,
                    )

            return bqa_list

        except Exception as e:
            logger.error(f"Batch context extraction failed: {e}")
            # 降级到简单处理：第一个问题无上下文，其他问题使用基本规则
            return self._fallback_transform(qa_list)

    def _parse_batch_response(self, response: str) -> list:
        """解析LLM批量响应"""
        import json
        import re

        # 尝试提取JSON部分
        json_match = re.search(r"\[.*\]", response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # 如果JSON解析失败，使用正则表达式解析
        return self._parse_text_response(response)

    def _parse_text_response(self, response: str) -> list:
        """解析文本格式的响应"""
        results = []
        lines = response.split("\n")
        current_item = {}

        for line in lines:
            line = line.strip()
            if line.startswith("index:") or line.startswith('"index":'):
                if current_item:
                    results.append(current_item)
                current_item = {"index": len(results)}
            elif line.startswith("context:") or line.startswith('"context":'):
                context = line.split(":", 1)[1].strip().strip('"')
                current_item["context"] = context

        if current_item:
            results.append(current_item)

        return results

    def _fallback_transform(self, qa_list: QAList) -> CQAList:
        """降级处理方案"""
        cqa_list = CQAList(session_id=qa_list.session_id)

        for i, qa_item in enumerate(qa_list.items):
            context = ""
            if i > 0:
                # 简单规则：如果问题包含指代词，使用前一个问答作为上下文
                question_lower = qa_item.question.lower()
                dependency_keywords = [
                    "它",
                    "这个",
                    "那个",
                    "上面",
                    "前面",
                    "刚才",
                    "之前",
                ]

                if any(keyword in question_lower for keyword in dependency_keywords):
                    prev_qa = qa_list.items[i - 1]
                    context = f"前面提到：Q: {prev_qa.question} A: {prev_qa.answer}"

            cqa_list.add_cqa(
                context=context,
                question=qa_item.question,
                answer=qa_item.answer,
                metadata=qa_item.metadata,
            )

        return bqa_list
