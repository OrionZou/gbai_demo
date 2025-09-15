import pytest
import uuid

from workbook_ai.application.services.conversation_service import (
    ConversationService
)
from workbook_ai.domain.message_entity import (
    MESSAGE_CLASS,
    get_message_schema
)
from agent_runtime.clients.weaviate_client import WeaviateClient
from workbook_ai.infrastructure.config.loader import ConfigLoader


@pytest.fixture(scope="module")
def client() -> WeaviateClient:
    config = ConfigLoader.get_weaviate_config()
    client = WeaviateClient(
        base_url=config.base_url,
        api_key=config.api_key,
        embedding_api_key=config.embedding_api_key,
        module_config=config.module_config,
        timeout=config.timeout,
    )
    # 确保 schema 存在
    try:
        client.get_collection(MESSAGE_CLASS)
    except Exception:
        client.create_collection(
            class_name=MESSAGE_CLASS,
            properties=get_message_schema()["properties"],
            description=get_message_schema()["description"],
        )
    return client


@pytest.fixture
def service(client: WeaviateClient) -> ConversationService:
    return ConversationService(client)


def test_conversation_crud(service: ConversationService):
    session_id = f"test_session_{uuid.uuid4()}"
    # Create
    msg1 = service.create_message(session_id, "user", "Hello AI!")
    msg2 = service.create_message(session_id, "assistant", "Hello user!")

    assert msg1.session_id == session_id
    assert msg2.role == "assistant"

    # Read
    messages = service.get_messages(session_id)
    assert len(messages) >= 2
    contents = [m.content for m in messages]
    assert "Hello AI!" in contents

    # Update
    new_content = "Hello AI!! Updated"
    updated = service.update_message(msg1.id, new_content)
    assert updated
    assert updated.content == new_content

    # Delete single
    service.delete_message(msg2.id)
    messages_after_delete = service.get_messages(session_id)
    contents = [m.content for m in messages_after_delete]
    assert "Hello user!" not in contents

    # Delete conversation
    service.delete_conversation(session_id)
    assert service.get_messages(session_id) == []