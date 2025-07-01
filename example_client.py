"""Example client for testing the LyBot API with OpenAI-compatible interface."""

import asyncio
import httpx
import json
from typing import AsyncGenerator


async def chat_completion_example():
    """Example of non-streaming chat completion."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/v1/chat/completions",
            json={
                "model": "lybot-gemini",
                "messages": [
                    {"role": "user", "content": "請問臺北市第7選舉區的立委是誰？"}
                ],
                "stream": False,
            },
        )
        
        if response.status_code == 200:
            data = response.json()
            print("Assistant:", data["choices"][0]["message"]["content"])
        else:
            print(f"Error: {response.status_code} - {response.text}")


async def streaming_example():
    """Example of streaming chat completion."""
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            "http://localhost:8000/v1/chat/completions",
            json={
                "model": "lybot-gemini",
                "messages": [
                    {"role": "user", "content": "請分析民主進步黨在第11屆立法院的表現"}
                ],
                "stream": True,
            },
            timeout=60.0,
        ) as response:
            print("Assistant: ", end="", flush=True)
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]  # Remove "data: " prefix
                    if data == "[DONE]":
                        print()  # New line at the end
                        break
                    try:
                        chunk = json.loads(data)
                        if "choices" in chunk and chunk["choices"]:
                            delta = chunk["choices"][0].get("delta", {})
                            if "content" in delta:
                                print(delta["content"], end="", flush=True)
                    except json.JSONDecodeError:
                        pass


async def conversation_example():
    """Example of multi-turn conversation with session management."""
    session_id = "test-session-123"
    
    async with httpx.AsyncClient() as client:
        # First message
        print("User: 請問台灣民眾黨有幾個立委？")
        response = await client.post(
            "http://localhost:8000/v1/chat/completions",
            json={
                "model": "lybot-gemini",
                "messages": [
                    {"role": "user", "content": "請問台灣民眾黨有幾個立委？"}
                ],
                "user": session_id,  # Session ID for conversation tracking
                "stream": False,
            },
        )
        
        if response.status_code == 200:
            data = response.json()
            print("Assistant:", data["choices"][0]["message"]["content"])
            print()
        
        # Follow-up message
        print("User: 他們分別是誰？")
        response = await client.post(
            "http://localhost:8000/v1/chat/completions",
            json={
                "model": "lybot-gemini",
                "messages": [
                    {"role": "user", "content": "他們分別是誰？"}
                ],
                "user": session_id,  # Same session ID
                "stream": False,
            },
        )
        
        if response.status_code == 200:
            data = response.json()
            print("Assistant:", data["choices"][0]["message"]["content"])


async def openai_sdk_example():
    """Example using OpenAI Python SDK (requires: pip install openai)."""
    try:
        from openai import AsyncOpenAI
        
        # Configure client to point to local API
        client = AsyncOpenAI(
            base_url="http://localhost:8000/v1",
            api_key="not-needed",  # API key not required for local instance
        )
        
        # Create chat completion
        response = await client.chat.completions.create(
            model="lybot-gemini",
            messages=[
                {"role": "user", "content": "請查詢最近關於AI相關的法案"}
            ],
            stream=False,
        )
        
        print("Using OpenAI SDK:")
        print("Assistant:", response.choices[0].message.content)
        
    except ImportError:
        print("OpenAI SDK not installed. Install with: pip install openai")


async def main():
    """Run all examples."""
    print("=== LyBot API Examples ===\n")
    
    print("1. Simple Chat Completion:")
    print("-" * 50)
    await chat_completion_example()
    print()
    
    print("2. Streaming Response:")
    print("-" * 50)
    await streaming_example()
    print()
    
    print("3. Multi-turn Conversation:")
    print("-" * 50)
    await conversation_example()
    print()
    
    print("4. OpenAI SDK Compatibility:")
    print("-" * 50)
    await openai_sdk_example()


if __name__ == "__main__":
    print("Make sure the API server is running with: ./run_api.sh")
    print("Press Enter to continue...")
    input()
    
    asyncio.run(main())