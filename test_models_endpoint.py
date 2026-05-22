#!/usr/bin/env python3
"""
Test the models endpoint directly
"""
import asyncio
import httpx

async def test_models_endpoint():
    """Test the models endpoint"""

    headers = {
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkiLCJleHAiOjE3NzYyMzM1MzZ9.F8_HYBCp75mujGuQI9CyMdLMggLxSYFofIrBzPAEf8E",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            print("Testing models endpoint...")
            response = await client.get(
                "http://localhost:4135/api/generation/models/comfyui",
                headers=headers
            )

            print(f"Status Code: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print(f"Success: {result}")
            else:
                print(f"Error Response: {response.text}")

        except Exception as e:
            print(f"Request failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_models_endpoint())
