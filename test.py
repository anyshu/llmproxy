from openai import AsyncOpenAI
import asyncio
import json
import time
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Create AsyncOpenAI client
client = AsyncOpenAI(
    base_url="http://localhost:3000/v1",
    api_key=os.getenv('OPENAI_API_KEY'),  # Use the actual API key from environment
    timeout=60.0
)

async def test_chat_completion():
    """Test regular chat completion"""
    try:
        print("\n=== Chat Completion Test ===")
        print("Sending request...", flush=True)
        
        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What's the capital of France?"}
            ],
            temperature=0.7,
            max_tokens=100
        )
        
        print(f"Response received:")
        print(f"Content: {response.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"Chat completion test failed: {str(e)}")
        return False

async def test_stream_chat_completion():
    """Test streaming chat completion"""
    try:
        print("\n=== Stream Chat Completion Test ===")
        print("Sending streaming request...", flush=True)
        print("Response: ", end="", flush=True)
        
        stream = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Count from 1 to 5 slowly."}
            ],
            stream=True,
            temperature=0.7,
            max_tokens=100
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="", flush=True)
        print("\nStream completed")
        return True
    except Exception as e:
        print(f"Stream chat completion test failed: {str(e)}")
        return False

async def test_with_retry(test_func, max_retries=3, delay=2):
    """Run a test function with retries"""
    for i in range(max_retries):
        try:
            if await test_func():
                return True
            if i < max_retries - 1:
                print(f"Retrying... ({i + 2}/{max_retries})")
                await asyncio.sleep(delay)
        except Exception as e:
            print(f"Error during test: {str(e)}")
            if i < max_retries - 1:
                print(f"Retrying... ({i + 2}/{max_retries})")
                await asyncio.sleep(delay)
    return False

async def main():
    """Run all tests"""
    print("Starting API tests...")
    print("Please ensure:")
    print("1. The proxy server (proxy_server.py) is running")
    print("2. The .env file contains valid OPENAI_API_KEY and OPENAI_API_BASE_URL")
    print("3. The proxy server port (default: 3000) is correct")
    
    # Run regular chat completion test
    chat_success = await test_with_retry(test_chat_completion)
    await asyncio.sleep(1)  # Wait between tests
    
    # Run streaming chat completion test
    stream_success = await test_with_retry(test_stream_chat_completion)
    
    # Print test results summary
    print("\n=== Test Results ===")
    print(f"Chat Completion Test: {'✅ Passed' if chat_success else '❌ Failed'}")
    print(f"Stream Chat Test: {'✅ Passed' if stream_success else '❌ Failed'}")

if __name__ == "__main__":
    asyncio.run(main())