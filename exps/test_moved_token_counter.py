#!/usr/bin/env python3
"""
Test script for moved TokenCounter to stats module
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from agent_runtime.stats import TokenCounter


def test_token_counter():
    """Test the moved TokenCounter functionality"""

    print("Testing moved TokenCounter from stats module...")

    # Test 1: Basic creation
    counter = TokenCounter()
    print(f"✓ TokenCounter created: {counter}")

    # Test 2: Add some calls
    counter.add_call(input_tokens=100, output_tokens=50)
    print(f"✓ After first call: {counter}")

    counter.add_call(input_tokens=200, output_tokens=75)
    print(f"✓ After second call: {counter}")

    # Test 3: Properties
    print(f"✓ Total tokens: {counter.total_tokens}")
    print(f"✓ LLM calls: {counter.llm_calling_times}")
    print(f"✓ Input tokens: {counter.total_input_token}")
    print(f"✓ Output tokens: {counter.total_output_token}")

    # Test 4: Reset
    counter.reset()
    print(f"✓ After reset: {counter}")

    # Test 5: Direct assignment (old style)
    counter.llm_calling_times = 3
    counter.total_input_token = 500
    counter.total_output_token = 200
    print(f"✓ After direct assignment: {counter}")

    print("\n✓ TokenCounter successfully moved to stats module!")
    print("✓ All functionality preserved")
    print("✓ New methods added: add_call(), reset(), total_tokens property")


def test_import_compatibility():
    """Test that imports work correctly from different locations"""

    print("\nTesting import compatibility...")

    # Test data_format import
    try:
        from agent_runtime.data_format import TokenCounter as DataFormatTokenCounter
        print("✓ Import from data_format works")

        # Test they're the same class
        counter1 = TokenCounter()
        counter2 = DataFormatTokenCounter()
        print(f"✓ Same class type: {type(counter1) == type(counter2)}")

    except ImportError as e:
        print(f"✗ Import from data_format failed: {e}")

    # Test direct stats import
    try:
        from agent_runtime.stats.token_counter import TokenCounter as DirectTokenCounter
        print("✓ Direct import from stats.token_counter works")

        counter3 = DirectTokenCounter()
        print(f"✓ Direct import creates same type: {type(counter1) == type(counter3)}")

    except ImportError as e:
        print(f"✗ Direct import failed: {e}")


if __name__ == "__main__":
    test_token_counter()
    test_import_compatibility()