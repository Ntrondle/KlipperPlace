#!/usr/bin/env python3
# Unit tests for Pick and Place Routes

import pytest
from aiohttp import web
from unittest.mock import Mock, AsyncMock


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
from api.routes.pnp_routes import handle_pick, handle_place, handle_pick_and_place


class TestHandlePick:
    """Test handle_pick route handler."""
    
    @pytest.mark.asyncio
    async def test_handle_pick_success(self, mock_server, mock_request):
        """Test successful pick command."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data
        mock_request.json.return_value = {
            'z': 5.0,
            'feedrate': 1000.0,
            'vacuum_power': 200,
            'travel_height': 10.0
        }
        
        # Setup mock response
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        mock_server.execute_command.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            gcode="PICK commands"
        )
        
        # Call handler
        response = await handle_pick(mock_request)
        
        # Verify response
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
        assert 'gcode' in data
        
        # Verify command was created
        mock_server.execute_command.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_pick_with_defaults(self, mock_server, mock_request):
        """Test pick command with default values."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data with minimal parameters
        mock_request.json.return_value = {}
        
        # Setup mock response
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        mock_server.execute_command.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            gcode="PICK commands"
        )
        
        # Call handler
        response = await handle_pick(mock_request)
        
        # Verify response
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
        
        # Verify command was created
        mock_server.execute_command.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_pick_exception(self, mock_server, mock_request):
        """Test pick command with exception."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data
        mock_request.json.return_value = {
            'z': 5.0,
            'feedrate': 1000.0
        }
        
        # Setup mock to raise exception
        mock_server.execute_command = AsyncMock(side_effect=Exception('Pick failed'))
        
        # Call handler
        response = await handle_pick(mock_request)
        
        # Verify error response
        assert response.status == 500
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'EXECUTION_ERROR'
        assert 'Pick failed' in data['error_message']


class TestHandlePlace:
    """Test handle_place route handler."""
    
    @pytest.mark.asyncio
    async def test_handle_place_success(self, mock_server, mock_request):
        """Test successful place command."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data
        mock_request.json.return_value = {
            'z': 2.0,
            'feedrate': 800.0,
            'travel_height': 10.0
        }
        
        # Setup mock response
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        mock_server.execute_command.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            gcode="PLACE commands"
        )
        
        # Call handler
        response = await handle_place(mock_request)
        
        # Verify response
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
        assert 'gcode' in data
        
        # Verify command was created
        mock_server.execute_command.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_place_with_defaults(self, mock_server, mock_request):
        """Test place command with default values."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data with minimal parameters
        mock_request.json.return_value = {}
        
        # Setup mock response
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        mock_server.execute_command.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            gcode="PLACE commands"
        )
        
        # Call handler
        response = await handle_place(mock_request)
        
        # Verify response
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
        
        # Verify command was created
        mock_server.execute_command.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_place_exception(self, mock_server, mock_request):
        """Test place command with exception."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data
        mock_request.json.return_value = {
            'z': 2.0,
            'feedrate': 800.0
        }
        
        # Setup mock to raise exception
        mock_server.execute_command = AsyncMock(side_effect=Exception('Place failed'))
        
        # Call handler
        response = await handle_place(mock_request)
        
        # Verify error response
        assert response.status == 500
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'EXECUTION_ERROR'
        assert 'Place failed' in data['error_message']


class TestHandlePickAndPlace:
    """Test handle_pick_and_place route handler."""
    
    @pytest.mark.asyncio
    async def test_handle_pick_and_place_success(self, mock_server, mock_request):
        """Test successful pick and place command."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data
        mock_request.json.return_value = {
            'x': 100.0,
            'y': 50.0,
            'place_x': 200.0,
            'place_y': 150.0,
            'pick_height': 5.0,
            'place_height': 2.0,
            'safe_height': 10.0,
            'feedrate': 1200.0,
            'vacuum_power': 255
        }
        
        # Setup mock response
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        mock_server.execute_command.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            gcode="PICK_AND_PLACE commands"
        )
        
        # Call handler
        response = await handle_pick_and_place(mock_request)
        
        # Verify response
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
        assert 'gcode' in data
        
        # Verify command was created
        mock_server.execute_command.assert_called_once()
        
        # Verify axes were marked as homed
        assert mock_server.safety_manager.mark_axis_homed.call_count >= 2
    
    @pytest.mark.asyncio
    async def test_handle_pick_and_place_missing_parameters(self, mock_server, mock_request):
        """Test pick and place with missing required parameters."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data with missing parameters
        mock_request.json.return_value = {
            'x': 100.0,
            'y': 50.0
            # Missing place_x and place_y
        }
        
        # Call handler
        response = await handle_pick_and_place(mock_request)
        
        # Verify error response
        assert response.status == 400
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'MISSING_PARAMETER'
        assert 'place_x' in data['error_message'].lower()
        assert 'place_y' in data['error_message'].lower()
        
        # Verify command was not executed
        mock_server.execute_command.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_handle_pick_and_place_pick_bounds_violation(self, mock_server, mock_request):
        """Test pick and place with pick position bounds violation."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data
        mock_request.json.return_value = {
            'x': 500.0,  # Beyond max_x_position (300.0)
            'y': 50.0,
            'place_x': 200.0,
            'place_y': 150.0,
            'pick_height': 5.0,
            'place_height': 2.0,
            'safe_height': 10.0,
            'feedrate': 1200.0,
            'vacuum_power': 255
        }
        
        # Setup safety manager to return violation
        mock_server.safety_manager.validate_move_command = AsyncMock(
            return_value=(False, ['X position 500.0 mm out of bounds [0.0, 300.0]'])
        )
        
        # Call handler
        response = await handle_pick_and_place(mock_request)
        
        # Verify error response
        assert response.status == 400
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'BOUNDS_VIOLATION'
        assert 'Pick position' in data['error_message']
        
        # Verify command was not executed
        mock_server.execute_command.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_handle_pick_and_place_place_bounds_violation(self, mock_server, mock_request):
        """Test pick and place with place position bounds violation."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data
        mock_request.json.return_value = {
            'x': 100.0,
            'y': 50.0,
            'place_x': 500.0,  # Beyond max_x_position (300.0)
            'place_y': 150.0,
            'pick_height': 5.0,
            'place_height': 2.0,
            'safe_height': 10.0,
            'feedrate': 1200.0,
            'vacuum_power': 255
        }
        
        # Setup safety manager to return violation
        mock_server.safety_manager.validate_move_command = AsyncMock(
            return_value=(False, ['Place position X 500.0 mm out of bounds [0.0, 300.0]'])
        )
        
        # Call handler
        response = await handle_pick_and_place(mock_request)
        
        # Verify error response
        assert response.status == 400
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'BOUNDS_VIOLATION'
        assert 'Place position' in data['error_message']
        
        # Verify command was not executed
        mock_server.execute_command.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_handle_pick_and_place_exception(self, mock_server, mock_request):
        """Test pick and place with exception."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data
        mock_request.json.return_value = {
            'x': 100.0,
            'y': 50.0,
            'place_x': 200.0,
            'place_y': 150.0,
            'pick_height': 5.0,
            'place_height': 2.0,
            'safe_height': 10.0,
            'feedrate': 1200.0,
            'vacuum_power': 255
        }
        
        # Setup mock to raise exception
        mock_server.execute_command = AsyncMock(side_effect=Exception('Pick and place failed'))
        
        # Call handler
        response = await handle_pick_and_place(mock_request)
        
        # Verify error response
        assert response.status == 500
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'EXECUTION_ERROR'
        assert 'Pick and place failed' in data['error_message']


class TestSetup:
    """Test route setup."""
    
    def test_setup(self):
        """Test that routes are registered correctly."""
        from api.routes.pnp_routes import setup
        from aiohttp import web
        
        app = web.Application()
        setup(app)
        
        # Verify routes are registered
        routes = [route.path for route in app.router.routes()]
        assert '/api/v1/pnp/pick' in routes
        assert '/api/v1/pnp/place' in routes
        assert '/api/v1/pnp/pick_and_place' in routes
