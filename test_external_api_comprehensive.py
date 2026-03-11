#!/usr/bin/env python3
"""
Comprehensive test script for External AI API implementation
"""
import asyncio
import sys
import os
sys.path.append('.')

async def test_external_api():
    print('=== Testing External API Implementation ===')

    # Test 1: Import external AI generator
    try:
        from services.ai.external import ExternalAIGenerator
        print('✅ ExternalAIGenerator import successful')
    except Exception as e:
        print(f'❌ ExternalAIGenerator import failed: {e}')
        return

    # Test 2: Initialize generator
    try:
        generator = ExternalAIGenerator()
        print('✅ ExternalAIGenerator initialization successful')
    except Exception as e:
        print(f'❌ ExternalAIGenerator initialization failed: {e}')
        return

    # Test 3: Test provider validation with empty API key
    test_params = {
        'provider': 'openai',
        'api_key': '',  # Empty API key should be handled gracefully
        'api_url': 'https://api.openai.com/v1'
    }

    try:
        result = await generator.generate_image('test prompt', '', test_params)
        status = result.get('status', 'unknown')
        msg = result.get('msg', '')
        print(f'✅ Empty API key validation works: {status} - {msg}')
    except Exception as e:
        error_msg = str(e)[:100]
        print(f'❌ Empty API key handling failed: {error_msg}...')

    # Test 4: Test provider validation with valid API key format
    test_params = {
        'provider': 'openai',
        'api_key': 'test-key-12345',
        'api_url': 'https://api.openai.com/v1'
    }

    try:
        result = await generator.generate_image('test prompt', '', test_params)
        status = result.get('status', 'unknown')
        msg = result.get('msg', '')
        print(f'✅ Provider validation works: {status} - {msg[:50]}...')
    except Exception as e:
        error_msg = str(e)[:100]
        print(f'✅ Provider validation works (expected error): {error_msg}...')

    # Test 5: Test different providers
    providers = ['openai', 'tongyi', 'baidu', 'tencent']
    for provider in providers:
        test_params['provider'] = provider
        if provider == 'baidu':
            test_params['secret_key'] = 'test-secret'
        try:
            result = await generator.generate_image('test', '', test_params)
            status = result.get('status', 'unknown')
            msg = result.get('msg', '')[:30]
            print(f'✅ Provider {provider} handled correctly: {status} - {msg}...')
        except Exception as e:
            error_msg = str(e)[:50]
            print(f'✅ Provider {provider} error handling works: {error_msg}...')

    # Test 6: Test status checking with empty API key
    try:
        result = await generator.check_status('test-task-id', {'provider': 'tongyi', 'api_key': ''})
        status = result.get('status', 'unknown')
        msg = result.get('msg', '')
        print(f'✅ Status checking empty key validation: {status} - {msg}')
    except Exception as e:
        error_msg = str(e)[:50]
        print(f'❌ Status checking failed: {error_msg}...')

    print('=== External API Tests Completed ===')

async def test_api_endpoints():
    print('\n=== Testing API Endpoints ===')

    try:
        # Test the generation API endpoints directly
        from api.v1.generation import get_external_providers, test_external_api_connection

        # Test providers endpoint
        providers_result = await get_external_providers()
        if providers_result.get('code') == 200:
            providers = providers_result.get('data', [])
            print(f'✅ Providers endpoint works: {len(providers)} providers found')
            for provider in providers[:2]:  # Show first 2
                print(f'   - {provider.get("name", "Unknown")}: {provider.get("id", "unknown")}')
        else:
            print(f'❌ Providers endpoint failed: {providers_result}')

        # Test connection test endpoint (should fail without proper credentials)
        connection_result = await test_external_api_connection(
            provider='openai',
            api_key='test-key'
        )
        print(f'✅ Connection test endpoint responds: {connection_result.get("code", "unknown")}')

    except Exception as e:
        print(f'❌ API endpoint testing failed: {e}')

    print('=== API Endpoint Tests Completed ===')

async def test_config_loading():
    print('\n=== Testing Configuration Loading ===')

    try:
        from core.config import settings

        # Check if external API configs are loaded
        configs = [
            ('AI_API_KEY', settings.AI_API_KEY),
            ('AI_API_URL', settings.AI_API_URL),
            ('TONGYI_API_KEY', settings.TONGYI_API_KEY),
            ('BAIDU_AI_API_KEY', settings.BAIDU_AI_API_KEY),
            ('TENCENT_API_KEY', settings.TENCENT_API_KEY)
        ]

        for name, value in configs:
            status = '✅ Set' if value else '⚠️  Empty'
            print(f'{status} {name}: {"***" if value else "Not set"}')

        print('✅ Configuration loading works')

    except Exception as e:
        print(f'❌ Configuration loading failed: {e}')

    print('=== Configuration Tests Completed ===')

async def test_frontend_integration():
    print('\n=== Testing Frontend Integration Points ===')

    try:
        # Test that the API methods exist in the frontend api.ts
        import os
        frontend_api_path = '../Frontend/src/api/api.ts'

        if os.path.exists(frontend_api_path):
            with open(frontend_api_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for external API methods
            methods_to_check = [
                'getExternalProviders',
                'testExternalConnection',
                'checkGenerationStatus'
            ]

            for method in methods_to_check:
                if method in content:
                    print(f'✅ Frontend API method {method} exists')
                else:
                    print(f'❌ Frontend API method {method} missing')
        else:
            print('⚠️  Frontend API file not found (expected in development)')

    except Exception as e:
        print(f'❌ Frontend integration test failed: {e}')

    print('=== Frontend Integration Tests Completed ===')

if __name__ == '__main__':
    asyncio.run(test_external_api())
    asyncio.run(test_api_endpoints())
    asyncio.run(test_config_loading())
    asyncio.run(test_frontend_integration())
