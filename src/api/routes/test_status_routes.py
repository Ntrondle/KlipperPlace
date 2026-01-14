#!/usr/bin/env python3
# Unit tests for Status Routes

import pytest
from aiohttp import web
from unittest.mock import Mock, AsyncMock


@pytest.fixture
def mock_server():
    """Create a mock server instance."""
    server = Mock()
    server.execute_command = AsyncMock()
    server.get_status = AsyncMock()
    return server


@pytest.fixture
def mock_request():
    """Create a mock request object."""
    request = Mock()
    request.json = AsyncMock()
    request.app = {'server': None}
    return request


# Import route handlers
from api.routes.status_routes import handle_get_status


class TestHandleGetStatus:
    """Test handle_get_status route handler."""
    
    @pytest.mark.asyncio
    async def test_handle_get_status_success(self, mock_server, mock_request):
        """Test successful get status command."""
        mock_request.app = {'server': mock_server}
        
        # Setup mock response
        mock_server.get_status.return_value = {
            'status': 'idle',
            'position': {'x': 100, 'y': 50, 'z': 10},
            'homed_axes': ['x', 'y', 'z'],
            'print_stats': {
                'state': 'idle',
                'print_duration': 0
            }
        }
        
        # Call handler
        response = await handle_get_status(mock_request)
        
        # Verify response
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
        assert 'status' in data
        assert data['status'] == 'idle'
        assert 'position' in data
        assert data['position']['x'] == 100
    
    @pytest.mark.asyncio
    async def test_handle_get_status_with_filter(self, mock_server, mock_request):
        """Test get status with filter parameter."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data with filter
        mock_request.json.return_value = {
            'filter': ['position', 'homed_axes']
        }
        
        # Setup mock response
        mock_server.get_status.return_value = {
            'position': {'x': 100, 'y': 50, 'z': 10},
            'homed_axes': ['x', 'y', 'z']
        }
        
        # Call handler
        response = await handle_get_status(mock_request)
        
        # Verify response
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
        assert 'position' in data
        assert 'homed_axes' in data
        assert 'print_stats' not in data
    
    @pytest.mark.asyncio
    async def test_handle_get_status_exception(self, mock_server, mock_request):
        """Test get status with exception."""
        mock_request.app = {'server': mock_server}
        
        # Setup mock to raise exception
        mock_server.get_status = AsyncMock(side_effect=Exception('Status query failed'))
        
        # Call handler
        response = await handle_get_status(mock_request)
        
        # Verify error response
        assert response.status == 500
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'EXECUTION_ERROR'
    
    @pytest.mark.asyncio
    async def test_handle_get_status_empty_response(self, mock_server, mock_request):
        """Test get status with empty response."""
        mock_request.app = {'server': mock_server}
        
        # Setup mock response
        mock_server.get_status.return_value = {}
        
        # Call handler
        response = await handle_get_status(mock_request)
        
        # Verify response
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
        assert data['status_data'] == {}


class TestSetup:
    """Test route setup."""
    
    def test_setup(self):
        """Test that routes are registered correctly."""
        from api.routes.status_routes import setup
        from aiohttp import web
        
        app = web.Application()
        setup(app)
        
        # Verify routes are registered
        routes = [route.path for route in app.router.routes()]
        assert '/api/v1/status' in routes
