#!/usr/bin/env python3
# Unit tests for Fan Routes

import pytest
from aiohttp import web
from unittest.mock import Mock, AsyncMock


@pytest.fixture
def mock_server():
    """Create a mock server instance."""
    server = Mock()
    server.execute_command = AsyncMock()
    server.safety_manager = Mock()
    server.safety_manager.validate_fan_command = AsyncMock(return_value=(True, []))
    return server


@pytest.fixture
def mock_request():
    """Create a mock request object."""
    request = Mock()
    request.json = AsyncMock()
    request.app = {'server': None}
    return request


# Import route handlers
from api.routes.fan_routes import handle_fan_on, handle_fan_off, handle_fan_set


class TestHandleFanOn:
    """Test handle_fan_on route handler."""
    
    @pytest.mark.asyncio
    async def test_handle_fan_on_success(self, mock_server, mock_request):
        """Test successful fan on command."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data
        mock_request.json.return_value = {
            'fan': 'fan',
            'speed': 0.75
        }
        
        # Setup mock response
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        mock_server.execute_command.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            gcode="FAN_ON FAN=0.75"
        )
        
        # Call handler
        response = await handle_fan_on(mock_request)
        
        # Verify response
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
        assert 'gcode' in data
    
    @pytest.mark.asyncio
    async def test_handle_fan_on_invalid_speed(self, mock_server, mock_request):
        """Test fan on with invalid speed."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data with invalid speed
        mock_request.json.return_value = {
            'fan': 'fan',
            'speed': 1.5
        }
        
        # Setup safety manager to return violation
        mock_server.safety_manager.validate_fan_command = AsyncMock(
            return_value=(False, ['Speed must be a float between 0.0 and 1.0'])
        )
        
        # Call handler
        response = await handle_fan_on(mock_request)
        
        # Verify error response
        assert response.status == 400
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'BOUNDS_VIOLATION'
    
    @pytest.mark.asyncio
    async def test_handle_fan_on_exception(self, mock_server, mock_request):
        """Test fan on with exception."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data
        mock_request.json.return_value = {
            'fan': 'fan',
            'speed': 0.75
        }
        
        # Setup mock to raise exception
        mock_server.execute_command = AsyncMock(side_effect=Exception('Fan on failed'))
        
        # Call handler
        response = await handle_fan_on(mock_request)
        
        # Verify error response
        assert response.status == 500
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'EXECUTION_ERROR'


class TestHandleFanOff:
    """Test handle_fan_off route handler."""
    
    @pytest.mark.asyncio
    async def test_handle_fan_off_success(self, mock_server, mock_request):
        """Test successful fan off command."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data
        mock_request.json.return_value = {
            'fan': 'fan'
        }
        
        # Setup mock response
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        mock_server.execute_command.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            gcode="FAN_OFF FAN=fan"
        )
        
        # Call handler
        response = await handle_fan_off(mock_request)
        
        # Verify response
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
        assert 'gcode' in data
    
    @pytest.mark.asyncio
    async def test_handle_fan_off_exception(self, mock_server, mock_request):
        """Test fan off with exception."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data
        mock_request.json.return_value = {
            'fan': 'fan'
        }
        
        # Setup mock to raise exception
        mock_server.execute_command = AsyncMock(side_effect=Exception('Fan off failed'))
        
        # Call handler
        response = await handle_fan_off(mock_request)
        
        # Verify error response
        assert response.status == 500
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'EXECUTION_ERROR'


class TestHandleFanSet:
    """Test handle_fan_set route handler."""
    
    @pytest.mark.asyncio
    async def test_handle_fan_set_success(self, mock_server, mock_request):
        """Test successful fan set command."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data
        mock_request.json.return_value = {
            'fan': 'fan',
            'speed': 0.5
        }
        
        # Setup mock response
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        mock_server.execute_command.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            gcode="FAN_SET FAN=0.5"
        )
        
        # Call handler
        response = await handle_fan_set(mock_request)
        
        # Verify response
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
        assert 'gcode' in data
    
    @pytest.mark.asyncio
    async def test_handle_fan_set_missing_fan(self, mock_server, mock_request):
        """Test fan set with missing fan parameter."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data without fan
        mock_request.json.return_value = {
            'speed': 0.5
        }
        
        # Call handler
        response = await handle_fan_set(mock_request)
        
        # Verify error response
        assert response.status == 400
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'MISSING_PARAMETER'
        assert 'Fan name is required' in data['error_message']
    
    @pytest.mark.asyncio
    async def test_handle_fan_set_missing_speed(self, mock_server, mock_request):
        """Test fan set with missing speed parameter."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data without speed
        mock_request.json.return_value = {
            'fan': 'fan'
        }
        
        # Call handler
        response = await handle_fan_set(mock_request)
        
        # Verify error response
        assert response.status == 400
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'MISSING_PARAMETER'
        assert 'Speed value is required' in data['error_message']
    
    @pytest.mark.asyncio
    async def test_handle_fan_set_invalid_speed(self, mock_server, mock_request):
        """Test fan set with invalid speed."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data with invalid speed
        mock_request.json.return_value = {
            'fan': 'fan',
            'speed': -0.5
        }
        
        # Setup safety manager to return violation
        mock_server.safety_manager.validate_fan_command = AsyncMock(
            return_value=(False, ['Speed must be a float between 0.0 and 1.0'])
        )
        
        # Call handler
        response = await handle_fan_set(mock_request)
        
        # Verify error response
        assert response.status == 400
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'BOUNDS_VIOLATION'


class TestSetup:
    """Test route setup."""
    
    def test_setup(self):
        """Test that routes are registered correctly."""
        from api.routes.fan_routes import setup
        from aiohttp import web
        
        app = web.Application()
        setup(app)
        
        # Verify routes are registered
        routes = [route.path for route in app.router.routes()]
        assert '/api/v1/fans/on' in routes
        assert '/api/v1/fans/off' in routes
        assert '/api/v1/fans/set' in routes
