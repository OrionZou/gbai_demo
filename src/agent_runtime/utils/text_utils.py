"""
文本处理工具模块

包含各种文本处理相关的工具函数
"""

import re


def safe_to_int(text: str) -> int:
    """从给定字符串中提取第一个有效整数

    如果没有找到有效整数，函数返回 `0`。它使用正则表达式来搜索第一个数字序列，
    可选地带有负号前缀 (`-`)。

    Args:
        text (str): 可能包含整数的输入字符串

    Returns:
        int: 字符串中找到的第一个整数，如果没有找到则返回 `0`

    Example:
        >>> safe_to_int("Price: -42 USD")
        -42
        >>> safe_to_int("No numbers here")
        0
        >>> safe_to_int("100 apples")
        100
        >>> safe_to_int("--45 banana")
        -45
    """
    matched = re.search(r"-?\d+", text)  # Find first integer in `text`
    return int(matched.group()) if matched else 0