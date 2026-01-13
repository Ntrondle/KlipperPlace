#!/usr/bin/env python3
# Authentication and Authorization Module
# API key management, authentication middleware, and rate limiting

import logging
import secrets
import time
import hashlib
from typing import Optional, Dict, List, Set, Any
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime, timedelta
from aiohttp import web
import json
import os

logger = logging.getLogger(__name__)


@dataclass
class APIKey:
    """API key data structure."""
    key_id: str
    key_hash: str
    name: str
    permissions: List[str]
    rate_limit: int
    created_at: float
    last_used: float = 0.0
    is_active: bool = True
    description: str = ""
    
    def to_dict(self, include_hash: bool = False) -> Dict[str, Any]:
        """Convert to dictionary for API responses.
        
        Args:
            include_hash: Whether to include the key hash (for internal use only)
            
        Returns:
            Dictionary representation
        """
        data = {
            'key_id': self.key_id,
            'name': self.name,
            'permissions': self.permissions,
            'rate_limit': self.rate_limit,
            'created_at': self.created_at,
            'last_used': self.last_used,
            'is_active': self.is_active,
            'description': self.description
        }
        if include_hash:
            data['key_hash'] = self.key_hash
        return data


@dataclass
class RateLimitTracker:
    """Track rate limit usage for an API key."""
    requests: List[float] = field(default_factory=list)
    
    def cleanup_old_requests(self, window_seconds: int = 1) -> None:
        """Remove requests outside the time window.
        
        Args:
            window_seconds: Time window in seconds
        """
        cutoff = time.time() - window_seconds
        self.requests = [r for r in self.requests if r > cutoff]
    
    def count_requests(self) -> int:
        """Count requests in the current window.
        
        Returns:
            Number of requests in the window
        """
        self.cleanup_old_requests()
        return len(self.requests)
    
    def add_request(self) -> None:
        """Add a request to the tracker."""
        self.requests.append(time.time())


class APIKeyManager:
    """Manage API keys with permissions and rate limiting."""
    
    def __init__(self, storage_path: Optional[str] = None):
        """Initialize API key manager.
        
        Args:
            storage_path: Optional path to persist API keys to disk
        """
        self.api_keys: Dict[str, APIKey] = {}
        self.rate_limit_trackers: Dict[str, RateLimitTracker] = defaultdict(RateLimitTracker)
        self.storage_path = storage_path
        self._load_keys()
    
    def _hash_key(self, key: str) -> str:
        """Hash an API key for storage.
        
        Args:
            key: API key to hash
            
        Returns:
            Hashed key
        """
        return hashlib.sha256(key.encode()).hexdigest()
    
    def _generate_key_id(self) -> str:
        """Generate a unique key ID.
        
        Returns:
            Unique key ID
        """
        return secrets.token_hex(16)
    
    def _generate_api_key(self) -> str:
        """Generate a secure API key.
        
        Returns:
            Generated API key
        """
        return f"kp_{secrets.token_urlsafe(32)}"
    
    def _load_keys(self) -> None:
        """Load API keys from storage if available."""
        if self.storage_path and os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    for key_data in data.get('api_keys', []):
                        api_key = APIKey(**key_data)
                        self.api_keys[api_key.key_id] = api_key
                logger.info(f"Loaded {len(self.api_keys)} API keys from storage")
            except Exception as e:
                logger.error(f"Failed to load API keys: {e}")
    
    def _save_keys(self) -> None:
        """Save API keys to storage if configured."""
        if self.storage_path:
            try:
                data = {
                    'api_keys': [
                        key.to_dict(include_hash=True)
                        for key in self.api_keys.values()
                    ]
                }
                with open(self.storage_path, 'w') as f:
                    json.dump(data, f, indent=2)
                logger.debug("API keys saved to storage")
            except Exception as e:
                logger.error(f"Failed to save API keys: {e}")
    
    def create_key(self, name: str, permissions: List[str], 
                  rate_limit: int = 100, description: str = "") -> tuple[str, str]:
        """Create a new API key.
        
        Args:
            name: Human-readable name for the key
            permissions: List of permissions (e.g., ['read', 'write', 'admin'])
            rate_limit: Rate limit (requests per second)
            description: Optional description
            
        Returns:
            Tuple of (key_id, api_key)
        """
        key_id = self._generate_key_id()
        api_key = self._generate_api_key()
        key_hash = self._hash_key(api_key)
        
        new_key = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            name=name,
            permissions=permissions,
            rate_limit=rate_limit,
            created_at=time.time(),
            description=description
        )
        
        self.api_keys[key_id] = new_key
        self._save_keys()
        
        logger.info(f"Created API key: {key_id} ({name})")
        return key_id, api_key
    
    def validate_key(self, api_key: str) -> Optional[APIKey]:
        """Validate an API key.
        
        Args:
            api_key: API key to validate
            
        Returns:
            APIKey object if valid, None otherwise
        """
        key_hash = self._hash_key(api_key)
        
        for key in self.api_keys.values():
            if key.key_hash == key_hash and key.is_active:
                key.last_used = time.time()
                self._save_keys()
                return key
        
        return None
    
    def get_key(self, key_id: str) -> Optional[APIKey]:
        """Get an API key by ID.
        
        Args:
            key_id: Key ID to retrieve
            
        Returns:
            APIKey object if found, None otherwise
        """
        return self.api_keys.get(key_id)
    
    def list_keys(self) -> List[Dict[str, Any]]:
        """List all API keys.
        
        Returns:
            List of API key dictionaries (without hashes)
        """
        return [key.to_dict() for key in self.api_keys.values()]
    
    def update_key(self, key_id: str, **kwargs) -> bool:
        """Update an API key.
        
        Args:
            key_id: Key ID to update
            **kwargs: Fields to update (name, permissions, rate_limit, description, is_active)
            
        Returns:
            True if updated, False if not found
        """
        key = self.api_keys.get(key_id)
        if not key:
            return False
        
        for field, value in kwargs.items():
            if hasattr(key, field):
                setattr(key, field, value)
        
        self._save_keys()
        logger.info(f"Updated API key: {key_id}")
        return True
    
    def delete_key(self, key_id: str) -> bool:
        """Delete an API key.
        
        Args:
            key_id: Key ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        if key_id in self.api_keys:
            del self.api_keys[key_id]
            self._save_keys()
            logger.info(f"Deleted API key: {key_id}")
            return True
        return False
    
    def check_rate_limit(self, api_key: APIKey) -> bool:
        """Check if API key is within rate limits.
        
        Args:
            api_key: API key to check
            
        Returns:
            True if within limits, False otherwise
        """
        tracker = self.rate_limit_trackers[api_key.key_id]
        return tracker.count_requests() < api_key.rate_limit
    
    def record_request(self, api_key: APIKey) -> None:
        """Record a request for rate limiting.
        
        Args:
            api_key: API key making the request
        """
        tracker = self.rate_limit_trackers[api_key.key_id]
        tracker.add_request()
    
    def check_permission(self, api_key: APIKey, required_permission: str) -> bool:
        """Check if API key has required permission.
        
        Args:
            api_key: API key to check
            required_permission: Required permission
            
        Returns:
            True if has permission, False otherwise
        """
        return 'admin' in api_key.permissions or required_permission in api_key.permissions
    
    def get_rate_limit_info(self, api_key: APIKey) -> Dict[str, int]:
        """Get rate limit information for an API key.
        
        Args:
            api_key: API key to check
            
        Returns:
            Dictionary with limit, remaining, and reset time
        """
        tracker = self.rate_limit_trackers[api_key.key_id]
        used = tracker.count_requests()
        remaining = max(0, api_key.rate_limit - used)
        
        # Calculate reset time (1 second window)
        if tracker.requests:
            oldest_request = min(tracker.requests)
            reset_time = int(oldest_request + 1)
        else:
            reset_time = int(time.time()) + 1
        
        return {
            'limit': api_key.rate_limit,
            'remaining': remaining,
            'reset': reset_time
        }


class AuthLogger:
    """Log authentication attempts."""
    
    def __init__(self):
        """Initialize auth logger."""
        self.failed_attempts: Dict[str, List[float]] = defaultdict(list)
    
    def log_success(self, key_id: str, ip: str, endpoint: str) -> None:
        """Log successful authentication.
        
        Args:
            key_id: API key ID
            ip: Client IP address
            endpoint: Requested endpoint
        """
        logger.info(f"Auth success: key_id={key_id}, ip={ip}, endpoint={endpoint}")
    
    def log_failure(self, ip: str, endpoint: str, reason: str) -> None:
        """Log failed authentication.
        
        Args:
            ip: Client IP address
            endpoint: Requested endpoint
            reason: Failure reason
        """
        logger.warning(f"Auth failure: ip={ip}, endpoint={endpoint}, reason={reason}")
        
        # Track failed attempts by IP
        self.failed_attempts[ip].append(time.time())
        
        # Clean up old attempts (older than 1 hour)
        cutoff = time.time() - 3600
        self.failed_attempts[ip] = [
            t for t in self.failed_attempts[ip] if t > cutoff
        ]
    
    def get_failed_attempts(self, ip: str) -> int:
        """Get number of failed attempts from an IP.
        
        Args:
            ip: IP address to check
            
        Returns:
            Number of failed attempts in the last hour
        """
        return len(self.failed_attempts.get(ip, []))
    
    def is_ip_blocked(self, ip: str, threshold: int = 10) -> bool:
        """Check if IP should be blocked due to too many failures.
        
        Args:
            ip: IP address to check
            threshold: Failure threshold
            
        Returns:
            True if IP should be blocked
        """
        return self.get_failed_attempts(ip) >= threshold


class AuthMiddleware:
    """Authentication middleware for aiohttp."""
    
    def __init__(self, 
                 key_manager: APIKeyManager,
                 auth_logger: AuthLogger,
                 require_auth: bool = True,
                 public_endpoints: Optional[Set[str]] = None):
        """Initialize authentication middleware.
        
        Args:
            key_manager: API key manager instance
            auth_logger: Auth logger instance
            require_auth: Whether authentication is required
            public_endpoints: Set of endpoints that don't require auth
        """
        self.key_manager = key_manager
        self.auth_logger = auth_logger
        self.require_auth = require_auth
        self.public_endpoints = public_endpoints or set()
    
    @web.middleware
    async def middleware(self, request: web.Request, handler):
        """Authentication middleware handler.
        
        Args:
            request: Incoming request
            handler: Next handler in chain
            
        Returns:
            Response from handler or auth error
        """
        # Skip auth if disabled
        if not self.require_auth:
            return await handler(request)
        
        # Check if endpoint is public
        path = request.path
        if any(path.startswith(ep) for ep in self.public_endpoints):
            return await handler(request)
        
        # Get API key from header
        provided_key = request.headers.get('X-API-Key')
        
        if not provided_key:
            self.auth_logger.log_failure(
                request.remote or 'unknown',
                path,
                'Missing API key'
            )
            return web.json_response(
                {
                    'status': 'error',
                    'error_code': 'AUTHORIZATION_REQUIRED',
                    'error_message': 'API key is required'
                },
                status=401
            )
        
        # Check if IP is blocked
        if self.auth_logger.is_ip_blocked(request.remote or 'unknown'):
            return web.json_response(
                {
                    'status': 'error',
                    'error_code': 'IP_BLOCKED',
                    'error_message': 'Too many failed authentication attempts'
                },
                status=429
            )
        
        # Validate API key
        api_key = self.key_manager.validate_key(provided_key)
        
        if not api_key:
            self.auth_logger.log_failure(
                request.remote or 'unknown',
                path,
                'Invalid API key'
            )
            return web.json_response(
                {
                    'status': 'error',
                    'error_code': 'INVALID_API_KEY',
                    'error_message': 'Invalid or inactive API key'
                },
                status=401
            )
        
        # Check rate limit
        if not self.key_manager.check_rate_limit(api_key):
            rate_info = self.key_manager.get_rate_limit_info(api_key)
            return web.json_response(
                {
                    'status': 'error',
                    'error_code': 'RATE_LIMIT_EXCEEDED',
                    'error_message': 'Rate limit exceeded',
                    'details': rate_info
                },
                status=429,
                headers={
                    'X-RateLimit-Limit': str(rate_info['limit']),
                    'X-RateLimit-Remaining': str(rate_info['remaining']),
                    'X-RateLimit-Reset': str(rate_info['reset']),
                    'X-RateLimit-Retry-After': '1'
                }
            )
        
        # Record request and add rate limit headers
        self.key_manager.record_request(api_key)
        rate_info = self.key_manager.get_rate_limit_info(api_key)
        
        # Store API key in request for use by handlers
        request['api_key'] = api_key
        
        # Log successful authentication
        self.auth_logger.log_success(
            api_key.key_id,
            request.remote or 'unknown',
            path
        )
        
        # Call handler and add rate limit headers to response
        response = await handler(request)
        response.headers['X-RateLimit-Limit'] = str(rate_info['limit'])
        response.headers['X-RateLimit-Remaining'] = str(rate_info['remaining'])
        response.headers['X-RateLimit-Reset'] = str(rate_info['reset'])
        
        return response


def create_auth_manager(config: Optional[Dict[str, Any]] = None) -> tuple[APIKeyManager, AuthMiddleware, AuthLogger]:
    """Factory function to create authentication components.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Tuple of (APIKeyManager, AuthMiddleware, AuthLogger)
    """
    if config is None:
        config = {}
    
    # Initialize components
    storage_path = config.get('api_key_storage_path')
    key_manager = APIKeyManager(storage_path=storage_path)
    auth_logger = AuthLogger()
    
    # Create default API key if none exist
    if not key_manager.api_keys and config.get('api_key'):
        key_id, api_key = key_manager.create_key(
            name='Default Key',
            permissions=['read', 'write', 'admin'],
            rate_limit=config.get('rate_limit', 100),
            description='Default API key from configuration'
        )
        logger.info(f"Created default API key from configuration: {key_id}")
        logger.warning(f"API Key: {api_key} - Store this securely!")
    
    # Create middleware
    require_auth = config.get('api_key_enabled', True)
    public_endpoints = set(config.get('public_endpoints', [
        '/api/v1/version',
        '/health'
    ]))
    
    middleware = AuthMiddleware(
        key_manager=key_manager,
        auth_logger=auth_logger,
        require_auth=require_auth,
        public_endpoints=public_endpoints
    )
    
    return key_manager, middleware, auth_logger
