#!/usr/bin/env python3
# Unit tests for Sensor Routes

import pytest
from aiohttp import web
from unittest.mock import Mock, AsyncMock


@pytest.fixture
def mock_server():
    """Create a mock server instance."""
    server = Mock()
    server.execute_command = AsyncMock()
    server.safety_manager = Mock()
    server.safety_manager.validate_sensor_command = AsyncMock(return_value=(True, []))
    return server


@pytest.fixture
def mock_request():
    """Create a mock request object."""
    request = Mock()
    request.json = AsyncMock()
    request.app = {'server': None}
    return request


# Import route handlers
from api.routes.sensor_routes import handle_sensor_read


class TestHandleSensorRead:
    """Test handle_sensor_read route handler."""
    
    @pytest.mark.asyncio
    async def test_handle_sensor_read_success(self, mock_server, mock_request):
        """Test successful sensor read command."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data
        mock_request.json.return_value = {}
        
        # Setup mock response
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        mock_server.execute_command.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            gcode="SENSOR_READ",
            response={
                'sensors': {
                    'temperature_sensor': {'temperature': 25.5},
                    'pressure_sensor': {'pressure': 101.3}
                }
            }
        )
        
        # Call handler
        response = await handle_sensor_read(mock_request)
        
        # Verify response
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
        assert 'gcode' in data
        assert 'sensors' in data
    
    @pytest.mark.asyncio
    async def test_handle_sensor_read_specific_sensor(self, mock_server, mock_request):
        """Test sensor read for specific sensor."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data with specific sensor
        mock_request.json.return_value = {
            'sensor': 'temperature_sensor'
        }
        
        # Setup mock response
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        mock_server.execute_command.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            gcode="SENSOR_READ SENSOR=temperature_sensor",
            response={
                'sensors': {
                    'temperature_sensor': {'temperature': 25.5}
                }
            }
        )
        
        # Call handler
        response = await handle_sensor_read(mock_request)
        
        # Verify response
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
    
    @pytest.mark.asyncio
    async def test_handle_sensor_read_with_timestamp(self, mock_server, mock_request):
        """Test sensor read with timestamp."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data with timestamp flag
        mock_request.json.return_value = {
            'include_timestamp': True
        }
        
        # Setup mock response
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        mock_server.execute_command.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            gcode="SENSOR_READ INCLUDE_TIMESTAMP=1",
            response={
                'sensors': {
                    'temperature_sensor': {'temperature': 25.5}
                },
                'timestamp': 1234567890.0
            }
        )
        
        # Call handler
        response = await handle_sensor_read(mock_request)
        
        # Verify response
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
        assert 'timestamp' in data
    
    @pytest.mark.asyncio
    async def test_handle_sensor_read_exception(self, mock_server, mock_request):
        """Test sensor read with exception."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data
        mock_request.json.return_value = {}
        
        # Setup mock to raise exception
        mock_server.execute_command = AsyncMock(side_effect=Exception('Sensor read failed'))
        
        # Call handler
        response = await handle_sensor_read(mock_request)
        
        # Verify error response
        assert response.status == 500
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'EXECUTION_ERROR'


class TestSetup:
    """Test route setup."""
    
    def test_setup(self):
        """Test that routes are registered correctly."""
        from api.routes.sensor_routes import setup
        from aiohttp import web
        
        app = web.Application()
        setup(app)
        
        # Verify routes are registered
        routes = [route.path for route in app.router.routes()]
        assert '/api/v1/sensors/read' in routes
