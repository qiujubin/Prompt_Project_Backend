#!/usr/bin/env python3
"""
Direct API test to reproduce the 500 error
"""
import asyncio
import httpx
import json

async def test_generation_api():
    """Test the generation API directly"""
    try:
        # Test data similar to frontend request
        data = {
            "prompt": "test",
            "negative_prompt": "",
            "width": 512,
            "height": 512,
            "cfg": 7,
            "steps": 20,
            "sampler": "euler",
            "backend": "comfyui"
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkiLCJleHAiOjE3NzYyMzM1MzZ9.F8_HYBCp75mujGuQI9CyMdLMggLxSYFofIrBzPAEf8E"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            print("Testing generation API...")
            response = await client.post(
                "http://localhost:4135/api/generation/draw",
                json=data,
                headers=headers
            )

            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")

            if response.status_code != 200:
                print(f"Error response: {response.text}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_generation_api())
