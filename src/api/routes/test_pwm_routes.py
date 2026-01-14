#!/usr/bin/env python3
# Unit tests for PWM Routes

import pytest
from aiohttp import web
from unittest.mock import Mock, AsyncMock


@pytest.fixture
def mock_server():
    """Create a mock server instance."""
    server = Mock()
    server.execute_command = AsyncMock()
    server.safety_manager = Mock()
    server.safety_manager.validate_pwm_command = AsyncMock(return_value=(True, []))
    return server


@pytest.fixture
def mock_request():
    """Create a mock request object."""
    request = Mock()
    request.json = AsyncMock()
    request.app = {'server': None}
    return request


# Import route handlers
from api.routes.pwm_routes import handle_pwm_set


class TestHandlePwmSet:
    """Test handle_pwm_set route handler."""
    
    @pytest.mark.asyncio
    async def test_handle_pwm_set_success(self, mock_server, mock_request):
        """Test successful PWM set command."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data
        mock_request.json.return_value = {
            'pin': 'PWM1',
            'value': 0.75
        }
        
        # Setup mock response
        from gcode_driver.handlers import ExecutionResult, ExecutionStatus
        mock_server.execute_command.return_value = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            gcode="SET_PIN PIN=PWM1 VALUE=0.75"
        )
        
        # Call handler
        response = await handle_pwm_set(mock_request)
        
        # Verify response
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'success'
        assert 'gcode' in data
    
    @pytest.mark.asyncio
    async def test_handle_pwm_set_missing_pin(self, mock_server, mock_request):
        """Test PWM set with missing pin parameter."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data without pin
        mock_request.json.return_value = {
            'value': 0.75
        }
        
        # Call handler
        response = await handle_pwm_set(mock_request)
        
        # Verify error response
        assert response.status == 400
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'MISSING_PARAMETER'
        assert 'Pin name is required' in data['error_message']
    
    @pytest.mark.asyncio
    async def test_handle_pwm_set_missing_value(self, mock_server, mock_request):
        """Test PWM set with missing value parameter."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data without value
        mock_request.json.return_value = {
            'pin': 'PWM1'
        }
        
        # Call handler
        response = await handle_pwm_set(mock_request)
        
        # Verify error response
        assert response.status == 400
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'MISSING_PARAMETER'
        assert 'PWM value is required' in data['error_message']
    
    @pytest.mark.asyncio
    async def test_handle_pwm_set_invalid_value(self, mock_server, mock_request):
        """Test PWM set with invalid value."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data with invalid value
        mock_request.json.return_value = {
            'pin': 'PWM1',
            'value': 1.5
        }
        
        # Setup safety manager to return violation
        mock_server.safety_manager.validate_pwm_command = AsyncMock(
            return_value=(False, ['PWM value must be a float between 0.0 and 1.0'])
        )
        
        # Call handler
        response = await handle_pwm_set(mock_request)
        
        # Verify error response
        assert response.status == 400
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'BOUNDS_VIOLATION'
    
    @pytest.mark.asyncio
    async def test_handle_pwm_set_exception(self, mock_server, mock_request):
        """Test PWM set with exception."""
        mock_request.app = {'server': mock_server}
        
        # Setup request data
        mock_request.json.return_value = {
            'pin': 'PWM1',
            'value': 0.75
        }
        
        # Setup mock to raise exception
        mock_server.execute_command = AsyncMock(side_effect=Exception('PWM set failed'))
        
        # Call handler
        response = await handle_pwm_set(mock_request)
        
        # Verify error response
        assert response.status == 500
        data = await response.json()
        assert data['status'] == 'error'
        assert data['error_code'] == 'EXECUTION_ERROR'


class TestSetup:
    """Test route setup."""
    
    def test_setup(self):
        """Test that routes are registered correctly."""
        from api.routes.pwm_routes import setup
        from aiohttp import web
        
        app = web.Application()
        setup(app)
        
        # Verify routes are registered
        routes = [route.path for route in app.router.routes()]
        assert '/api/v1/pwm/set' in routes
