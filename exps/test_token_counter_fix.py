#!/usr/bin/env python3
"""
Token Counter Fix Test

Test to verify that token counting is working correctly after fixing
the session ID mismatch issue.
"""

import asyncio
import json
import os
from typing import Dict, Any

import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_BASE_URL = "http://localhost:8000"
CHAT_ENDPOINT = f"{API_BASE_URL}/chat"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-openai-api-key")


def create_simple_test_payload() -> Dict[str, Any]:
    """Create a simple test payload for token counting verification"""
    return {
        "user_message": "Hello! Please tell me a short joke.",
        "edited_last_response": "",
        "recall_last_user_message": False,
        "settings": {
            "api_key": OPENAI_API_KEY,
            "chat_model": "gpt-4o-mini",  # Using cheaper model for testing
            "base_url": "https://api.openai.com/v1/",
            "top_p": 1.0,
            "temperature": 0.7,
            "top_k": 5,
            "vector_db_url": "http://weaviate:8080",
            "global_prompt": "You are a helpful assistant. Keep responses short and concise.",
            "max_history_len": 256,
            "state_machine": {},
            "agent_name": "TokenTestAgent",
        },
        "memory": {
            "history": [],
        },
        "request_tools": [],
    }


async def test_token_counting():
    """Test token counting functionality"""
    print("🧪 Testing Token Counter Fix")
    print("=" * 50)

    payload = create_simple_test_payload()

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            print("📤 Sending request to chat API...")
            response = await client.post(CHAT_ENDPOINT, json=payload)

            if response.status_code == 200:
                result = response.json()
                print("✅ Request successful!")
                print(f"🤖 Response: {result.get('response', 'No response')}")
                print()
                print("📊 Token Statistics:")
                print(f"   Input tokens:  {result.get('total_input_token', 0)}")
                print(f"   Output tokens: {result.get('total_output_token', 0)}")
                print(f"   Total tokens:  {result.get('total_input_token', 0) + result.get('total_output_token', 0)}")
                print(f"   LLM calls:     {result.get('llm_calling_times', 0)}")
                print()

                # Check if token counting is working
                input_tokens = result.get('total_input_token', 0)
                output_tokens = result.get('total_output_token', 0)
                total_tokens = input_tokens + output_tokens

                if total_tokens > 0:
                    print("✅ Token counting is working correctly!")
                    print(f"   Detected {total_tokens} total tokens")

                    # Rough estimate check (input should be reasonable for our prompt)
                    if input_tokens > 10 and output_tokens > 5:
                        print("✅ Token counts look reasonable")
                    else:
                        print("⚠️  Token counts seem low, but counting is working")
                else:
                    print("❌ Token counting still shows 0 - issue not resolved")

            else:
                print(f"❌ Request failed with status {response.status_code}")
                print(f"Error: {response.text}")

    except Exception as e:
        print(f"❌ Error during test: {str(e)}")


async def main():
    """Main test function"""
    print("Token Counter Fix Verification")
    print("=" * 50)
    print("This test verifies that the session ID mismatch")
    print("between chat_api.py and chat_v1_5_service.py has been fixed.")
    print()

    if OPENAI_API_KEY == "your-openai-api-key":
        print("⚠️  Warning: Please set OPENAI_API_KEY in your .env file")
        print("Continuing with placeholder key (test will likely fail)")
        print()

    await test_token_counting()

    print()
    print("=" * 50)
    print("Test completed!")
    print()
    print("💡 If token counting is still showing 0:")
    print("1. Check that your OpenAI API key is valid")
    print("2. Verify the FastAPI server is running")
    print("3. Check server logs for any errors")


if __name__ == "__main__":
    asyncio.run(main())