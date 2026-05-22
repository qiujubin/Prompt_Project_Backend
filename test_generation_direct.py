#!/usr/bin/env python3
"""
Direct test of the generation API to debug the 500 error
"""
import asyncio
import httpx
import json

async def test_generation():
    """Test the generation endpoint directly"""

    # Test data
    test_data = {
        "prompt": "a beautiful landscape",
        "negative_prompt": "ugly, blurry",
        "backend": "comfyui",
        "width": 512,
        "height": 512,
        "seed": -1,
        "cfg": 7.0,
        "steps": 20,
        "sampler": "euler",
        "scheduler": "normal"
    }

    # Test token (you'll need to get a real one)
    headers = {
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkiLCJleHAiOjE3NzYyMzM1MzZ9.F8_HYBCp75mujGuQI9CyMdLMggLxSYFofIrBzPAEf8E",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            print("Testing generation endpoint...")
            response = await client.post(
                "http://localhost:4135/api/generation/draw",
                json=test_data,
                headers=headers
            )

            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")

            if response.status_code == 200:
                result = response.json()
                print(f"Success: {json.dumps(result, indent=2)}")
            else:
                print(f"Error Response: {response.text}")

        except Exception as e:
            print(f"Request failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_generation())
