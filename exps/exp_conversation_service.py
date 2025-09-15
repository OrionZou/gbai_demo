import uuid
from workbook_ai.application.services.conversation_service import ConversationService
from agent_runtime.clients.weaviate_client import WeaviateClient
from workbook_ai.infrastructure.config.loader import ConfigLoader
from workbook_ai.domain.message_entity import MESSAGE_CLASS, get_message_schema


def main():
    # 初始化 WeaviateClient
    config = ConfigLoader.get_weaviate_config()
    client = WeaviateClient(**config)

    # 确保 Schema 存在
    try:
        client.get_collection(MESSAGE_CLASS)
    except Exception:
        client.create_collection(
            class_name=MESSAGE_CLASS,
            properties=get_message_schema()["properties"],
            description=get_message_schema()["description"],
        )

    service = ConversationService(client)
    session_id = f"demo_session_{uuid.uuid4()}"

    # 创建对话
    print("👉 创建对话")
    service.create_message(session_id, "user", "你好，AI！")
    service.create_message(session_id, "assistant", "你好，我是 AI，可以帮你做什么？")

    # 查询对话
    print("👉 查询对话")
    messages = service.get_messages(session_id)
    for m in messages:
        print(f"[{m.role}] {m.content}")

    # 更新消息
    print("👉 更新消息")
    if messages:
        first_msg = messages[0]
        updated = service.update_message(first_msg.id, "你好，AI！（已更新）")
        print(f"更新后的消息: {updated}")

    # 删除消息
    print("👉 删除单条消息")
    if len(messages) > 1:
        service.delete_message(messages[1].id)

    # 删除会话
    print("👉 删除整个会话")
    service.delete_conversation(session_id)
    print("会话删除完成")


if __name__ == "__main__":
    main()