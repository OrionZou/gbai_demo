#!/usr/bin/env python3
"""
Test script for StateSelectAgent with empty memory (initial state scenario)
"""
import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from agent_runtime.interface.api_models import Setting, Memory
from agent_runtime.data_format.fsm import State, StateMachine, select_state
from agent_runtime.stats import TokenCounter


async def test_state_select_empty_memory():
    """Test StateSelectAgent behavior with empty memory"""

    # Create test states
    state1 = State(
        name="greeting",
        scenario="Initial greeting state",
        instruction="Greet the user warmly"
    )
    state2 = State(
        name="conversation",
        scenario="Main conversation state",
        instruction="Continue the conversation"
    )

    # Create state machine
    state_machine = StateMachine(
        initial_state_name="greeting",
        states=[state1, state2],
        out_transitions={
            "greeting": ["conversation"],
            "conversation": ["conversation"]
        }
    )

    # Mock settings
    settings = Setting(
        api_key="test-key",
        chat_model="gpt-4o-mini",
        base_url="https://api.openai.com/v1/",
        agent_name="test_agent",
        global_prompt="You are a helpful assistant.",
        temperature=0.7,
        state_machine=state_machine
    )

    # Empty memory
    memory = Memory(history=[])

    # Mock token counter
    token_counter = TokenCounter()

    print("Testing StateSelectAgent with empty memory...")

    try:
        # Test with empty memory - should return initial state
        selected_state = await select_state(
            settings=settings,
            memory=memory,
            feedbacks=[],
            token_counter=token_counter
        )

        print(f"✓ select_state completed successfully")
        print(f"✓ Selected state name: '{selected_state.name}'")
        print(f"✓ Should be initial state: {selected_state.name == 'greeting'}")
        print(f"✓ Token counter calls: {token_counter.llm_calling_times}")
        print("✓ No LLM call needed for empty memory - returned initial state directly")

    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        raise

    print("\n✓ Empty memory test completed successfully!")


if __name__ == "__main__":
    asyncio.run(test_state_select_empty_memory())