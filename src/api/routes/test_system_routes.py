#!/usr/bin/env python3
# Unit tests for System Routes

import pytest
from aiohttp import web
from unittest.mock import Mock, AsyncMock


@pytest.fixture
def mock_server():
    """Create a mock server instance."""
    server = Mock()
    server.execute_command = AsyncMock()
    server.get_system_info = AsyncMock()
    return server


@pytest.fixture
def mock_request():
    """Create a mock request object."""
    request = Mock()
    request.json = AsyncMock()
    request.app = {'server': None}
    return request


# Import route handlers
from api.routes.system_routes import handle_get_info


class TestHandleGetInfo:
    """Test handle_get_info route handler."""
    
    @pytest.mark.asyncio
    async def test_handle_get_info_success(self, mock_server, mock_request):
        """Test successful get info command."""
        mock_request.app = {'server': mock_server}
        
        # Setup mock response
        mock_server.get_system_info.return_value = {
            'version': '1.0.0',
            'api_version': '1.0',
            'hostname': 'klipperplace',
            'uptime': 3600,
            'cpu_usage': 25.5,
            'memory_usage': 512.0
        }
        
        # Call handler
        response = await handle_get_info(mock_request)
        
        # Verify response
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
        assert 'version' in data
        assert data['version'] == '1.0.0'
        assert 'api_version' in data
        assert data['api_version'] == '1.0'
        assert 'uptime' in data
        assert data['uptime'] == 3600
    
    @pytest.mark.asyncio
    async def test_handle_get_info_exception(self, mock_server, mock_request):
        """Test get info with exception."""
        mock_request.app = {'server': mock_server}
        
        # Setup mock to raise exception
        mock_server.get_system_info = AsyncMock(side_effect=Exception('System info query failed'))
        
        # Call handler
        response = await handle_get_info(mock_request)
        
        # Verify error response
        assert response.status == 500
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'EXECUTION_ERROR'
    
    @pytest.mark.asyncio
    async def test_handle_get_info_partial_response(self, mock_server, mock_request):
        """Test get info with partial response."""
        mock_request.app = {'server': mock_server}
        
        # Setup mock response with partial data
        mock_server.get_system_info.return_value = {
            'version': '1.0.0',
            'api_version': '1.0'
        }
        
        # Call handler
        response = await handle_get_info(mock_request)
        
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
        from api.routes.system_routes import setup
        from aiohttp import web
        
        app = web.Application()
        setup(app)
        
        # Verify routes are registered
        routes = [route.path for route in app.router.routes()]
        assert '/api/v1/system/info' in routes
