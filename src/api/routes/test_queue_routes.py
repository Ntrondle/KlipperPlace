#!/usr/bin/env python3
# Unit tests for Queue Routes

import pytest
from aiohttp import web
from unittest.mock import Mock, AsyncMock


@pytest.fixture
def mock_server():
    """Create a mock server instance."""
    server = Mock()
    server.execute_command = AsyncMock()
    server.get_queue_status = AsyncMock()
    server.clear_queue = AsyncMock()
    return server


@pytest.fixture
def mock_request():
    """Create a mock request object."""
    request = Mock()
    request.json = AsyncMock()
    request.app = {'server': None}
    return request


# Import route handlers
from api.routes.queue_routes import handle_get_queue, handle_clear_queue


class TestHandleGetQueue:
    """Test handle_get_queue route handler."""
    
    @pytest.mark.asyncio
    async def test_handle_get_queue_success(self, mock_server, mock_request):
        """Test successful get queue command."""
        mock_request.app = {'server': mock_server}
        
        # Setup mock response
        mock_server.get_queue_status.return_value = {
            'size': 3,
            'snapshot': [
                {'id': 'cmd1', 'command': 'G0 X100', 'priority': 1},
                {'id': 'cmd2', 'command': 'G0 Y100', 'priority': 1},
                {'id': 'cmd3', 'command': 'G0 Z100', 'priority': 1}
            ]
        }
        
        # Call handler
        response = await handle_get_queue(mock_request)
        
        # Verify response
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
        assert data['size'] == 3
        assert len(data['snapshot']) == 3
        assert data['snapshot'][0]['command'] == 'G0 X100'
    
    @pytest.mark.asyncio
    async def test_handle_get_queue_empty(self, mock_server, mock_request):
        """Test get queue with empty queue."""
        mock_request.app = {'server': mock_server}
        
        # Setup mock response
        mock_server.get_queue_status.return_value = {
            'size': 0,
            'snapshot': []
        }
        
        # Call handler
        response = await handle_get_queue(mock_request)
        
        # Verify response
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
        assert data['size'] == 0
        assert len(data['snapshot']) == 0
    
    @pytest.mark.asyncio
    async def test_handle_get_queue_exception(self, mock_server, mock_request):
        """Test get queue with exception."""
        mock_request.app = {'server': mock_server}
        
        # Setup mock to raise exception
        mock_server.get_queue_status = AsyncMock(side_effect=Exception('Queue query failed'))
        
        # Call handler
        response = await handle_get_queue(mock_request)
        
        # Verify error response
        assert response.status == 500
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'EXECUTION_ERROR'


class TestHandleClearQueue:
    """Test handle_clear_queue route handler."""
    
    @pytest.mark.asyncio
    async def test_handle_clear_queue_success(self, mock_server, mock_request):
        """Test successful clear queue command."""
        mock_request.app = {'server': mock_server}
        
        # Setup mock response
        mock_server.clear_queue.return_value = {
            'cleared': 5
        }
        
        # Call handler
        response = await handle_clear_queue(mock_request)
        
        # Verify response
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
        assert data['cleared'] == 5
    
    @pytest.mark.asyncio
    async def test_handle_clear_queue_empty(self, mock_server, mock_request):
        """Test clear queue when queue is empty."""
        mock_request.app = {'server': mock_server}
        
        # Setup mock response
        mock_server.clear_queue.return_value = {
            'cleared': 0
        }
        
        # Call handler
        response = await handle_clear_queue(mock_request)
        
        # Verify response
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
        assert data['cleared'] == 0
    
    @pytest.mark.asyncio
    async def test_handle_clear_queue_exception(self, mock_server, mock_request):
        """Test clear queue with exception."""
        mock_request.app = {'server': mock_server}
        
        # Setup mock to raise exception
        mock_server.clear_queue = AsyncMock(side_effect=Exception('Clear queue failed'))
        
        # Call handler
        response = await handle_clear_queue(mock_request)
        
        # Verify error response
        assert response.status == 500
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'EXECUTION_ERROR'


class TestSetup:
    """Test route setup."""
    
    def test_setup(self):
        """Test that routes are registered correctly."""
        from api.routes.queue_routes import setup
        from aiohttp import web
        
        app = web.Application()
        setup(app)
        
        # Verify routes are registered
        routes = [route.path for route in app.router.routes()]
        assert '/api/v1/queue' in routes
        assert '/api/v1/queue/clear' in routes
