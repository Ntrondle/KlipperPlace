#!/usr/bin/env python3
# Unit tests for Actuator Routes

import pytest
from aiohttp import web
from unittest.mock import Mock, AsyncMock


@pytest.fixture
def mock_server():
    """Create a mock server instance."""
    server = Mock()
    server.execute_command = AsyncMock()
    server.safety_manager = Mock()
    return server


@pytest.fixture
def mock_request():
    """Create a mock request object."""
    request = Mock()
    request.json = AsyncMock()
    request.app = {'server': None}
    return request


# Import route handlers
from api.routes.actuator_routes import handle_actuate, handle_actuator_on, handle_actuator_off


class TestHandleActuate:
    """Test handle_actuate route handler."""
    
    @pytest.mark.asyncio
    async def test_handle_actuate_success(self, mock_server, mock_request):
        """Test successful actuate command."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data
        mock_request.json.return_value = {
            'pin': 'ACT1',
            'value': 1.0
        }
        
        # Setup mock response
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        mock_server.execute_command.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            gcode="ACTUATE ACT1 VALUE=1.0"
        )
        
        # Call handler
        response = await handle_actuate(mock_request)
        
        # Verify response
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
        assert 'gcode' in data
    
    @pytest.mark.asyncio
    async def test_handle_actuate_missing_pin(self, mock_server, mock_request):
        """Test actuate with missing pin."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data without pin
        mock_request.json.return_value = {
            'value': 1.0
        }
        
        # Call handler
        response = await handle_actuate(mock_request)
        
        # Verify error response
        assert response.status == 400
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'MISSING_PARAMETER'
        assert 'Pin name is required' in data['error_message']


class TestHandleActuatorOn:
    """Test handle_actuator_on route handler."""
    
    @pytest.mark.asyncio
    async def test_handle_actuator_on_success(self, mock_server, mock_request):
        """Test successful actuator on command."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data
        mock_request.json.return_value = {
            'pin': 'ACT1'
        }
        
        # Setup mock response
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        mock_server.execute_command.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            gcode="ACTUATOR_ON ACT1"
        )
        
        # Call handler
        response = await handle_actuator_on(mock_request)
        
        # Verify response
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
        assert 'gcode' in data
    
    @pytest.mark.asyncio
    async def test_handle_actuator_on_missing_pin(self, mock_server, mock_request):
        """Test actuator on with missing pin."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data without pin
        mock_request.json.return_value = {}
        
        # Call handler
        response = await handle_actuator_on(mock_request)
        
        # Verify error response
        assert response.status == 400
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'MISSING_PARAMETER'


class TestHandleActuatorOff:
    """Test handle_actuator_off route handler."""
    
    @pytest.mark.asyncio
    async def test_handle_actuator_off_success(self, mock_server, mock_request):
        """Test successful actuator off command."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data
        mock_request.json.return_value = {
            'pin': 'ACT1'
        }
        
        # Setup mock response
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        mock_server.execute_command.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            gcode="ACTUATOR_OFF ACT1"
        )
        
        # Call handler
        response = await handle_actuator_off(mock_request)
        
        # Verify response
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
        assert 'gcode' in data
    
    @pytest.mark.asyncio
    async def test_handle_actuator_off_missing_pin(self, mock_server, mock_request):
        """Test actuator off with missing pin."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data without pin
        mock_request.json.return_value = {}
        
        # Call handler
        response = await handle_actuator_off(mock_request)
        
        # Verify error response
        assert response.status == 400
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'MISSING_PARAMETER'


class TestSetup:
    """Test route setup."""
    
    def test_setup(self):
        """Test that routes are registered correctly."""
        from api.routes.actuator_routes import setup
        from aiohttp import web
        
        app = web.Application()
        setup(app)
        
        # Verify routes are registered
        routes = [route.path for route in app.router.routes()]
        assert '/api/v1/actuators/actuate' in routes
        assert '/api/v1/actuators/on' in routes
        assert '/api/v1/actuators/off' in routes
