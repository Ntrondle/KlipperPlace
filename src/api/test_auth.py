#!/usr/bin/env python3
# Authentication Module Test Script
# Test authentication/authorization functionality

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth import (
    APIKeyManager,
    AuthLogger,
    AuthMiddleware,
    create_auth_manager
)


async def test_api_key_manager():
    """Test API key manager functionality."""
    print("\n=== Testing API Key Manager ===\n")
    
    # Create a temporary manager (no storage)
    manager = APIKeyManager(storage_path=None)
    
    # Test creating API keys
    print("1. Creating API keys...")
    key_id_1, api_key_1 = manager.create_key(
        name="Test Key 1",
        permissions=["read", "write"],
        rate_limit=100,
        description="Test key for read/write operations"
    )
    print(f"   Created key: {key_id_1}")
    print(f"   API Key: {api_key_1}")
    
    key_id_2, api_key_2 = manager.create_key(
        name="Admin Key",
        permissions=["read", "write", "admin"],
        rate_limit=200,
        description="Admin key with full permissions"
    )
    print(f"   Created key: {key_id_2}")
    print(f"   API Key: {api_key_2}")
    
    # Test listing keys
    print("\n2. Listing API keys...")
    keys = manager.list_keys()
    print(f"   Total keys: {len(keys)}")
    for key in keys:
        print(f"   - {key['key_id']}: {key['name']} ({len(key['permissions'])} permissions)")
    
    # Test validating keys
    print("\n3. Validating API keys...")
    validated_key = manager.validate_key(api_key_1)
    print(f"   Key 1 valid: {validated_key is not None}")
    if validated_key:
        print(f"   Key ID: {validated_key.key_id}")
        print(f"   Permissions: {validated_key.permissions}")
    
    # Test invalid key
    invalid_key = manager.validate_key("invalid_key_12345")
    print(f"   Invalid key valid: {invalid_key is not None}")
    
    # Test getting specific key
    print("\n4. Getting specific API key...")
    key = manager.get_key(key_id_1)
    print(f"   Retrieved key: {key is not None}")
    if key:
        print(f"   Name: {key.name}")
        print(f"   Rate limit: {key.rate_limit}")
    
    # Test updating key
    print("\n5. Updating API key...")
    success = manager.update_key(
        key_id_1,
        name="Updated Test Key",
        rate_limit=150
    )
    print(f"   Update successful: {success}")
    
    # Verify update
    updated_key = manager.get_key(key_id_1)
    print(f"   New name: {updated_key.name}")
    print(f"   New rate limit: {updated_key.rate_limit}")
    
    # Test rate limiting
    print("\n6. Testing rate limiting...")
    api_key = manager.validate_key(api_key_1)
    
    # Check initial rate limit
    rate_info = manager.get_rate_limit_info(api_key)
    print(f"   Initial - Limit: {rate_info['limit']}, Remaining: {rate_info['remaining']}")
    
    # Record some requests
    for i in range(5):
        manager.record_request(api_key)
    
    rate_info = manager.get_rate_limit_info(api_key)
    print(f"   After 5 requests - Remaining: {rate_info['remaining']}")
    
    # Check if within limit
    within_limit = manager.check_rate_limit(api_key)
    print(f"   Within limit: {within_limit}")
    
    # Test permission checking
    print("\n7. Testing permission checking...")
    has_read = manager.check_permission(api_key, "read")
    has_admin = manager.check_permission(api_key, "admin")
    has_write = manager.check_permission(api_key, "write")
    
    print(f"   Has 'read' permission: {has_read}")
    print(f"   Has 'write' permission: {has_write}")
    print(f"   Has 'admin' permission: {has_admin}")
    
    # Test deactivating key
    print("\n8. Deactivating API key...")
    success = manager.update_key(key_id_1, is_active=False)
    print(f"   Deactivation successful: {success}")
    
    # Validate deactivated key
    validated = manager.validate_key(api_key_1)
    print(f"   Deactivated key valid: {validated is None}")
    
    # Test deleting key
    print("\n9. Deleting API key...")
    success = manager.delete_key(key_id_1)
    print(f"   Deletion successful: {success}")
    
    # Verify deletion
    key = manager.get_key(key_id_1)
    print(f"   Key exists after deletion: {key is not None}")
    
    print("\n✓ API Key Manager tests completed successfully!")


async def test_auth_logger():
    """Test auth logger functionality."""
    print("\n=== Testing Auth Logger ===\n")
    
    logger = AuthLogger()
    
    # Test logging success
    print("1. Logging successful authentication...")
    logger.log_success("key_123", "192.168.1.100", "/api/v1/status")
    
    # Test logging failure
    print("2. Logging failed authentication...")
    logger.log_failure("192.168.1.100", "/api/v1/status", "Invalid API key")
    
    # Test failed attempts tracking
    print("\n3. Testing failed attempts tracking...")
    for i in range(5):
        logger.log_failure("192.168.1.100", "/api/v1/status", f"Failed attempt {i+1}")
    
    attempts = logger.get_failed_attempts("192.168.1.100")
    print(f"   Failed attempts from IP: {attempts}")
    
    # Test IP blocking
    print("\n4. Testing IP blocking (threshold=10)...")
    is_blocked = logger.is_ip_blocked("192.168.1.100", threshold=10)
    print(f"   IP blocked (5 attempts): {is_blocked}")
    
    # Add more attempts
    for i in range(5):
        logger.log_failure("192.168.1.100", "/api/v1/status", f"Failed attempt {i+6}")
    
    is_blocked = logger.is_ip_blocked("192.168.1.100", threshold=10)
    print(f"   IP blocked (10 attempts): {is_blocked}")
    
    print("\n✓ Auth Logger tests completed successfully!")


async def test_create_auth_manager():
    """Test auth manager factory function."""
    print("\n=== Testing Auth Manager Factory ===\n")
    
    # Test with config
    config = {
        'api_key_enabled': True,
        'api_key': 'test_legacy_key',
        'rate_limit': 100,
        'api_key_storage_path': None
    }
    
    print("1. Creating auth manager with config...")
    key_manager, auth_middleware, auth_logger = create_auth_manager(config)
    
    print(f"   Key manager created: {key_manager is not None}")
    print(f"   Auth middleware created: {auth_middleware is not None}")
    print(f"   Auth logger created: {auth_logger is not None}")
    
    # Check if default key was created
    print("\n2. Checking for default API key...")
    keys = key_manager.list_keys()
    print(f"   Number of keys: {len(keys)}")
    if keys:
        print(f"   Default key created: {keys[0]['name']}")
    
    print("\n✓ Auth Manager factory tests completed successfully!")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("KlipperPlace Authentication Module Tests")
    print("=" * 60)
    
    try:
        await test_api_key_manager()
        await test_auth_logger()
        await test_create_auth_manager()
        
        print("\n" + "=" * 60)
        print("All tests completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
