"""
Token Counter for tracking LLM usage statistics
"""

from pydantic import BaseModel


class TokenCounter(BaseModel):
    """Token计数器

    用于统计LLM调用的token使用情况

    Attributes:
        llm_calling_times (int): LLM调用次数
        total_input_token (int): 总输入token数
        total_output_token (int): 总输出token数
    """
    llm_calling_times: int = 0
    total_input_token: int = 0
    total_output_token: int = 0

    def add_call(self, input_tokens: int = 0, output_tokens: int = 0) -> None:
        """添加一次LLM调用的统计信息

        Args:
            input_tokens: 输入token数量
            output_tokens: 输出token数量
        """
        self.llm_calling_times += 1
        self.total_input_token += input_tokens
        self.total_output_token += output_tokens

    def reset(self) -> None:
        """重置计数器"""
        self.llm_calling_times = 0
        self.total_input_token = 0
        self.total_output_token = 0

    @property
    def total_tokens(self) -> int:
        """总token数量"""
        return self.total_input_token + self.total_output_token

    def __str__(self) -> str:
        """字符串表示"""
        return (
            f"TokenCounter(calls={self.llm_calling_times}, "
            f"input={self.total_input_token}, "
            f"output={self.total_output_token}, "
            f"total={self.total_tokens})"
        )