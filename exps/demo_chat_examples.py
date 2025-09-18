#!/usr/bin/env python3
"""
Chat API Examples Demo

This script demonstrates all the chat interface examples:
1. OpenAI Chat with String Format
2. OpenAI Chat with ChatML Messages Format
3. OpenAI API completed example with ChatML Messages Format
4. Deepseek completed example with ChatML Messages Format
5. DeepInfra completed example with ChatML Messages Format
6. OpenAI Chat with Image

Usage:
    python exps/demo_chat_examples.py
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

# API Keys from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-openai-api-key")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "your-deepseek-api-key")
DEEPINFRA_API_KEY = os.getenv("DEEPINFRA_API_KEY", "your-deepinfra-api-key")


def create_openai_string_format_example() -> Dict[str, Any]:
    """OpenAI Chat with String Format - 字串格式"""
    return {
        "user_message": "您好，請問您今天可以如何協助我？",
        "edited_last_response": "",
        "recall_last_user_message": False,
        "settings": {
            "api_key": OPENAI_API_KEY,
            "chat_model": "gpt-4o",
            "base_url": "https://api.openai.com/v1/",
            "top_p": 1.0,
            "temperature": 0.7,
            "top_k": 5,
            "vector_db_url": "http://weaviate:8080",
            "global_prompt": "您是一個樂於助人的 AI 助手。請提供清晰準確的回應，使用繁體中文。",
            "max_history_len": 256,
            "state_machine": {},
            "agent_name": "OpenAIAgent",
        },
        "memory": {
            "history": [],
        },
        "request_tools": [],
    }


def create_openai_chatml_example() -> Dict[str, Any]:
    """OpenAI Chat with ChatML Messages Format"""
    return {
        "user_message": [
            {
                "role": "system",
                "content": "You are a helpful AI assistant that provides detailed and accurate responses.",
            },
            {"role": "user", "content": "What is artificial intelligence and how does it work?"},
        ],
        "edited_last_response": "",
        "recall_last_user_message": False,
        "settings": {
            "api_key": OPENAI_API_KEY,
            "chat_model": "gpt-4o",
            "base_url": "https://api.openai.com/v1/",
            "top_p": 1.0,
            "temperature": 0.7,
            "top_k": 5,
            "vector_db_url": "http://weaviate:8080",
            "global_prompt": "You are a professional AI assistant with expertise in technology and science.",
            "max_history_len": 256,
            "state_machine": {},
            "agent_name": "OpenAIAssistant",
        },
        "memory": {
            "history": [],
        },
        "request_tools": [],
    }


def create_openai_completed_chatml_example() -> Dict[str, Any]:
    """OpenAI API completed example with ChatML Messages Format"""
    return {
        "user_message": [
            {
                "role": "system",
                "content": "You are a professional assistant that helps users with time and weather information. Be helpful and accurate.",
            },
            {"role": "user", "content": "Hello! Can you help me with the current time?"},
        ],
        "edited_last_response": "",
        "recall_last_user_message": False,
        "settings": {
            "api_key": OPENAI_API_KEY,
            "chat_model": "gpt-4o",
            "base_url": "https://api.openai.com/v1/",
            "top_p": 1.0,
            "temperature": 0.7,
            "top_k": 5,
            "vector_db_url": "http://weaviate:8080",
            "global_prompt": "You are a professional assistant specialized in providing time and weather information.",
            "max_history_len": 256,
            "agent_name": "TimeWeatherAgent",
            "state_machine": {
                "initial_state_name": "greeting",
                "states": [
                    {
                        "name": "greeting",
                        "scenario": "Assistant greets the user",
                        "instruction": "Politely greet the user and ask how you can help",
                    },
                    {
                        "name": "time_inquiry",
                        "scenario": "User asks time-related questions",
                        "instruction": "Use appropriate tools to answer time-related questions accurately",
                    },
                    {
                        "name": "weather_inquiry",
                        "scenario": "User asks weather-related questions",
                        "instruction": "Use appropriate tools to provide weather information",
                    },
                    {
                        "name": "general_assistance",
                        "scenario": "User asks about other topics",
                        "instruction": "Politely guide the conversation back to time and weather topics",
                    },
                ],
                "out_transitions": {
                    "greeting": ["time_inquiry", "weather_inquiry", "general_assistance"],
                    "time_inquiry": ["weather_inquiry", "general_assistance"],
                    "weather_inquiry": ["time_inquiry", "general_assistance"],
                    "general_assistance": ["time_inquiry", "weather_inquiry"],
                },
            },
        },
        "memory": {
            "history": [],
        },
        "request_tools": [
            {
                "name": "get_time",
                "description": "Get current time for specified coordinates",
                "url": "https://timeapi.io/api/time/current/coordinate",
                "method": "GET",
                "headers": {"Content-Type": "application/json"},
                "request_params": {
                    "latitude": {
                        "type": ["number", "null"],
                        "description": "The latitude coordinate",
                    },
                    "longitude": {
                        "type": ["number", "null"],
                        "description": "The longitude coordinate",
                    },
                },
                "request_json": None,
            },
            {
                "name": "get_weather",
                "description": "Get current weather information",
                "url": "https://api.open-meteo.com/v1/forecast?current=temperature_2m,wind_speed_10m,weather_code",
                "method": "GET",
                "headers": {"Content-Type": "application/json"},
                "request_params": {
                    "latitude": {
                        "type": "number",
                        "description": "The latitude coordinate",
                    },
                    "longitude": {
                        "type": "number",
                        "description": "The longitude coordinate",
                    },
                },
                "request_json": None,
            },
        ],
    }


def create_deepseek_completed_chatml_example() -> Dict[str, Any]:
    """Deepseek completed example with ChatML Messages Format"""
    return {
        "user_message": [
            {
                "role": "system",
                "content": "You are an intelligent AI assistant powered by Deepseek. Provide helpful, accurate, and thoughtful responses.",
            },
            {"role": "user", "content": "Can you explain how large language models work?"},
        ],
        "edited_last_response": "",
        "recall_last_user_message": False,
        "settings": {
            "api_key": DEEPSEEK_API_KEY,
            "chat_model": "deepseek-chat",
            "base_url": "https://api.deepseek.com/v1",
            "top_p": 0.95,
            "temperature": 0.8,
            "top_k": 5,
            "vector_db_url": "http://weaviate:8080",
            "global_prompt": "You are an expert AI assistant specializing in technology and scientific explanations. Provide clear, detailed responses.",
            "max_history_len": 512,
            "state_machine": {
                "initial_state_name": "introduction",
                "states": [
                    {
                        "name": "introduction",
                        "scenario": "Initial interaction with user",
                        "instruction": "Introduce yourself and understand the user's needs",
                    },
                    {
                        "name": "technical_explanation",
                        "scenario": "User asks for technical explanations",
                        "instruction": "Provide detailed, accurate technical explanations with examples",
                    },
                    {
                        "name": "clarification",
                        "scenario": "User needs clarification or has follow-up questions",
                        "instruction": "Ask clarifying questions and provide targeted explanations",
                    },
                ],
                "out_transitions": {
                    "introduction": ["technical_explanation", "clarification"],
                    "technical_explanation": ["clarification", "technical_explanation"],
                    "clarification": ["technical_explanation", "introduction"],
                },
            },
            "agent_name": "DeepseekExpert",
        },
        "memory": {
            "history": [],
        },
        "request_tools": [],
    }


def create_deepinfra_completed_chatml_example() -> Dict[str, Any]:
    """DeepInfra completed example with ChatML Messages Format"""
    return {
        "user_message": [
            {
                "role": "system",
                "content": "You are an AI assistant powered by DeepInfra's infrastructure. Provide comprehensive and well-structured responses.",
            },
            {"role": "user", "content": "What are the benefits of using cloud-based AI inference?"},
            {
                "role": "assistant",
                "content": "Cloud-based AI inference offers several key benefits including scalability, cost-effectiveness, and access to powerful hardware without upfront investment.",
            },
            {"role": "user", "content": "Can you elaborate on the scalability aspect?"},
        ],
        "edited_last_response": "",
        "recall_last_user_message": False,
        "settings": {
            "api_key": DEEPINFRA_API_KEY,
            "chat_model": "meta-llama/Meta-Llama-3.1-405B-Instruct",
            "base_url": "https://api.deepinfra.com/v1/openai",
            "top_p": 0.9,
            "temperature": 0.7,
            "top_k": 5,
            "vector_db_url": "http://weaviate:8080",
            "global_prompt": "You are a knowledgeable AI assistant with expertise in cloud computing and AI infrastructure. Provide detailed, practical insights.",
            "max_history_len": 512,
            "state_machine": {
                "initial_state_name": "consultation",
                "states": [
                    {
                        "name": "consultation",
                        "scenario": "Providing expert consultation on AI and cloud topics",
                        "instruction": "Engage in detailed technical discussions and provide expert insights",
                    },
                    {
                        "name": "deep_dive",
                        "scenario": "User wants detailed technical information",
                        "instruction": "Provide comprehensive technical explanations with practical examples",
                    },
                    {
                        "name": "solution_design",
                        "scenario": "User needs help designing solutions",
                        "instruction": "Help design and architect AI solutions based on requirements",
                    },
                ],
                "out_transitions": {
                    "consultation": ["deep_dive", "solution_design"],
                    "deep_dive": ["solution_design", "consultation"],
                    "solution_design": ["deep_dive", "consultation"],
                },
            },
            "agent_name": "DeepInfraConsultant",
        },
        "memory": {
            "history": [],
        },
        "request_tools": [],
    }


def create_openai_with_image_example() -> Dict[str, Any]:
    """OpenAI Chat with Image"""
    # A simple 1x1 pixel transparent PNG encoded in base64 for demo
    transparent_pixel = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAI9jU77mgAAAABJRU5ErkJggg=="

    return {
        "user_message": [
            {
                "role": "system",
                "content": "You are a helpful AI assistant that can analyze images and answer questions about visual content. Provide detailed and accurate descriptions.",
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "What do you see in this image? Please describe it in detail."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{transparent_pixel}",
                            "detail": "high"
                        }
                    }
                ]
            }
        ],
        "edited_last_response": "",
        "recall_last_user_message": False,
        "settings": {
            "api_key": OPENAI_API_KEY,
            "chat_model": "gpt-4o",
            "base_url": "https://api.openai.com/v1/",
            "top_p": 1.0,
            "temperature": 0.7,
            "top_k": 5,
            "vector_db_url": "http://weaviate:8080",
            "global_prompt": "You are a professional image analysis assistant. Provide detailed, accurate descriptions and insights about visual content.",
            "max_history_len": 256,
            "state_machine": {},
            "agent_name": "VisionAssistant",
        },
        "memory": {
            "history": [],
        },
        "request_tools": [],
    }


async def test_chat_example(name: str, payload: Dict[str, Any], dry_run: bool = True) -> None:
    """Test a chat example"""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"{'='*60}")

    if dry_run:
        print("DRY RUN - Payload structure:")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(CHAT_ENDPOINT, json=payload)

            if response.status_code == 200:
                result = response.json()
                print(f"✅ Success!")
                print(f"Response: {result.get('response', 'No response')}")
                print(f"Tokens - Input: {result.get('total_input_token', 0)}, Output: {result.get('total_output_token', 0)}")
                print(f"LLM calls: {result.get('llm_calling_times', 0)}")
            else:
                print(f"❌ Failed with status {response.status_code}")
                print(f"Error: {response.text}")

    except Exception as e:
        print(f"❌ Error: {str(e)}")


async def main():
    """Main demo function"""
    print("Chat API Examples Demo")
    print("=" * 60)

    examples = [
        ("OpenAI String Format", create_openai_string_format_example()),
        ("OpenAI ChatML Messages", create_openai_chatml_example()),
        ("OpenAI Completed ChatML", create_openai_completed_chatml_example()),
        ("Deepseek Completed ChatML", create_deepseek_completed_chatml_example()),
        ("DeepInfra Completed ChatML", create_deepinfra_completed_chatml_example()),
        ("OpenAI with Image", create_openai_with_image_example()),
    ]

    # Set to True to actually call the API, False for dry run
    dry_run = True

    if dry_run:
        print("🔍 DRY RUN MODE - Showing payload structures")
        print("Set dry_run=False to actually test API calls")
    else:
        print("🚀 LIVE MODE - Making actual API calls")
        print(f"API Endpoint: {CHAT_ENDPOINT}")

    for name, example in examples:
        await test_chat_example(name, example, dry_run=dry_run)

    print(f"\n{'='*60}")
    print("Demo completed!")
    if dry_run:
        print("To test with real API calls:")
        print("1. Start your FastAPI server: uvicorn main:app --reload")
        print("2. Set your API keys in .env file")
        print("3. Change dry_run=False in this script")


if __name__ == "__main__":
    asyncio.run(main())