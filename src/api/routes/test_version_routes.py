#!/usr/bin/env python3
# Unit tests for Version Routes

import pytest
from aiohttp import web
from unittest.mock import Mock, AsyncMock


@pytest.fixture
def mock_server():
    """Create a mock server instance."""
    server = Mock()
    server.execute_command = AsyncMock()
    server.get_version = AsyncMock()
    return server


@pytest.fixture
def mock_request():
    """Create a mock request object."""
    request = Mock()
    request.json = AsyncMock()
    request.app = {'server': None}
    return request


# Import route handlers
from api.routes.version_routes import handle_get_version


class TestHandleGetVersion:
    """Test handle_get_version route handler."""
    
    @pytest.mark.asyncio
    async def test_handle_get_version_success(self, mock_server, mock_request):
        """Test successful get version command."""
        mock_request.app = {'server': mock_server}
        
        # Setup mock response
        mock_server.get_version.return_value = {
            'version': '1.0.0',
            'api_version': '1.0',
            'git_hash': 'abc123',
            'build_date': '2024-01-01'
        }
        
        # Call handler
        response = await handle_get_version(mock_request)
        
        # Verify response
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
        assert 'version' in data
        assert data['version'] == '1.0.0'
        assert 'api_version' in data
        assert data['api_version'] == '1.0'
        assert 'git_hash' in data
        assert data['git_hash'] == 'abc123'
        assert 'build_date' in data
    
    @pytest.mark.asyncio
    async def test_handle_get_version_exception(self, mock_server, mock_request):
        """Test get version with exception."""
        mock_request.app = {'server': mock_server}
        
        # Setup mock to raise exception
        mock_server.get_version = AsyncMock(side_effect=Exception('Version query failed'))
        
        # Call handler
        response = await handle_get_version(mock_request)
        
        # Verify error response
        assert response.status == 500
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'EXECUTION_ERROR'
    
    @pytest.mark.asyncio
    async def test_handle_get_version_partial_response(self, mock_server, mock_request):
        """Test get version with partial response."""
        mock_request.app = {'server': mock_server}
        
        # Setup mock response with partial data
        mock_server.get_version.return_value = {
            'version': '1.0.0',
            'api_version': '1.0'
        }
        
        # Call handler
        response = await handle_get_version(mock_request)
        
        # Verify response
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
        assert 'version' in data
        assert 'api_version' in data


class TestSetup:
    """Test route setup."""
    
    def test_setup(self):
        """Test that routes are registered correctly."""
        from api.routes.version_routes import setup
        from aiohttp import web
        
        app = web.Application()
        setup(app)
        
        # Verify routes are registered
        routes = [route.path for route in app.router.routes()]
        assert '/api/v1/version' in routes
