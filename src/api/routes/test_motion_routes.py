#!/usr/bin/env python3
# Unit tests for Motion Routes

import pytest
from aiohttp import web
from unittest.mock import Mock, AsyncMock, MagicMock


@pytest.fixture
def mock_server():
    """Create a mock server instance."""
    server = Mock()
    server.execute_command = AsyncMock()
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
from api.routes.motion_routes import handle_move, handle_home


class TestHandleMove:
    """Test handle_move route handler."""
    
    @pytest.mark.asyncio
    async def test_handle_move_success(self, mock_server, mock_request):
        """Test successful move command."""
        # Setup mock server
        mock_request.app = {'server': mock_server}
        
        # Setup request data
        mock_request.json.return_value = {
            'x': 100.0,
            'y': 50.0,
            'z': 10.0,
            'feedrate': 1500.0,
            'relative': False
        }
        
        # Setup mock response
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        mock_server.execute_command.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            gcode="G0 X100 Y50 Z10 F1500"
        )
        
        # Call handler
        response = await handle_move(mock_request)
        
        # Verify response
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
        assert 'gcode' in data
        
        # Verify command was created
        mock_server.execute_command.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_move_missing_parameters(self, mock_server, mock_request):
        """Test move command with missing parameters."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data with no coordinates
        mock_request.json.return_value = {
            'feedrate': 1500.0
        }
        
        # Call handler
        response = await handle_move(mock_request)
        
        # Verify error response
        assert response.status == 400
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'MISSING_PARAMETER'
        assert 'at least one of x, y, or z' in data['error_message'].lower()
        
        # Verify command was not executed
        mock_server.execute_command.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_handle_move_bounds_violation(self, mock_server, mock_request):
        """Test move command with bounds violation."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data with out of bounds position
        mock_request.json.return_value = {
            'x': 500.0,  # Beyond max_x_position (300.0)
            'y': 50.0,
            'z': 10.0,
            'feedrate': 1500.0
        }
        
        # Setup safety manager to return violation
        mock_server.safety_manager.validate_move_command = AsyncMock(
            return_value=(False, ['X position 500.0 mm out of bounds [0.0, 300.0]'])
        )
        
        # Call handler
        response = await handle_move(mock_request)
        
        # Verify error response
        assert response.status == 400
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'BOUNDS_VIOLATION'
        assert 'validation failed' in data['error_message'].lower()
        assert 'errors' in data['details']
        
        # Verify command was not executed
        mock_server.execute_command.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_handle_move_relative_positioning(self, mock_server, mock_request):
        """Test move command with relative positioning."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data with relative positioning
        mock_request.json.return_value = {
            'x': 100.0,
            'y': 50.0,
            'z': 10.0,
            'feedrate': 1500.0,
            'relative': True
        }
        
        # Setup mock response
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        mock_server.execute_command.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            gcode="G0 X100 Y50 Z10 F1500"
        )
        
        # Call handler
        response = await handle_move(mock_request)
        
        # Verify response
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
        
        # Verify command was created with relative flag
        call_args = mock_server.execute_command.call_args
        assert call_args[0][1]['parameters']['relative'] == True
    
    @pytest.mark.asyncio
    async def test_handle_move_exception(self, mock_server, mock_request):
        """Test move command with exception."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data
        mock_request.json.return_value = {
            'x': 100.0,
            'y': 50.0,
            'z': 10.0,
            'feedrate': 1500.0
        }
        
        # Setup mock to raise exception
        mock_server.execute_command = AsyncMock(side_effect=Exception('Execution failed'))
        
        # Call handler
        response = await handle_move(mock_request)
        
        # Verify error response
        assert response.status == 500
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'EXECUTION_ERROR'
        assert 'Execution failed' in data['error_message']


class TestHandleHome:
    """Test handle_home route handler."""
    
    @pytest.mark.asyncio
    async def test_handle_home_all_axes(self, mock_server, mock_request):
        """Test home command for all axes."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data
        mock_request.json.return_value = {
            'axes': 'all'
        }
        
        # Setup mock response
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        mock_server.execute_command.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            gcode="G28"
        )
        
        # Call handler
        response = await handle_home(mock_request)
        
        # Verify response
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
        assert 'gcode' in data
        
        # Verify command was created
        mock_server.execute_command.assert_called_once()
        
        # Verify axes were marked as homed
        assert mock_server.safety_manager.mark_axis_homed.call_count == 3
    
    @pytest.mark.asyncio
    async def test_handle_home_specific_axes(self, mock_server, mock_request):
        """Test home command for specific axes."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data
        mock_request.json.return_value = {
            'axes': ['x', 'y']
        }
        
        # Setup mock response
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        mock_server.execute_command.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            gcode="G28 X Y"
        )
        
        # Call handler
        response = await handle_home(mock_request)
        
        # Verify response
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
        assert 'gcode' in data
        
        # Verify command was created
        mock_server.execute_command.assert_called_once()
        
        # Verify only X and Y axes were marked as homed
        assert mock_server.safety_manager.mark_axis_homed.call_count == 2
    
    @pytest.mark.asyncio
    async def test_handle_home_exception(self, mock_server, mock_request):
        """Test home command with exception."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data
        mock_request.json.return_value = {
            'axes': 'all'
        }
        
        # Setup mock to raise exception
        mock_server.execute_command = AsyncMock(side_effect=Exception('Homing failed'))
        
        # Call handler
        response = await handle_home(mock_request)
        
        # Verify error response
        assert response.status == 500
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'EXECUTION_ERROR'
        assert 'Homing failed' in data['error_message']
        
        # Verify axes were not marked as homed
        mock_server.safety_manager.mark_axis_homed.assert_not_called()


class TestSetup:
    """Test route setup."""
    
    def test_setup(self):
        """Test that routes are registered correctly."""
        from api.routes.motion_routes import setup
        from aiohttp import web
        
        app = web.Application()
        setup(app)
        
        # Verify routes are registered
        routes = [route.path for route in app.router.routes()]
        assert '/api/v1/motion/move' in routes
        assert '/api/v1/motion/home' in routes
