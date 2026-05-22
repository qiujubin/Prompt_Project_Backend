#!/usr/bin/env python3
"""
Debug the models endpoint issue
"""
import asyncio
import httpx
from core.comfyui_config import get_comfyui_settings

async def test_models_endpoint_debug():
    """Debug the models endpoint"""

    print("=== Testing ComfyUI Settings ===")
    try:
        settings = get_comfyui_settings()
        print(f"Settings loaded: {settings}")
        print(f"Base URL: {settings.base_url}")
    except Exception as e:
        print(f"Error loading settings: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n=== Testing Direct ComfyUI Connection ===")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{settings.base_url}/object_info")
            print(f"Direct connection success: {resp.status_code}")
            print(f"Content length: {len(resp.content)}")
    except Exception as e:
        print(f"Direct connection failed: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n=== Testing Models Endpoint Logic ===")
    try:
        # Simulate the models endpoint logic
        target_url = settings.base_url

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{target_url}/object_info")
            resp.raise_for_status()
            object_info = resp.json()

        # Parse model information
        models = {}

        # Checkpoints
        if "CheckpointLoaderSimple" in object_info:
            checkpoint_info = object_info["CheckpointLoaderSimple"]
            if "input" in checkpoint_info and "required" in checkpoint_info["input"]:
                ckpt_name = checkpoint_info["input"]["required"].get("ckpt_name")
                if ckpt_name and isinstance(ckpt_name, list) and len(ckpt_name) > 0:
                    models["checkpoints"] = ckpt_name[0] if isinstance(ckpt_name[0], list) else []

        print(f"Models parsed successfully: {len(models.get('checkpoints', []))} checkpoints found")
        return {"code": 200, "msg": "OK", "data": models}

    except Exception as e:
        print(f"Models endpoint logic failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_models_endpoint_debug())
