#!/usr/bin/env python3
# Unit tests for GPIO Routes

import pytest
from aiohttp import web
from unittest.mock import Mock, AsyncMock


@pytest.fixture
def mock_server():
    """Create a mock server instance."""
    server = Mock()
    server.execute_command = AsyncMock()
    server.safety_manager = Mock()
    server.safety_manager.validate_gpio_command = AsyncMock(return_value=(True, []))
    return server


@pytest.fixture
def mock_request():
    """Create a mock request object."""
    request = Mock()
    request.json = AsyncMock()
    request.app = {'server': None}
    return request


# Import route handlers
from api.routes.gpio_routes import handle_gpio_read, handle_gpio_write


class TestHandleGpioRead:
    """Test handle_gpio_read route handler."""
    
    @pytest.mark.asyncio
    async def test_handle_gpio_read_success(self, mock_server, mock_request):
        """Test successful GPIO read command."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data
        mock_request.json.return_value = {}
        
        # Setup mock response
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        mock_server.execute_command.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            gcode="GPIO_READ",
            response={'gpio_states': {'GPIO1': 1, 'GPIO2': 0}}
        )
        
        # Call handler
        response = await handle_gpio_read(mock_request)
        
        # Verify response
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
        assert 'gcode' in data
        assert 'gpio_states' in data
    
    @pytest.mark.asyncio
    async def test_handle_gpio_read_specific_pin(self, mock_server, mock_request):
        """Test GPIO read for specific pin."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data with specific pin
        mock_request.json.return_value = {
            'pin': 'GPIO1'
        }
        
        # Setup mock response
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        mock_server.execute_command.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            gcode="GPIO_READ PIN=GPIO1",
            response={'gpio_states': {'GPIO1': 1}}
        )
        
        # Call handler
        response = await handle_gpio_read(mock_request)
        
        # Verify response
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
    
    @pytest.mark.asyncio
    async def test_handle_gpio_read_exception(self, mock_server, mock_request):
        """Test GPIO read with exception."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data
        mock_request.json.return_value = {}
        
        # Setup mock to raise exception
        mock_server.execute_command = AsyncMock(side_effect=Exception('GPIO read failed'))
        
        # Call handler
        response = await handle_gpio_read(mock_request)
        
        # Verify error response
        assert response.status == 500
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'EXECUTION_ERROR'


class TestHandleGpioWrite:
    """Test handle_gpio_write route handler."""
    
    @pytest.mark.asyncio
    async def test_handle_gpio_write_success(self, mock_server, mock_request):
        """Test successful GPIO write command."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data
        mock_request.json.return_value = {
            'pin': 'GPIO1',
            'value': 1
        }
        
        # Setup mock response
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        mock_server.execute_command.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            gcode="GPIO_WRITE PIN=GPIO1 VALUE=1"
        )
        
        # Call handler
        response = await handle_gpio_write(mock_request)
        
        # Verify response
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
        assert 'gcode' in data
    
    @pytest.mark.asyncio
    async def test_handle_gpio_write_missing_pin(self, mock_server, mock_request):
        """Test GPIO write with missing pin parameter."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data without pin
        mock_request.json.return_value = {
            'value': 1
        }
        
        # Call handler
        response = await handle_gpio_write(mock_request)
        
        # Verify error response
        assert response.status == 400
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'MISSING_PARAMETER'
        assert 'Pin name is required' in data['error_message']
    
    @pytest.mark.asyncio
    async def test_handle_gpio_write_missing_value(self, mock_server, mock_request):
        """Test GPIO write with missing value parameter."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data without value
        mock_request.json.return_value = {
            'pin': 'GPIO1'
        }
        
        # Call handler
        response = await handle_gpio_write(mock_request)
        
        # Verify error response
        assert response.status == 400
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'MISSING_PARAMETER'
        assert 'Value is required' in data['error_message']
    
    @pytest.mark.asyncio
    async def test_handle_gpio_write_invalid_value(self, mock_server, mock_request):
        """Test GPIO write with invalid value."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data with invalid value
        mock_request.json.return_value = {
            'pin': 'GPIO1',
            'value': 2
        }
        
        # Setup safety manager to return violation
        mock_server.safety_manager.validate_gpio_command = AsyncMock(
            return_value=(False, ['Value must be 0 or 1'])
        )
        
        # Call handler
        response = await handle_gpio_write(mock_request)
        
        # Verify error response
        assert response.status == 400
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'BOUNDS_VIOLATION'
    
    @pytest.mark.asyncio
    async def test_handle_gpio_write_exception(self, mock_server, mock_request):
        """Test GPIO write with exception."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data
        mock_request.json.return_value = {
            'pin': 'GPIO1',
            'value': 1
        }
        
        # Setup mock to raise exception
        mock_server.execute_command = AsyncMock(side_effect=Exception('GPIO write failed'))
        
        # Call handler
        response = await handle_gpio_write(mock_request)
        
        # Verify error response
        assert response.status == 500
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'EXECUTION_ERROR'


class TestSetup:
    """Test route setup."""
    
    def test_setup(self):
        """Test that routes are registered correctly."""
        from api.routes.gpio_routes import setup
        from aiohttp import web
        
        app = web.Application()
        setup(app)
        
        # Verify routes are registered
        routes = [route.path for route in app.router.routes()]
        assert '/api/v1/gpio/read' in routes
        assert '/api/v1/gpio/write' in routes
