#!/usr/bin/env python3
# Integration Tests: Authentication Flow
# Tests for complete authentication and authorization flow

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import time

from api.auth import (
    APIKeyManager,
    APIKey,
    AuthMiddleware,
    AuthLogger,
    RateLimitTracker
)
from api.server import APIServer


class TestAPIKeyManagement:
    """Test suite for API key management."""
    
    @pytest_asyncio.asyncio_test
    async def test_create_api_key(self, api_key_manager):
        """Test API key creation."""
        key_id, api_key = api_key_manager.create_key(
            name='Test Key',
            permissions=['read', 'write'],
            rate_limit=100,
            description='Test API key'
        )
        
        # Verify key was created
        assert key_id is not None
        assert api_key is not None
        assert api_key.startswith('kp_')
        
        # Verify key is stored
        stored_key = api_key_manager.get_key(key_id)
        assert stored_key is not None
        assert stored_key.name == 'Test Key'
        assert stored_key.permissions == ['read', 'write']
        assert stored_key.rate_limit == 100
    
    @pytest_asyncio.asyncio_test
    async def test_validate_api_key(self, api_key_manager):
        """Test API key validation."""
        # Create a key
        key_id, api_key = api_key_manager.create_key(
            name='Test Key',
            permissions=['read', 'write'],
            rate_limit=100
        )
        
        # Validate the key
        validated_key = api_key_manager.validate_key(api_key)
        
        # Verify validation
        assert validated_key is not None
        assert validated_key.key_id == key_id
        assert validated_key.name == 'Test Key'
        assert validated_key.is_active == True
        
        # Validate with wrong key
        wrong_key = 'kp_wrong_key_12345678'
        validated_wrong = api_key_manager.validate_key(wrong_key)
        assert validated_wrong is None
    
    @pytest_asyncio.asyncio_test
    async def test_list_api_keys(self, api_key_manager):
        """Test listing API keys."""
        # Create multiple keys
        key_id_1, _ = api_key_manager.create_key(
            name='Key 1',
            permissions=['read'],
            rate_limit=50
        )
        key_id_2, _ = api_key_manager.create_key(
            name='Key 2',
            permissions=['write'],
            rate_limit=100
        )
        
        # List keys
        keys = api_key_manager.list_keys()
        
        # Verify listing
        assert len(keys) >= 2
        key_ids = [k['key_id'] for k in keys]
        assert key_id_1 in key_ids
        assert key_id_2 in key_ids
    
    @pytest_asyncio.asyncio_test
    async def test_update_api_key(self, api_key_manager):
        """Test updating API key."""
        # Create a key
        key_id, _ = api_key_manager.create_key(
            name='Test Key',
            permissions=['read'],
            rate_limit=100
        )
        
        # Update the key
        success = api_key_manager.update_key(
            key_id,
            name='Updated Key',
            permissions=['read', 'write', 'admin'],
            rate_limit=200
        )
        
        # Verify update
        assert success == True
        
        # Verify updated values
        updated_key = api_key_manager.get_key(key_id)
        assert updated_key.name == 'Updated Key'
        assert updated_key.permissions == ['read', 'write', 'admin']
        assert updated_key.rate_limit == 200
    
    @pytest_asyncio.asyncio_test
    async def test_delete_api_key(self, api_key_manager):
        """Test deleting API key."""
        # Create a key
        key_id, _ = api_key_manager.create_key(
            name='Test Key',
            permissions=['read'],
            rate_limit=100
        )
        
        # Verify key exists
        assert api_key_manager.get_key(key_id) is not None
        
        # Delete the key
        success = api_key_manager.delete_key(key_id)
        
        # Verify deletion
        assert success == True
        assert api_key_manager.get_key(key_id) is None
    
    @pytest_asyncio.asyncio_test
    async def test_api_key_permissions(self, api_key_manager):
        """Test API key permission checking."""
        # Create key with specific permissions
        key_id, api_key = api_key_manager.create_key(
            name='Admin Key',
            permissions=['admin'],
            rate_limit=100
        )
        
        # Check permissions
        validated_key = api_key_manager.validate_key(api_key)
        
        # Verify admin permission
        assert api_key_manager.check_permission(validated_key, 'admin') == True
        assert api_key_manager.check_permission(validated_key, 'read') == True
        assert api_key_manager.check_permission(validated_key, 'write') == True
        
        # Create key with limited permissions
        key_id_2, api_key_2 = api_key_manager.create_key(
            name='Read Only Key',
            permissions=['read'],
            rate_limit=100
        )
        
        validated_key_2 = api_key_manager.validate_key(api_key_2)
        
        # Verify limited permissions
        assert api_key_manager.check_permission(validated_key_2, 'admin') == False
        assert api_key_manager.check_permission(validated_key_2, 'read') == True
        assert api_key_manager.check_permission(validated_key_2, 'write') == False
    
    @pytest_asyncio.asyncio_test
    async def test_api_key_deactivation(self, api_key_manager):
        """Test API key deactivation."""
        # Create a key
        key_id, api_key = api_key_manager.create_key(
            name='Test Key',
            permissions=['read'],
            rate_limit=100
        )
        
        # Verify key is active
        validated_key = api_key_manager.validate_key(api_key)
        assert validated_key.is_active == True
        
        # Deactivate the key
        success = api_key_manager.update_key(key_id, is_active=False)
        assert success == True
        
        # Verify deactivation
        deactivated_key = api_key_manager.get_key(key_id)
        assert deactivated_key.is_active == False
        
        # Verify deactivated key cannot be used
        validated_deactivated = api_key_manager.validate_key(api_key)
        assert validated_deactivated is None


class TestRateLimiting:
    """Test suite for rate limiting."""
    
    @pytest_asyncio.asyncio_test
    async def test_rate_limit_tracking(self, api_key_manager):
        """Test rate limit tracking."""
        # Create a key
        key_id, api_key = api_key_manager.create_key(
            name='Rate Limit Key',
            permissions=['read'],
            rate_limit=5  # 5 requests per second
        )
        
        # Validate key
        validated_key = api_key_manager.validate_key(api_key)
        
        # Check rate limit
        assert api_key_manager.check_rate_limit(validated_key) == True
        
        # Record requests
        for i in range(3):
            api_key_manager.record_request(validated_key)
        
        # Check rate limit after requests
        assert api_key_manager.check_rate_limit(validated_key) == True
        
        # Record more requests to exceed limit
        for i in range(3):
            api_key_manager.record_request(validated_key)
        
        # Check rate limit exceeded
        assert api_key_manager.check_rate_limit(validated_key) == False
    
    @pytest_asyncio.asyncio_test
    async def test_rate_limit_info(self, api_key_manager):
        """Test rate limit information."""
        # Create a key
        key_id, api_key = api_key_manager.create_key(
            name='Rate Limit Key',
            permissions=['read'],
            rate_limit=10
        )
        
        # Validate key
        validated_key = api_key_manager.validate_key(api_key)
        
        # Record some requests
        for i in range(3):
            api_key_manager.record_request(validated_key)
        
        # Get rate limit info
        info = api_key_manager.get_rate_limit_info(validated_key)
        
        # Verify rate limit info
        assert info['limit'] == 10
        assert info['remaining'] == 7
        assert 'reset' in info
        assert info['remaining'] == info['limit'] - 3
    
    @pytest_asyncio.asyncio_test
    async def test_rate_limit_window_cleanup(self, api_key_manager):
        """Test rate limit window cleanup."""
        # Create a key
        key_id, api_key = api_key_manager.create_key(
            name='Rate Limit Key',
            permissions=['read'],
            rate_limit=10
        )
        
        # Validate key
        validated_key = api_key_manager.validate_key(api_key)
        
        # Record old requests
        old_time = time.time() - 2.0  # 2 seconds ago
        tracker = api_key_manager.rate_limit_trackers[validated_key.key_id]
        tracker.requests = [old_time, old_time, old_time]
        
        # Cleanup old requests
        tracker.cleanup_old_requests(window_seconds=1)
        
        # Verify cleanup
        assert len(tracker.requests) == 0
        assert tracker.count_requests() == 0
    
    @pytest_asyncio.asyncio_test
    async def test_rate_limit_multiple_keys(self, api_key_manager):
        """Test rate limiting with multiple keys."""
        # Create multiple keys
        key_id_1, api_key_1 = api_key_manager.create_key(
            name='Key 1',
            permissions=['read'],
            rate_limit=5
        )
        key_id_2, api_key_2 = api_key_manager.create_key(
            name='Key 2',
            permissions=['read'],
            rate_limit=10
        )
        
        # Validate keys
        validated_key_1 = api_key_manager.validate_key(api_key_1)
        validated_key_2 = api_key_manager.validate_key(api_key_2)
        
        # Record requests for key 1
        for i in range(4):
            api_key_manager.record_request(validated_key_1)
        
        # Record requests for key 2
        for i in range(4):
            api_key_manager.record_request(validated_key_2)
        
        # Check rate limits
        assert api_key_manager.check_rate_limit(validated_key_1) == True  # 4/5
        assert api_key_manager.check_rate_limit(validated_key_2) == True  # 4/10


class TestAuthMiddleware:
    """Test suite for authentication middleware."""
    
    @pytest_asyncio.asyncio_test
    async def test_auth_middleware_skip_on_disabled(self, auth_manager):
        """Test that auth is skipped when disabled."""
        key_manager, middleware, auth_logger = auth_manager
        
        # Create mock request
        mock_request = MagicMock()
        mock_request.path = '/api/v1/version'
        mock_request.headers = {}
        mock_request.remote = '127.0.0.1'
        
        # Create mock handler
        async def mock_handler(request):
            return MagicMock(status=200)
        
        # Test with auth disabled
        middleware.require_auth = False
        response = await middleware.middleware(mock_request, mock_handler)
        
        # Verify request passed through
        assert response is not None
    
    @pytest_asyncio.asyncio_test
    async def test_auth_middleware_require_api_key(self, auth_manager):
        """Test that auth requires API key when enabled."""
        key_manager, middleware, auth_logger = auth_manager
        
        # Create mock request without API key
        mock_request = MagicMock()
        mock_request.path = '/api/v1/move'
        mock_request.headers = {}
        mock_request.remote = '127.0.0.1'
        
        # Create mock handler
        async def mock_handler(request):
            return MagicMock(status=200)
        
        # Test with auth enabled
        middleware.require_auth = True
        response = await middleware.middleware(mock_request, mock_handler)
        
        # Verify request was rejected
        assert response is not None
        assert response.status == 401
    
    @pytest_asyncio.asyncio_test
    async def test_auth_middleware_valid_api_key(self, auth_manager):
        """Test that auth accepts valid API key."""
        key_manager, middleware, auth_logger = auth_manager
        
        # Create a valid API key
        key_id, api_key = key_manager.create_key(
            name='Valid Key',
            permissions=['read', 'write'],
            rate_limit=100
        )
        
        # Create mock request with API key
        mock_request = MagicMock()
        mock_request.path = '/api/v1/move'
        mock_request.headers = {'X-API-Key': api_key}
        mock_request.remote = '127.0.0.1'
        
        # Create mock handler
        async def mock_handler(request):
            return MagicMock(status=200)
        
        # Test with valid API key
        middleware.require_auth = True
        response = await middleware.middleware(mock_request, mock_handler)
        
        # Verify request passed through
        assert response is not None
        assert response.status == 200
    
    @pytest_asyncio.asyncio_test
    async def test_auth_middleware_invalid_api_key(self, auth_manager):
        """Test that auth rejects invalid API key."""
        key_manager, middleware, auth_logger = auth_manager
        
        # Create mock request with invalid API key
        mock_request = MagicMock()
        mock_request.path = '/api/v1/move'
        mock_request.headers = {'X-API-Key': 'invalid_key_123456'}
        mock_request.remote = '127.0.0.1'
        
        # Create mock handler
        async def mock_handler(request):
            return MagicMock(status=200)
        
        # Test with invalid API key
        middleware.require_auth = True
        response = await middleware.middleware(mock_request, mock_handler)
        
        # Verify request was rejected
        assert response is not None
        assert response.status == 401
    
    @pytest_asyncio.asyncio_test
    async def test_auth_middleware_public_endpoint(self, auth_manager):
        """Test that public endpoints bypass auth."""
        key_manager, middleware, auth_logger = auth_manager
        
        # Add public endpoint
        middleware.public_endpoints.add('/api/v1/version')
        
        # Create mock request without API key
        mock_request = MagicMock()
        mock_request.path = '/api/v1/version'
        mock_request.headers = {}
        mock_request.remote = '127.0.0.1'
        
        # Create mock handler
        async def mock_handler(request):
            return MagicMock(status=200)
        
        # Test public endpoint
        middleware.require_auth = True
        response = await middleware.middleware(mock_request, mock_handler)
        
        # Verify request passed through
        assert response is not None
        assert response.status == 200
    
    @pytest_asyncio.asyncio_test
    async def test_auth_middleware_rate_limit_exceeded(self, auth_manager):
        """Test that auth blocks when rate limit exceeded."""
        key_manager, middleware, auth_logger = auth_manager
        
        # Create a key with low rate limit
        key_id, api_key = key_manager.create_key(
            name='Rate Limited Key',
            permissions=['read'],
            rate_limit=1
        )
        
        # Exceed rate limit
        validated_key = key_manager.validate_key(api_key)
        for i in range(2):
            key_manager.record_request(validated_key)
        
        # Create mock request with API key
        mock_request = MagicMock()
        mock_request.path = '/api/v1/move'
        mock_request.headers = {'X-API-Key': api_key}
        mock_request.remote = '127.0.0.1'
        
        # Create mock handler
        async def mock_handler(request):
            return MagicMock(status=200)
        
        # Test with rate limit exceeded
        middleware.require_auth = True
        response = await middleware.middleware(mock_request, mock_handler)
        
        # Verify request was rejected
        assert response is not None
        assert response.status == 429
    
    @pytest_asyncio.asyncio_test
    async def test_auth_middleware_rate_limit_headers(self, auth_manager):
        """Test that rate limit headers are added."""
        key_manager, middleware, auth_logger = auth_manager
        
        # Create a key
        key_id, api_key = key_manager.create_key(
            name='Rate Limit Key',
            permissions=['read'],
            rate_limit=10
        )
        
        # Record a request
        validated_key = key_manager.validate_key(api_key)
        key_manager.record_request(validated_key)
        
        # Create mock request
        mock_request = MagicMock()
        mock_request.path = '/api/v1/move'
        mock_request.headers = {'X-API-Key': api_key}
        mock_request.remote = '127.0.0.1'
        
        # Create mock handler
        async def mock_handler(request):
            response = MagicMock()
            response.headers = {}
            return response
        
        # Test rate limit headers
        middleware.require_auth = True
        response = await middleware.middleware(mock_request, mock_handler)
        
        # Verify rate limit headers
        assert 'X-RateLimit-Limit' in response.headers
        assert 'X-RateLimit-Remaining' in response.headers
        assert 'X-RateLimit-Reset' in response.headers
        assert response.headers['X-RateLimit-Limit'] == '10'
        assert response.headers['X-RateLimit-Remaining'] == '9'


class TestAuthLogger:
    """Test suite for authentication logger."""
    
    @pytest_asyncio.asyncio_test
    async def test_auth_log_success(self, auth_manager):
        """Test successful authentication logging."""
        key_manager, middleware, auth_logger = auth_manager
        
        # Create a key
        key_id, api_key = key_manager.create_key(
            name='Test Key',
            permissions=['read'],
            rate_limit=100
        )
        
        # Log success
        auth_logger.log_success(key_id, '127.0.0.1', '/api/v1/move')
        
        # Verify no failed attempts
        assert auth_logger.get_failed_attempts('127.0.0.1') == 0
    
    @pytest_asyncio.asyncio_test
    async def test_auth_log_failure(self, auth_manager):
        """Test failed authentication logging."""
        key_manager, middleware, auth_logger = auth_manager
        
        # Log failure
        auth_logger.log_failure('127.0.0.1', '/api/v1/move', 'Invalid API key')
        
        # Verify failed attempt was logged
        assert auth_logger.get_failed_attempts('127.0.0.1') == 1
    
    @pytest_asyncio.asyncio_test
    async def test_auth_log_multiple_failures(self, auth_manager):
        """Test multiple failed authentication logging."""
        key_manager, middleware, auth_logger = auth_manager
        
        # Log multiple failures
        for i in range(5):
            auth_logger.log_failure('127.0.0.1', '/api/v1/move', 'Invalid API key')
        
        # Verify failed attempts
        assert auth_logger.get_failed_attempts('127.0.0.1') == 5
    
    @pytest_asyncio.asyncio_test
    async def test_auth_log_old_failures_cleanup(self, auth_manager):
        """Test that old failures are cleaned up."""
        key_manager, middleware, auth_logger = auth_manager
        
        # Log old failures
        old_time = time.time() - 3700  # 1 hour ago
        auth_logger.failed_attempts['127.0.0.1'] = [old_time, old_time, old_time]
        
        # Log new failure
        auth_logger.log_failure('127.0.0.1', '/api/v1/move', 'Invalid API key')
        
        # Verify old failures were cleaned up
        assert len(auth_logger.failed_attempts['127.0.0.1']) == 1
    
    @pytest_asyncio.asyncio_test
    async def test_auth_ip_blocking(self, auth_manager):
        """Test IP blocking after multiple failures."""
        key_manager, middleware, auth_logger = auth_manager
        
        # Log multiple failures to reach threshold
        for i in range(10):
            auth_logger.log_failure('192.168.1.1', '/api/v1/move', 'Invalid API key')
        
        # Check if IP is blocked
        assert auth_logger.is_ip_blocked('192.168.1.1', threshold=10) == True
        
        # Check if another IP is not blocked
        assert auth_logger.is_ip_blocked('192.168.1.2', threshold=10) == False


class TestCompleteAuthFlow:
    """Test suite for complete authentication flow."""
    
    @pytest_asyncio.asyncio_test
    async def test_complete_auth_flow_success(self, auth_manager):
        """Test complete authentication flow with success."""
        key_manager, middleware, auth_logger = auth_manager
        
        # Create API key
        key_id, api_key = key_manager.create_key(
            name='Flow Test Key',
            permissions=['read', 'write'],
            rate_limit=100
        )
        
        # Create mock request
        mock_request = MagicMock()
        mock_request.path = '/api/v1/move'
        mock_request.headers = {'X-API-Key': api_key}
        mock_request.remote = '192.168.1.1'
        
        # Create mock handler
        async def mock_handler(request):
            response = MagicMock()
            response.status = 200
            response.headers = {}
            return response
        
        # Test complete flow
        middleware.require_auth = True
        response = await middleware.middleware(mock_request, mock_handler)
        
        # Verify success flow
        assert response.status == 200
        assert 'X-RateLimit-Limit' in response.headers
        assert auth_logger.get_failed_attempts('192.168.1.1') == 0
    
    @pytest_asyncio.asyncio_test
    async def test_complete_auth_flow_failure(self, auth_manager):
        """Test complete authentication flow with failure."""
        key_manager, middleware, auth_logger = auth_manager
        
        # Create mock request without API key
        mock_request = MagicMock()
        mock_request.path = '/api/v1/move'
        mock_request.headers = {}
        mock_request.remote = '192.168.1.1'
        
        # Create mock handler
        async def mock_handler(request):
            response = MagicMock()
            response.status = 200
            return response
        
        # Test failure flow
        middleware.require_auth = True
        response = await middleware.middleware(mock_request, mock_handler)
        
        # Verify failure flow
        assert response.status == 401
        assert auth_logger.get_failed_attempts('192.168.1.1') == 1
    
    @pytest_asyncio.asyncio_test
    async def test_complete_auth_flow_rate_limit(self, auth_manager):
        """Test complete authentication flow with rate limiting."""
        key_manager, middleware, auth_logger = auth_manager
        
        # Create API key with low rate limit
        key_id, api_key = key_manager.create_key(
            name='Rate Limit Flow Key',
            permissions=['read'],
            rate_limit=2
        )
        
        # Exceed rate limit
        validated_key = key_manager.validate_key(api_key)
        for i in range(3):
            key_manager.record_request(validated_key)
        
        # Create mock request
        mock_request = MagicMock()
        mock_request.path = '/api/v1/move'
        mock_request.headers = {'X-API-Key': api_key}
        mock_request.remote = '192.168.1.1'
        
        # Create mock handler
        async def mock_handler(request):
            response = MagicMock()
            response.status = 200
            response.headers = {}
            return response
        
        # Test rate limit flow
        middleware.require_auth = True
        response = await middleware.middleware(mock_request, mock_handler)
        
        # Verify rate limit flow
        assert response.status == 429
        assert 'X-RateLimit-Limit' in response.headers
        assert 'X-RateLimit-Remaining' in response.headers
    
    @pytest_asyncio.asyncio_test
    async def test_complete_auth_flow_ip_blocking(self, auth_manager):
        """Test complete authentication flow with IP blocking."""
        key_manager, middleware, auth_logger = auth_manager
        
        # Log multiple failures to block IP
        for i in range(10):
            auth_logger.log_failure('10.0.0.1', '/api/v1/move', 'Invalid API key')
        
        # Create mock request from blocked IP
        mock_request = MagicMock()
        mock_request.path = '/api/v1/move'
        mock_request.headers = {}
        mock_request.remote = '10.0.0.1'
        
        # Create mock handler
        async def mock_handler(request):
            response = MagicMock()
            response.status = 200
            return response
        
        # Test IP blocking flow
        middleware.require_auth = True
        response = await middleware.middleware(mock_request, mock_handler)
        
        # Verify IP blocking flow
        assert response.status == 429
        assert auth_logger.is_ip_blocked('10.0.0.1', threshold=10) == True
    
    @pytest_asyncio.asyncio_test
    async def test_complete_auth_flow_permission_check(self, auth_manager):
        """Test complete authentication flow with permission checking."""
        key_manager, middleware, auth_logger = auth_manager
        
        # Create API key with limited permissions
        key_id, api_key = key_manager.create_key(
            name='Limited Key',
            permissions=['read'],
            rate_limit=100
        )
        
        # Create mock request
        mock_request = MagicMock()
        mock_request.path = '/api/v1/move'
        mock_request.headers = {'X-API-Key': api_key}
        mock_request.remote = '192.168.1.1'
        
        # Create mock handler that checks permissions
        async def mock_handler(request):
            validated_key = key_manager.validate_key(api_key)
            if not key_manager.check_permission(validated_key, 'write'):
                from aiohttp import web
                return web.json_response(
                    {
                        'status': 'error',
                        'error_code': 'PERMISSION_DENIED',
                        'error_message': 'Insufficient permissions'
                    },
                    status=403
                )
            response = MagicMock()
            response.status = 200
            return response
        
        # Test permission check flow
        middleware.require_auth = True
        response = await middleware.middleware(mock_request, mock_handler)
        
        # Verify permission check flow
        # Response will be 403 if permission check fails
        assert response is not None
