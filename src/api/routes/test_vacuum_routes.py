#!/usr/bin/env python3
# Unit tests for Vacuum Routes

import pytest
from aiohttp import web
from unittest.mock import Mock, AsyncMock


@pytest.fixture
def mock_server():
    """Create a mock server instance."""
    server = Mock()
    server.execute_command = AsyncMock()
    server.safety_manager = Mock()
    server.safety_manager.validate_vacuum_command = AsyncMock(return_value=(True, []))
    return server


@pytest.fixture
def mock_request():
    """Create a mock request object."""
    request = Mock()
    request.json = AsyncMock()
    request.app = {'server': None}
    return request


# Import route handlers
from api.routes.vacuum_routes import handle_vacuum_on, handle_vacuum_off, handle_vacuum_set


class TestHandleVacuumOn:
    """Test handle_vacuum_on route handler."""
    
    @pytest.mark.asyncio
    async def test_handle_vacuum_on_success(self, mock_server, mock_request):
        """Test successful vacuum on command."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data
        mock_request.json.return_value = {
            'power': 200
        }
        
        # Setup mock response
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        mock_server.execute_command.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            gcode="VACUUM_ON P200"
        )
        
        # Call handler
        response = await handle_vacuum_on(mock_request)
        
        # Verify response
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
        assert 'gcode' in data
    
    @pytest.mark.asyncio
    async def test_handle_vacuum_on_invalid_power(self, mock_server, mock_request):
        """Test vacuum on with invalid power."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data with invalid power
        mock_request.json.return_value = {
            'power': 300
        }
        
        # Setup safety manager to return violation
        mock_server.safety_manager.validate_vacuum_command = AsyncMock(
            return_value=(False, ['Power must be between 0 and 255'])
        )
        
        # Call handler
        response = await handle_vacuum_on(mock_request)
        
        # Verify error response
        assert response.status == 400
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'BOUNDS_VIOLATION'
    
    @pytest.mark.asyncio
    async def test_handle_vacuum_on_exception(self, mock_server, mock_request):
        """Test vacuum on with exception."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data
        mock_request.json.return_value = {
            'power': 200
        }
        
        # Setup mock to raise exception
        mock_server.execute_command = AsyncMock(side_effect=Exception('Vacuum on failed'))
        
        # Call handler
        response = await handle_vacuum_on(mock_request)
        
        # Verify error response
        assert response.status == 500
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'EXECUTION_ERROR'


class TestHandleVacuumOff:
    """Test handle_vacuum_off route handler."""
    
    @pytest.mark.asyncio
    async def test_handle_vacuum_off_success(self, mock_server, mock_request):
        """Test successful vacuum off command."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data
        mock_request.json.return_value = {}
        
        # Setup mock response
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        mock_server.execute_command.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            gcode="VACUUM_OFF"
        )
        
        # Call handler
        response = await handle_vacuum_off(mock_request)
        
        # Verify response
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
        assert 'gcode' in data
    
    @pytest.mark.asyncio
    async def test_handle_vacuum_off_exception(self, mock_server, mock_request):
        """Test vacuum off with exception."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data
        mock_request.json.return_value = {}
        
        # Setup mock to raise exception
        mock_server.execute_command = AsyncMock(side_effect=Exception('Vacuum off failed'))
        
        # Call handler
        response = await handle_vacuum_off(mock_request)
        
        # Verify error response
        assert response.status == 500
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'EXECUTION_ERROR'


class TestHandleVacuumSet:
    """Test handle_vacuum_set route handler."""
    
    @pytest.mark.asyncio
    async def test_handle_vacuum_set_success(self, mock_server, mock_request):
        """Test successful vacuum set command."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data
        mock_request.json.return_value = {
            'power': 150
        }
        
        # Setup mock response
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        mock_server.execute_command.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            gcode="VACUUM_SET P150"
        )
        
        # Call handler
        response = await handle_vacuum_set(mock_request)
        
        # Verify response
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
        assert 'gcode' in data
    
    @pytest.mark.asyncio
    async def test_handle_vacuum_set_missing_power(self, mock_server, mock_request):
        """Test vacuum set with missing power parameter."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data without power
        mock_request.json.return_value = {}
        
        # Call handler
        response = await handle_vacuum_set(mock_request)
        
        # Verify error response
        assert response.status == 400
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'MISSING_PARAMETER'
        assert 'Power value is required' in data['error_message']
    
    @pytest.mark.asyncio
    async def test_handle_vacuum_set_invalid_power(self, mock_server, mock_request):
        """Test vacuum set with invalid power."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data with invalid power
        mock_request.json.return_value = {
            'power': -10
        }
        
        # Setup safety manager to return violation
        mock_server.safety_manager.validate_vacuum_command = AsyncMock(
            return_value=(False, ['Power must be between 0 and 255'])
        )
        
        # Call handler
        response = await handle_vacuum_set(mock_request)
        
        # Verify error response
        assert response.status == 400
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'BOUNDS_VIOLATION'


class TestSetup:
    """Test route setup."""
    
    def test_setup(self):
        """Test that routes are registered correctly."""
        from api.routes.vacuum_routes import setup
        from aiohttp import web
        
        app = web.Application()
        setup(app)
        
        # Verify routes are registered
        routes = [route.path for route in app.router.routes()]
        assert '/api/v1/vacuum/on' in routes
        assert '/api/v1/vacuum/off' in routes
        assert '/api/v1/vacuum/set' in routes
