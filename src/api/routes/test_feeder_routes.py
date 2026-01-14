#!/usr/bin/env python3
# Unit tests for Feeder Routes

import pytest
from aiohttp import web
from unittest.mock import Mock, AsyncMock


@pytest.fixture
def mock_server():
    """Create a mock server instance."""
    server = Mock()
    server.execute_command = AsyncMock()
    server.safety_manager = Mock()
    server.safety_manager.validate_feeder_command = AsyncMock(return_value=(True, []))
    return server


@pytest.fixture
def mock_request():
    """Create a mock request object."""
    request = Mock()
    request.json = AsyncMock()
    request.app = {'server': None}
    return request


# Import route handlers
from api.routes.feeder_routes import handle_feeder_advance


class TestHandleFeederAdvance:
    """Test handle_feeder_advance route handler."""
    
    @pytest.mark.asyncio
    async def test_handle_feeder_advance_success(self, mock_server, mock_request):
        """Test successful feeder advance command."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data
        mock_request.json.return_value = {
            'distance': 10.0
        }
        
        # Setup mock response
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        mock_server.execute_command.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            gcode="FEEDER_ADVANCE DISTANCE=10.0"
        )
        
        # Call handler
        response = await handle_feeder_advance(mock_request)
        
        # Verify response
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
        assert 'gcode' in data
    
    @pytest.mark.asyncio
    async def test_handle_feeder_advance_missing_distance(self, mock_server, mock_request):
        """Test feeder advance with missing distance parameter."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data without distance
        mock_request.json.return_value = {}
        
        # Call handler
        response = await handle_feeder_advance(mock_request)
        
        # Verify error response
        assert response.status == 400
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'MISSING_PARAMETER'
        assert 'Distance is required' in data['error_message']
    
    @pytest.mark.asyncio
    async def test_handle_feeder_advance_invalid_distance(self, mock_server, mock_request):
        """Test feeder advance with invalid distance."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data with invalid distance
        mock_request.json.return_value = {
            'distance': -5.0
        }
        
        # Setup safety manager to return violation
        mock_server.safety_manager.validate_feeder_command = AsyncMock(
            return_value=(False, ['Distance must be positive'])
        )
        
        # Call handler
        response = await handle_feeder_advance(mock_request)
        
        # Verify error response
        assert response.status == 400
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'BOUNDS_VIOLATION'
    
    @pytest.mark.asyncio
    async def test_handle_feeder_advance_with_speed(self, mock_server, mock_request):
        """Test feeder advance with speed parameter."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data with speed
        mock_request.json.return_value = {
            'distance': 10.0,
            'speed': 50.0
        }
        
        # Setup mock response
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        mock_server.execute_command.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            gcode="FEEDER_ADVANCE DISTANCE=10.0 SPEED=50.0"
        )
        
        # Call handler
        response = await handle_feeder_advance(mock_request)
        
        # Verify response
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
    
    @pytest.mark.asyncio
    async def test_handle_feeder_advance_exception(self, mock_server, mock_request):
        """Test feeder advance with exception."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data
        mock_request.json.return_value = {
            'distance': 10.0
        }
        
        # Setup mock to raise exception
        mock_server.execute_command = AsyncMock(side_effect=Exception('Feeder advance failed'))
        
        # Call handler
        response = await handle_feeder_advance(mock_request)
        
        # Verify error response
        assert response.status == 500
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'EXECUTION_ERROR'


class TestSetup:
    """Test route setup."""
    
    def test_setup(self):
        """Test that routes are registered correctly."""
        from api.routes.feeder_routes import setup
        from aiohttp import web
        
        app = web.Application()
        setup(app)
        
        # Verify routes are registered
        routes = [route.path for route in app.router.routes()]
        assert '/api/v1/feeders/advance' in routes
