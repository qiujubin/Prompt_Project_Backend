#!/usr/bin/env python3
"""
Test the exact model fetching code that's causing the SSL error
"""
import asyncio
import httpx
from services.ai.comfyui import ComfyUIGenerator

async def test_model_fetch():
    """Test the model fetching that's failing"""

    print("=== Testing ComfyUI Model Fetching ===")

    generator = ComfyUIGenerator()

    # Test the exact code path that's failing
    try:
        result = await generator.generate_image(
            prompt="test prompt",
            negative_prompt="",
            params={
                "width": 512,
                "height": 512,
                "seed": -1,
                "cfg": 7.0,
                "steps": 20,
                "sampler": "euler",
                "scheduler": "normal"
                # No model_name specified - this should trigger the model fetching
            }
        )
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_model_fetch())
