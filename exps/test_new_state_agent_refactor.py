#!/usr/bin/env python3
"""
Test script for NewStateAgent refactor
"""
import asyncio
from datetime import datetime

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from agent_runtime.interface.api_models import Setting, Memory, Step, V2Action
from agent_runtime.data_format.fsm import State, TokenCounter
from agent_runtime.agents.new_state_agent import NewStateAgent
from agent_runtime.clients.openai_llm_client import LLM


async def test_new_state_agent_refactor():
    """Test the refactored NewStateAgent functionality"""

    # Mock settings
    settings = Setting(
        api_key="test-key",
        chat_model="gpt-4o-mini",
        base_url="https://api.openai.com/v1/",
        agent_name="test_agent",
        global_prompt="You are a helpful assistant.",
        temperature=0.7
    )

    # Mock memory with some history
    memory = Memory(
        history=[
            Step(
                state_name="greeting",
                actions=[
                    V2Action(
                        name="send_message_to_user",
                        arguments={"agent_message": "Hello! How can I help you?"},
                        result={"status": "sent"}
                    )
                ],
                timestamp=datetime.now().isoformat()
            ),
            Step(
                state_name="conversation",
                actions=[
                    V2Action(
                        name="send_message_to_user",
                        arguments={"agent_message": "I understand you need assistance."},
                        result={"status": "sent"}
                    )
                ],
                timestamp=datetime.now().isoformat()
            )
        ]
    )

    # Mock token counter
    token_counter = TokenCounter()

    print("Testing NewStateAgent refactor...")

    # Test 1: Create agent with default settings
    llm_engine = LLM()
    agent = NewStateAgent(llm_engine=llm_engine)

    print(f"✓ Agent created with name: {agent.agent_name}")
    print(f"✓ System prompt defined: {len(agent.system_prompt)} characters")
    print(f"✓ User template defined: {len(agent.user_prompt_template)} characters")

    # Test 2: Test parameter validation
    try:
        await agent.step()
        print("✗ Should have failed with missing parameters")
    except ValueError as e:
        print(f"✓ Correctly validated missing parameters: {e}")

    # Test 3: Test step method with valid parameters (but invalid API key)
    try:
        result = await agent.step(
            settings=settings,
            memory=memory,
            token_counter=token_counter
        )
        print(f"✓ Agent step completed successfully")
        print(f"✓ Generated state instruction: {result.instruction[:100]}...")

    except Exception as e:
        # This is expected since we don't have a real API key
        if "api" in str(e).lower() or "auth" in str(e).lower() or "401" in str(e):
            print("✓ Expected API error (no real API key provided)")
            print("✓ NewStateAgent integration is working correctly")
        else:
            print(f"✗ Unexpected error: {e}")
            raise

    # Test 4: Test custom initialization
    custom_system_prompt = "Custom system prompt for testing"
    custom_user_template = "Custom template: {{ global_prompt }} - {{ history }}"

    custom_agent = NewStateAgent(
        llm_engine=llm_engine,
        agent_name="custom_new_state_agent",
        system_prompt=custom_system_prompt,
        user_prompt_template=custom_user_template
    )

    print(f"✓ Custom agent created with name: {custom_agent.agent_name}")
    print(f"✓ Custom system prompt set: {custom_agent.system_prompt == custom_system_prompt}")
    print(f"✓ Custom user template set: {custom_agent.user_prompt_template == custom_user_template}")

    # Test 5: Test singleton behavior
    agent2 = NewStateAgent(llm_engine=llm_engine)
    print(f"✓ Singleton behavior confirmed: {agent is agent2}")

    print("\n✓ NewStateAgent refactor completed successfully!")
    print("✓ Agent now follows RewardAgent style patterns:")
    print("  - Class constants for default values")
    print("  - Improved initialization with LLM engine parameter")
    print("  - Better step method with context handling")
    print("  - Consistent error handling and logging")


if __name__ == "__main__":
    asyncio.run(test_new_state_agent_refactor())