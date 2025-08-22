from workbook_ai.domain.entity.message import Message
from workbook_ai.domain.entity.content import ContentPart

if __name__ == "__main__":

    msg1 = Message(
        role="system",
        # role_name="system-1",
        content="你是一个有帮助的助手。")
    print(msg1.model_dump())

    # 复杂案例：多内容片段组合
    msg2 = Message(
        # role="user",
        # role_name="customer",
        content=[
            ContentPart(type="text", text="你好，我的订单没到，请帮我查一下。"),
            ContentPart(type="markdown", markdown="**紧急订单**，请优先处理"),
            ContentPart(type="markdown",
                        markdown="```python\nprint('订单号: 123456')\n```"),
        ], )
    print(msg2.model_dump())

    # 复杂案例：多内容片段组合
    msg3 = Message(
        role="user",
        role_name="customer",
        content=[
            {
                "type": "text",
                "text": "你好，我的订单没到，请帮我查一下。"
            },
            {
                "type": "markdown",
                "markdown": "**紧急订单**，请优先处理"
            },
            {
                "type": "markdown",
                "markdown": "```python\nprint('订单号: 123456')\n```"
            },
        ], )
    print(msg3.model_dump())
