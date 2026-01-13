#!/usr/bin/env python3
# API Key Management Routes
# Endpoints for managing API keys

import logging
from typing import Dict, Any, List
from aiohttp import web
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


# Pydantic models for request validation
class CreateAPIKeyRequest(BaseModel):
    """Request model for creating API key."""
    name: str = Field(..., min_length=1, max_length=100, description="API key name")
    permissions: List[str] = Field(..., description="List of permissions")
    rate_limit: int = Field(100, ge=1, le=10000, description="Rate limit (requests per second)")
    description: str = Field("", max_length=500, description="Optional description")
    
    @validator('permissions')
    def validate_permissions(cls, v):
        """Validate permissions list."""
        valid_permissions = ['read', 'write', 'admin']
        for perm in v:
            if perm not in valid_permissions:
                raise ValueError(f"Invalid permission: {perm}. Valid permissions: {valid_permissions}")
        return v


class UpdateAPIKeyRequest(BaseModel):
    """Request model for updating API key."""
    name: str = Field(None, min_length=1, max_length=100)
    permissions: List[str] = None
    rate_limit: int = Field(None, ge=1, le=10000)
    description: str = Field(None, max_length=500)
    is_active: bool = None


def setup(app: web.Application) -> None:
    """Setup authentication routes.
    
    Args:
        app: aiohttp application
    """
    # API key management endpoints
    app.router.add_post('/api/v1/auth/keys', create_api_key)
    app.router.add_get('/api/v1/auth/keys', list_api_keys)
    app.router.add_get('/api/v1/auth/keys/{key_id}', get_api_key)
    app.router.add_put('/api/v1/auth/keys/{key_id}', update_api_key)
    app.router.add_delete('/api/v1/auth/keys/{key_id}', delete_api_key)
    
    # Auth status endpoint
    app.router.add_get('/api/v1/auth/status', get_auth_status)
    
    logger.info("Authentication routes registered")


async def create_api_key(request: web.Request) -> web.Response:
    """Create a new API key.
    
    Args:
        request: Incoming request
        
    Returns:
        Response with created API key
    """
    try:
        # Get server instance
        server = request.app['server']
        
        # Check if API key has admin permission
        api_key = request.get('api_key')
        if not server.key_manager.check_permission(api_key, 'admin'):
            return web.json_response(
                {
                    'status': 'error',
                    'error_code': 'PERMISSION_DENIED',
                    'error_message': 'Admin permission required to create API keys'
                },
                status=403
            )
        
        # Parse request body
        try:
            data = await request.json()
            key_request = CreateAPIKeyRequest(**data)
        except Exception as e:
            return web.json_response(
                {
                    'status': 'error',
                    'error_code': 'INVALID_REQUEST',
                    'error_message': f'Invalid request: {str(e)}'
                },
                status=400
            )
        
        # Create API key
        key_id, api_key_value = server.key_manager.create_key(
            name=key_request.name,
            permissions=key_request.permissions,
            rate_limit=key_request.rate_limit,
            description=key_request.description
        )
        
        # Return response (only show the key value once!)
        return web.json_response(
            {
                'status': 'success',
                'command': 'create_api_key',
                'data': {
                    'key_id': key_id,
                    'api_key': api_key_value,
                    'message': 'Save this API key securely - it will not be shown again!'
                }
            },
            status=201
        )
        
    except Exception as e:
        logger.error(f"Error creating API key: {e}", exc_info=True)
        return web.json_response(
            {
                'status': 'error',
                'error_code': 'INTERNAL_ERROR',
                'error_message': 'Failed to create API key'
            },
            status=500
        )


async def list_api_keys(request: web.Request) -> web.Response:
    """List all API keys.
    
    Args:
        request: Incoming request
        
    Returns:
        Response with list of API keys
    """
    try:
        # Get server instance
        server = request.app['server']
        
        # Check if API key has admin permission
        api_key = request.get('api_key')
        if not server.key_manager.check_permission(api_key, 'admin'):
            return web.json_response(
                {
                    'status': 'error',
                    'error_code': 'PERMISSION_DENIED',
                    'error_message': 'Admin permission required to list API keys'
                },
                status=403
            )
        
        # List API keys
        keys = server.key_manager.list_keys()
        
        return web.json_response(
            {
                'status': 'success',
                'command': 'list_api_keys',
                'data': {
                    'api_keys': keys,
                    'count': len(keys)
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Error listing API keys: {e}", exc_info=True)
        return web.json_response(
            {
                'status': 'error',
                'error_code': 'INTERNAL_ERROR',
                'error_message': 'Failed to list API keys'
            },
            status=500
        )


async def get_api_key(request: web.Request) -> web.Response:
    """Get a specific API key by ID.
    
    Args:
        request: Incoming request
        
    Returns:
        Response with API key details
    """
    try:
        # Get server instance
        server = request.app['server']
        
        # Check if API key has admin permission
        api_key = request.get('api_key')
        if not server.key_manager.check_permission(api_key, 'admin'):
            return web.json_response(
                {
                    'status': 'error',
                    'error_code': 'PERMISSION_DENIED',
                    'error_message': 'Admin permission required to view API keys'
                },
                status=403
            )
        
        # Get key ID from path
        key_id = request.match_info['key_id']
        
        # Get API key
        key = server.key_manager.get_key(key_id)
        
        if not key:
            return web.json_response(
                {
                    'status': 'error',
                    'error_code': 'KEY_NOT_FOUND',
                    'error_message': f'API key not found: {key_id}'
                },
                status=404
            )
        
        return web.json_response(
            {
                'status': 'success',
                'command': 'get_api_key',
                'data': key.to_dict()
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting API key: {e}", exc_info=True)
        return web.json_response(
            {
                'status': 'error',
                'error_code': 'INTERNAL_ERROR',
                'error_message': 'Failed to get API key'
            },
            status=500
        )


async def update_api_key(request: web.Request) -> web.Response:
    """Update an API key.
    
    Args:
        request: Incoming request
        
    Returns:
        Response with updated API key
    """
    try:
        # Get server instance
        server = request.app['server']
        
        # Check if API key has admin permission
        api_key = request.get('api_key')
        if not server.key_manager.check_permission(api_key, 'admin'):
            return web.json_response(
                {
                    'status': 'error',
                    'error_code': 'PERMISSION_DENIED',
                    'error_message': 'Admin permission required to update API keys'
                },
                status=403
            )
        
        # Get key ID from path
        key_id = request.match_info['key_id']
        
        # Parse request body
        try:
            data = await request.json()
            update_request = UpdateAPIKeyRequest(**data)
        except Exception as e:
            return web.json_response(
                {
                    'status': 'error',
                    'error_code': 'INVALID_REQUEST',
                    'error_message': f'Invalid request: {str(e)}'
                },
                status=400
            )
        
        # Build update dictionary
        updates = {}
        if update_request.name is not None:
            updates['name'] = update_request.name
        if update_request.permissions is not None:
            updates['permissions'] = update_request.permissions
        if update_request.rate_limit is not None:
            updates['rate_limit'] = update_request.rate_limit
        if update_request.description is not None:
            updates['description'] = update_request.description
        if update_request.is_active is not None:
            updates['is_active'] = update_request.is_active
        
        # Update API key
        success = server.key_manager.update_key(key_id, **updates)
        
        if not success:
            return web.json_response(
                {
                    'status': 'error',
                    'error_code': 'KEY_NOT_FOUND',
                    'error_message': f'API key not found: {key_id}'
                },
                status=404
            )
        
        # Get updated key
        updated_key = server.key_manager.get_key(key_id)
        
        return web.json_response(
            {
                'status': 'success',
                'command': 'update_api_key',
                'data': updated_key.to_dict()
            }
        )
        
    except Exception as e:
        logger.error(f"Error updating API key: {e}", exc_info=True)
        return web.json_response(
            {
                'status': 'error',
                'error_code': 'INTERNAL_ERROR',
                'error_message': 'Failed to update API key'
            },
            status=500
        )


async def delete_api_key(request: web.Request) -> web.Response:
    """Delete an API key.
    
    Args:
        request: Incoming request
        
    Returns:
        Response confirming deletion
    """
    try:
        # Get server instance
        server = request.app['server']
        
        # Check if API key has admin permission
        api_key = request.get('api_key')
        if not server.key_manager.check_permission(api_key, 'admin'):
            return web.json_response(
                {
                    'status': 'error',
                    'error_code': 'PERMISSION_DENIED',
                    'error_message': 'Admin permission required to delete API keys'
                },
                status=403
            )
        
        # Get key ID from path
        key_id = request.match_info['key_id']
        
        # Delete API key
        success = server.key_manager.delete_key(key_id)
        
        if not success:
            return web.json_response(
                {
                    'status': 'error',
                    'error_code': 'KEY_NOT_FOUND',
                    'error_message': f'API key not found: {key_id}'
                },
                status=404
            )
        
        return web.json_response(
            {
                'status': 'success',
                'command': 'delete_api_key',
                'data': {
                    'key_id': key_id,
                    'message': 'API key deleted successfully'
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Error deleting API key: {e}", exc_info=True)
        return web.json_response(
            {
                'status': 'error',
                'error_code': 'INTERNAL_ERROR',
                'error_message': 'Failed to delete API key'
            },
            status=500
        )


async def get_auth_status(request: web.Request) -> web.Response:
    """Get authentication status for current API key.
    
    Args:
        request: Incoming request
        
    Returns:
        Response with authentication status
    """
    try:
        # Get server instance
        server = request.app['server']
        
        # Get API key from request
        api_key = request.get('api_key')
        
        if not api_key:
            return web.json_response(
                {
                    'status': 'success',
                    'command': 'get_auth_status',
                    'data': {
                        'authenticated': False,
                        'message': 'No API key provided'
                    }
                }
            )
        
        # Get rate limit info
        rate_info = server.key_manager.get_rate_limit_info(api_key)
        
        return web.json_response(
            {
                'status': 'success',
                'command': 'get_auth_status',
                'data': {
                    'authenticated': True,
                    'key_id': api_key.key_id,
                    'key_name': api_key.name,
                    'permissions': api_key.permissions,
                    'rate_limit': {
                        'limit': rate_info['limit'],
                        'remaining': rate_info['remaining'],
                        'reset': rate_info['reset']
                    },
                    'last_used': api_key.last_used,
                    'created_at': api_key.created_at,
                    'is_active': api_key.is_active
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting auth status: {e}", exc_info=True)
        return web.json_response(
            {
                'status': 'error',
                'error_code': 'INTERNAL_ERROR',
                'error_message': 'Failed to get authentication status'
            },
            status=500
        )
