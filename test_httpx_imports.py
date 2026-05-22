#!/usr/bin/env python3
"""
Test httpx imports to see what's available
"""
import httpx

print("=== Testing httpx imports ===")
print(f"httpx version: {httpx.__version__}")

# Test what exceptions are available
print("\nAvailable exceptions:")
for attr in dir(httpx):
    if 'Error' in attr or 'Exception' in attr:
        print(f"  {attr}: {getattr(httpx, attr)}")

# Test specific ones
try:
    print(f"\nhttpx.ConnectError: {httpx.ConnectError}")
except AttributeError as e:
    print(f"httpx.ConnectError not available: {e}")

try:
    print(f"httpx.TimeoutException: {httpx.TimeoutException}")
except AttributeError as e:
    print(f"httpx.TimeoutException not available: {e}")

try:
    print(f"httpx.HTTPStatusError: {httpx.HTTPStatusError}")
except AttributeError as e:
    print(f"httpx.HTTPStatusError not available: {e}")
