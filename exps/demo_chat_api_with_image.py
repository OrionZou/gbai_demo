"""
演示如何使用 chat_api 接口支持图片输入

本演示展示了chat_api支持的图片输入功能：
- 网络图片URL
- Base64编码图片
- 多图片输入
- 文本+图片混合内容
- 支持从.env文件读取配置

注意：需要配置有效的OpenAI API key，并确保地区支持。
如果遇到地区限制，可以配置其他支持的LLM服务。
"""

import asyncio
import os
from dotenv import load_dotenv
import httpx

from agent_runtime.interface.api_models import ChatRequest, Setting
from agent_runtime.data_format.fsm import Memory
from agent_runtime.data_format.message import Message
from agent_runtime.data_format.content import (
    ContentPart, TextContent, ImageContent
)

# 加载环境变量
load_dotenv()


def get_env_config() -> dict:
    """从环境变量获取配置"""
    # 确保使用支持图片的模型
    model = os.getenv("LLM_MODEL", "gpt-4o")
    if model == "gpt-4.1":  # 修正无效的模型名
        model = "gpt-4o"

    return {
        "api_key": os.getenv("LLM_API_KEY", "your_api_key_here"),
        "chat_model": model,
        "base_url": os.getenv("LLM_BASE_URL", "https://api.openai.com/v1/").strip(),
        "temperature": float(os.getenv("LLM_TEMPERATURE", "0.7")),
    }


async def demo_chat_with_image() -> ChatRequest:
    """演示使用图片输入的聊天功能"""

    # 示例图片URL
    image_url = ("https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/"
                "Gfp-wisconsin-madison-the-nature-boardwalk.jpg/"
                "2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg")

    # 构建包含图片的消息
    messages = [
        Message(
            role="user",
            content=[
                ContentPart(root=TextContent(text="请描述这张图片中的内容")),
                ContentPart(root=ImageContent(image_url=image_url))
            ]
        )
    ]

    # 从环境变量获取配置
    env_config = get_env_config()

    # 配置设置
    settings = Setting(
        api_key=env_config["api_key"],
        chat_model=env_config["chat_model"],
        base_url=env_config["base_url"],
        temperature=env_config["temperature"],
        agent_name="ImageChatDemo",
        global_prompt="你是一个专业的图片分析助手，能够详细描述图片内容。"
    )

    # 创建聊天请求
    chat_request = ChatRequest(
        user_message=messages,
        settings=settings,
        memory=Memory(history=[])
    )

    print("=== 图片聊天API演示 ===")
    print(f"图片URL: {image_url}")

    # 安全地访问内容
    if isinstance(messages[0].content, list) and len(messages[0].content) > 0:
        first_content = messages[0].content[0]
        if hasattr(first_content, 'root') and hasattr(first_content.root, 'text'):
            print(f"用户消息: {first_content.root.text}")

    print("\n--- 请求数据结构 ---")
    print(f"消息格式: {type(messages[0].content).__name__}")
    if isinstance(messages[0].content, list):
        print(f"内容部分数量: {len(messages[0].content)}")

    # 将请求转换为JSON格式以便查看
    request_dict = chat_request.model_dump()
    print("\n--- Chat Request JSON结构 ---")
    print(f"user_message类型: {type(request_dict['user_message'])}")
    print(f"消息数量: {len(request_dict['user_message'])}")

    return chat_request


async def demo_local_image_base64() -> ChatRequest:
    """演示使用本地图片的base64编码"""

    # 示例base64数据（1x1像素的红色PNG）
    base64_image = ("data:image/png;base64,"
                   "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/"
                   "5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==")

    messages = [
        Message(
            role="user",
            content=[
                ContentPart(root=TextContent(text="这是什么颜色的像素？")),
                ContentPart(root=ImageContent(image_url=base64_image))
            ]
        )
    ]

    # 从环境变量获取配置
    env_config = get_env_config()

    settings = Setting(
        api_key=env_config["api_key"],
        chat_model=env_config["chat_model"],
        base_url=env_config["base_url"],
        temperature=env_config["temperature"],
        agent_name="LocalImageDemo"
    )

    chat_request = ChatRequest(
        user_message=messages,
        settings=settings,
        memory=Memory(history=[])
    )

    print("\n=== 本地图片Base64演示 ===")
    print(f"Base64前缀: {base64_image[:50]}...")
    if isinstance(messages[0].content, list):
        content_types = []
        for part in messages[0].content:
            if hasattr(part, 'root') and hasattr(part.root, 'type'):
                content_types.append(part.root.type)
        print(f"消息内容类型: {content_types}")

    return chat_request


async def demo_multiple_images() -> ChatRequest:
    """演示多图片输入"""

    images = [
        ("https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/"
         "PNG_transparency_demonstration_1.png/"
         "280px-PNG_transparency_demonstration_1.png"),
        ("https://upload.wikimedia.org/wikipedia/commons/thumb/a/a7/"
         "React-icon.svg/512px-React-icon.svg.png")
    ]

    content_parts = [
        ContentPart(root=TextContent(text="比较这两张图片的差异："))
    ]

    for img_url in images:
        content_parts.append(ContentPart(root=ImageContent(image_url=img_url)))

    messages = [Message(role="user", content=content_parts)]

    # 从环境变量获取配置
    env_config = get_env_config()

    settings = Setting(
        api_key=env_config["api_key"],
        chat_model=env_config["chat_model"],
        base_url=env_config["base_url"],
        temperature=env_config["temperature"],
        agent_name="MultiImageDemo"
    )

    chat_request = ChatRequest(
        user_message=messages,
        settings=settings,
        memory=Memory(history=[])
    )

    print("\n=== 多图片输入演示 ===")
    print(f"图片数量: {len(images)}")
    print(f"内容部分总数: {len(content_parts)}")
    print("图片URLs:")
    for i, url in enumerate(images):
        print(f"  {i+1}. {url}")

    return chat_request


async def demo_api_call_with_image() -> None:
    """演示实际调用chat API（需要配置真实的API key）"""

    # 注意：这个demo需要真实的API key才能运行
    print("\n=== API调用演示（需要真实API key） ===")

    chat_request = await demo_chat_with_image()

    # 实际调用API
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 使用model_dump(mode="json")确保datetime正确序列化
            request_data = chat_request.model_dump(mode="json")

            response = await client.post(
                "http://localhost:8011/v1.5/chat",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                result = response.json()
                print(f"API响应: {result['response']}")
                print(f"Token使用: 输入{result.get('total_input_token', 0)}, "
                      f"输出{result.get('total_output_token', 0)}")
            else:
                print(f"API调用失败: {response.status_code}")
                print(f"错误详情: {response.text}")

    except Exception as e:
        print(f"API调用异常: {str(e)}")
        print("可能的原因:")
        print("- OpenAI API key无效或地区限制")
        print("- API服务未启动")
        print("- 端口配置错误")
        print("- 请求格式问题")
        print("\n解决方案:")
        print("- 使用有效的OpenAI API key")
        print("- 或配置其他支持的LLM服务（如DeepSeek）")
        print("- 检查网络连接和地区限制")



if __name__ == "__main__":
    async def main() -> None:
        print("开始演示chat_api的图片输入功能\n")

        # 演示不同的图片输入方式
        await demo_chat_with_image()
        await demo_local_image_base64()
        await demo_multiple_images()
        await demo_api_call_with_image()

        print("\n演示完成！")
        print("\n图片输入支持的特性：")
        print("✓ 网络图片URL")
        print("✓ Base64编码的图片")
        print("✓ 多图片输入")
        print("✓ 文本+图片混合内容")
        print("✓ 兼容OpenAI ChatML格式")
        print("✓ 支持从.env文件读取配置")

    asyncio.run(main())