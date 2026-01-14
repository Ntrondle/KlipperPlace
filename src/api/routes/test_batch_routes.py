#!/usr/bin/env python3
# Unit tests for Batch Routes

import pytest
from aiohttp import web
from unittest.mock import Mock, AsyncMock


@pytest.fixture
def mock_server():
    """Create a mock server instance."""
    server = Mock()
    server.execute_batch = AsyncMock()
    server.safety_manager = Mock()
    server.safety_manager.validate_move_command = AsyncMock(return_value=(True, []))
    return server


@pytest.fixture
def mock_request():
    """Create a mock request object."""
    request = Mock()
    request.json = AsyncMock()
    request.app = {'server': None}
    return request


# Import route handlers
from api.routes.batch_routes import handle_execute_batch


class TestHandleExecuteBatch:
    """Test handle_execute_batch route handler."""
    
    @pytest.mark.asyncio
    async def test_handle_execute_batch_success(self, mock_server, mock_request):
        """Test successful execute batch command."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data
        mock_request.json.return_value = {
            'gcodes': ['G0 X100', 'G0 Y100'],
            'stop_on_error': True
        }
        
        # Setup mock response
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        mock_server.execute_batch.return_value = [
            ExecutionResult(status=ExecutionStatus.SUCCESS, gcode='G0 X100'),
            ExecutionResult(status=ExecutionStatus.SUCCESS, gcode='G0 Y100')
        ]
        
        # Call handler
        response = await handle_execute_batch(mock_request)
        
        # Verify response
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
        assert len(data['results']) == 2
        assert data['results'][0]['status'] == 'success'
        assert data['results'][1]['status'] == 'success'
    
    @pytest.mark.asyncio
    async def test_handle_execute_batch_no_gcodes(self, mock_server, mock_request):
        """Test execute batch with no G-codes."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data without gcodes
        mock_request.json.return_value = {
            'stop_on_error': True
        }
        
        # Call handler
        response = await handle_execute_batch(mock_request)
        
        # Verify error response
        assert response.status == 400
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'MISSING_PARAMETER'
        assert 'G-codes list is required' in data['error_message']
    
    @pytest.mark.asyncio
    async def test_handle_execute_batch_empty_gcodes(self, mock_server, mock_request):
        """Test execute batch with empty G-codes list."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data with empty gcodes list
        mock_request.json.return_value = {
            'gcodes': [],
            'stop_on_error': True
        }
        
        # Call handler
        response = await handle_execute_batch(mock_request)
        
        # Verify error response
        assert response.status == 400
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'MISSING_PARAMETER'
        assert 'G-codes list is required' in data['error_message']
    
    @pytest.mark.asyncio
    async def test_handle_execute_batch_with_error(self, mock_server, mock_request):
        """Test execute batch with one error."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data
        mock_request.json.return_value = {
            'gcodes': ['G0 X100', 'INVALID_COMMAND'],
            'stop_on_error': True
        }
        
        # Setup mock response with one error
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        mock_server.execute_batch.return_value = [
            ExecutionResult(status=ExecutionStatus.SUCCESS, gcode='G0 X100'),
            ExecutionResult(
                status=ExecutionStatus.ERROR,
                gcode='INVALID_COMMAND',
                error='Unknown command'
            )
        ]
        
        # Call handler
        response = await handle_execute_batch(mock_request)
        
        # Verify response
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'partial_success'
        assert len(data['results']) == 2
        assert data['results'][0]['status'] == 'success'
        assert data['results'][1]['status'] == 'error'
    
    @pytest.mark.asyncio
    async def test_handle_execute_batch_exception(self, mock_server, mock_request):
        """Test execute batch with exception."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data
        mock_request.json.return_value = {
            'gcodes': ['G0 X100', 'G0 Y100'],
            'stop_on_error': True
        }
        
        # Setup mock to raise exception
        mock_server.execute_batch = AsyncMock(side_effect=Exception('Batch execution failed'))
        
        # Call handler
        response = await handle_execute_batch(mock_request)
        
        # Verify error response
        assert response.status == 500
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'EXECUTION_ERROR'
    
    @pytest.mark.asyncio
    async def test_handle_execute_batch_default_stop_on_error(self, mock_server, mock_request):
        """Test execute batch with default stop_on_error parameter."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data without stop_on_error
        mock_request.json.return_value = {
            'gcodes': ['G0 X100', 'G0 Y100']
        }
        
        # Setup mock response
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        mock_server.execute_batch.return_value = [
            ExecutionResult(status=ExecutionStatus.SUCCESS, gcode='G0 X100'),
            ExecutionResult(status=ExecutionStatus.SUCCESS, gcode='G0 Y100')
        ]
        
        # Call handler
        response = await handle_execute_batch(mock_request)
        
        # Verify response
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'


class TestSetup:
    """Test route setup."""
    
    def test_setup(self):
        """Test that routes are registered correctly."""
        from api.routes.batch_routes import setup
        from aiohttp import web
        
        app = web.Application()
        setup(app)
        
        # Verify routes are registered
        routes = [route.path for route in app.router.routes()]
        assert '/api/v1/batch/execute' in routes
