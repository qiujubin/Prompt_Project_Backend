#!/usr/bin/env python3
"""
Test httpx in the same context as the generation code
"""

# Import exactly like in generation.py
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from services.ai import get_ai_generator
from api.v1.users import get_current_user
from database import get_db
from models.user import User
from models.drawing import Drawing
from api.v1.credits import deduct_credits, add_credits
from services.cos import COSStorageService, ImageProcessor, StorageManager
from core.logger import get_logger
import os
import tempfile
import base64
import httpx
from datetime import datetime

def test_httpx_in_context():
    print("=== Testing httpx in generation.py context ===")
    print(f"httpx module: {httpx}")
    print(f"httpx version: {httpx.__version__}")
    print(f"httpx file: {httpx.__file__}")

    # Test the specific exceptions
    try:
        print(f"httpx.ConnectError: {httpx.ConnectError}")
    except AttributeError as e:
        print(f"ERROR: httpx.ConnectError not available: {e}")

    try:
        print(f"httpx.TimeoutException: {httpx.TimeoutException}")
    except AttributeError as e:
        print(f"ERROR: httpx.TimeoutException not available: {e}")

    try:
        print(f"httpx.HTTPStatusError: {httpx.HTTPStatusError}")
    except AttributeError as e:
        print(f"ERROR: httpx.HTTPStatusError not available: {e}")

if __name__ == "__main__":
    test_httpx_in_context()
