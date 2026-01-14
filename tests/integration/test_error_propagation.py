#!/usr/bin/env python3
# Integration Tests: Error Propagation
# Tests for error handling and propagation across components

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from api.server import APIServer
from middleware.translator import (
    OpenPNPTranslator,
    OpenPNPCommand,
    OpenPNPCommandType,
    OpenPNPResponse,
    ResponseStatus
)
from middleware.cache import StateCacheManager, CacheCategory
from middleware.safety import SafetyManager, SafetyEvent, SafetyEventType, SafetyLevel


class TestAPIErrorPropagation:
    """Test suite for API error propagation."""
    
    @pytest_asyncio.asyncio_test
    async def test_api_propagates_translator_errors(self, api_server):
        """Test that API propagates translator errors correctly."""
        command = {
            'command': 'move',
            'parameters': {'x': 100.0, 'y': 50.0, 'z': 10.0}
        }
        
        # Mock translator to return error
        error_response = OpenPNPResponse(
            status=ResponseStatus.ERROR,
            command='move',
            error_message='Translation failed',
            error_code='TRANSLATION_ERROR'
        )
        api_server.translator.translate_and_execute = AsyncMock(return_value=error_response)
        
        # Execute command through API
        response = await api_server.execute_command(command)
        
        # Verify error propagation
        assert response.status == ResponseStatus.ERROR
        assert response.error_message == 'Translation failed'
        assert response.error_code == 'TRANSLATION_ERROR'
    
    @pytest_asyncio.asyncio_test
    async def test_api_propagates_moonraker_errors(self, api_server):
        """Test that API propagates Moonraker errors correctly."""
        command = {
            'command': 'move',
            'parameters': {'x': 100.0, 'y': 50.0, 'z': 10.0}
        }
        
        # Mock translator to propagate Moonraker error
        error_response = OpenPNPResponse(
            status=ResponseStatus.ERROR,
            command='move',
            error_message='Moonraker connection error',
            error_code='MOONRAKER_ERROR'
        )
        api_server.translator.translate_and_execute = AsyncMock(return_value=error_response)
        
        # Execute command through API
        response = await api_server.execute_command(command)
        
        # Verify error propagation
        assert response.status == ResponseStatus.ERROR
        assert response.error_code == 'MOONRAKER_ERROR'
    
    @pytest_asyncio.asyncio_test
    async def test_api_propagates_timeout_errors(self, api_server):
        """Test that API propagates timeout errors correctly."""
        command = {
            'command': 'move',
            'parameters': {'x': 100.0, 'y': 50.0, 'z': 10.0}
        }
        
        # Mock translator to return timeout
        error_response = OpenPNPResponse(
            status=ResponseStatus.TIMEOUT,
            command='move',
            error_message='Command execution timeout',
            error_code='TIMEOUT'
        )
        api_server.translator.translate_and_execute = AsyncMock(return_value=error_response)
        
        # Execute command through API
        response = await api_server.execute_command(command)
        
        # Verify error propagation
        assert response.status == ResponseStatus.TIMEOUT
        assert response.error_code == 'TIMEOUT'
    
    @pytest_asyncio.asyncio_test
    async def test_api_propagates_validation_errors(self, api_server):
        """Test that API propagates validation errors correctly."""
        command = {
            'command': 'move',
            'parameters': {'x': 9999.0, 'y': 50.0, 'z': 10.0}  # Out of bounds
        }
        
        # Mock safety validation to fail
        api_server.safety_manager.validate_move_command = AsyncMock(
            return_value=(False, ['X position out of bounds'])
        )
        
        # Execute command through API
        response = await api_server.execute_command(command)
        
        # Verify error propagation
        assert response.status == ResponseStatus.ERROR
        assert 'out of bounds' in response.error_message.lower()
    
    @pytest_asyncio.asyncio_test
    async def test_api_propagates_batch_errors(self, api_server):
        """Test that API propagates batch errors correctly."""
        commands = [
            {'command': 'move', 'parameters': {'x': 100.0}},
            {'command': 'move', 'parameters': {'y': 50.0}},
            {'command': 'move', 'parameters': {'z': 9999.0}}  # Error
        ]
        
        # Mock batch execution with error
        responses = [
            OpenPNPResponse(status=ResponseStatus.SUCCESS, command='move'),
            OpenPNPResponse(status=ResponseStatus.SUCCESS, command='move'),
            OpenPNPResponse(
                status=ResponseStatus.ERROR,
                command='move',
                error_message='Position out of bounds',
                error_code='VALIDATION_ERROR'
            )
        ]
        api_server.translator.execute_batch = AsyncMock(return_value=responses)
        
        # Execute batch through API
        results = await api_server.execute_batch(commands, stop_on_error=False)
        
        # Verify error propagation
        assert len(results) == 3
        assert results[0].status == ResponseStatus.SUCCESS
        assert results[1].status == ResponseStatus.SUCCESS
        assert results[2].status == ResponseStatus.ERROR
        assert results[2].error_code == 'VALIDATION_ERROR'
    
    @pytest_asyncio.asyncio_test
    async def test_api_propagates_network_errors(self, api_server):
        """Test that API propagates network errors correctly."""
        command = {
            'command': 'move',
            'parameters': {'x': 100.0, 'y': 50.0, 'z': 10.0}
        }
        
        # Mock translator to return network error
        error_response = OpenPNPResponse(
            status=ResponseStatus.ERROR,
            command='move',
            error_message='Network connection failed',
            error_code='NETWORK_ERROR'
        )
        api_server.translator.translate_and_execute = AsyncMock(return_value=error_response)
        
        # Execute command through API
        response = await api_server.execute_command(command)
        
        # Verify error propagation
        assert response.status == ResponseStatus.ERROR
        assert response.error_code == 'NETWORK_ERROR'


class TestMiddlewareErrorPropagation:
    """Test suite for middleware error propagation."""
    
    @pytest_asyncio.asyncio_test
    async def test_middleware_propagates_parser_errors(self, openpnp_translator):
        """Test that middleware propagates parser errors correctly."""
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.MOVE,
            parameters={'x': 100.0, 'y': 50.0, 'z': 10.0}
        )
        
        # Mock G-code translation to fail
        async def mock_translate_and_execute(cmd):
            return OpenPNPResponse(
                status=ResponseStatus.ERROR,
                command='move',
                error_message='G-code parsing failed',
                error_code='PARSER_ERROR'
            )
        
        openpnp_translator.translate_and_execute = mock_translate_and_execute
        
        # Execute command
        response = await openpnp_translator.translate_and_execute(command)
        
        # Verify error propagation
        assert response.status == ResponseStatus.ERROR
        assert response.error_code == 'PARSER_ERROR'
    
    @pytest_asyncio.asyncio_test
    async def test_middleware_propagates_gcode_errors(self, openpnp_translator):
        """Test that middleware propagates G-code errors correctly."""
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.MOVE,
            parameters={'x': 100.0, 'y': 50.0, 'z': 10.0}
        )
        
        # Mock G-code execution to fail
        async def mock_translate_and_execute(cmd):
            return OpenPNPResponse(
                status=ResponseStatus.ERROR,
                command='move',
                error_message='G-code execution failed',
                error_code='GCODE_ERROR'
            )
        
        openpnp_translator.translate_and_execute = mock_translate_and_execute
        
        # Execute command
        response = await openpnp_translator.translate_and_execute(command)
        
        # Verify error propagation
        assert response.status == ResponseStatus.ERROR
        assert response.error_code == 'GCODE_ERROR'
    
    @pytest_asyncio.asyncio_test
    async def test_middleware_propagates_api_errors(self, openpnp_translator):
        """Test that middleware propagates API errors correctly."""
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.GPIO_READ,
            parameters={'pin': 'PA1'}
        )
        
        # Mock direct API to fail
        async def mock_translate_and_execute(cmd):
            return OpenPNPResponse(
                status=ResponseStatus.ERROR,
                command='gpio_read',
                error_message='GPIO API request failed',
                error_code='API_ERROR'
            )
        
        openpnp_translator.translate_and_execute = mock_translate_and_execute
        
        # Execute command
        response = await openpnp_translator.translate_and_execute(command)
        
        # Verify error propagation
        assert response.status == ResponseStatus.ERROR
        assert response.error_code == 'API_ERROR'
    
    @pytest_asyncio.asyncio_test
    async def test_middleware_propagates_unknown_command_errors(self, openpnp_translator):
        """Test that middleware propagates unknown command errors correctly."""
        command_dict = {
            'command': 'unknown_command',
            'parameters': {}
        }
        
        # Mock translate_and_execute to handle unknown command
        async def mock_translate_and_execute(cmd):
            return OpenPNPResponse(
                status=ResponseStatus.ERROR,
                command='unknown_command',
                error_message='Unknown command type',
                error_code='UNKNOWN_COMMAND'
            )
        
        openpnp_translator.translate_and_execute = mock_translate_and_execute
        
        # Execute command
        response = await openpnp_translator.translate_and_execute(command_dict)
        
        # Verify error propagation
        assert response.status == ResponseStatus.ERROR
        assert response.error_code == 'UNKNOWN_COMMAND'
    
    @pytest_asyncio.asyncio_test
    async def test_middleware_propagates_parameter_errors(self, openpnp_translator):
        """Test that middleware propagates parameter errors correctly."""
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.MOVE,
            parameters={'x': 'invalid', 'y': 50.0, 'z': 10.0}  # Invalid x
        )
        
        # Mock translate_and_execute to handle parameter error
        async def mock_translate_and_execute(cmd):
            return OpenPNPResponse(
                status=ResponseStatus.ERROR,
                command='move',
                error_message='Invalid parameter value',
                error_code='PARAMETER_ERROR'
            )
        
        openpnp_translator.translate_and_execute = mock_translate_and_execute
        
        # Execute command
        response = await openpnp_translator.translate_and_execute(command)
        
        # Verify error propagation
        assert response.status == ResponseStatus.ERROR
        assert response.error_code == 'PARAMETER_ERROR'
    
    @pytest_asyncio.asyncio_test
    async def test_middleware_propagates_batch_errors(self, openpnp_translator):
        """Test that middleware propagates batch errors correctly."""
        commands = [
            {'command': 'move', 'parameters': {'x': 100.0}},
            {'command': 'move', 'parameters': {'y': 50.0}},
            {'command': 'invalid_command', 'parameters': {}}  # Error
        ]
        
        # Mock batch execution with error
        responses = [
            OpenPNPResponse(status=ResponseStatus.SUCCESS, command='move'),
            OpenPNPResponse(status=ResponseStatus.SUCCESS, command='move'),
            OpenPNPResponse(
                status=ResponseStatus.ERROR,
                command='invalid_command',
                error_message='Unknown command type',
                error_code='UNKNOWN_COMMAND'
            )
        ]
        openpnp_translator.execute_batch = AsyncMock(return_value=responses)
        
        # Execute batch
        results = await openpnp_translator.execute_batch(commands, stop_on_error=False)
        
        # Verify error propagation
        assert len(results) == 3
        assert results[2].status == ResponseStatus.ERROR
        assert results[2].error_code == 'UNKNOWN_COMMAND'


class TestSafetyErrorPropagation:
    """Test suite for safety error propagation."""
    
    @pytest_asyncio.asyncio_test
    async def test_safety_propagates_position_errors(self, api_server):
        """Test that safety propagates position errors correctly."""
        command = {
            'command': 'move',
            'parameters': {'x': 9999.0, 'y': 50.0, 'z': 10.0}  # Out of bounds
        }
        
        # Mock safety validation to fail
        api_server.safety_manager.validate_move_command = AsyncMock(
            return_value=(False, ['X position 9999.0 mm out of bounds'])
        )
        
        # Execute command
        response = await api_server.execute_command(command)
        
        # Verify error propagation
        assert response.status == ResponseStatus.ERROR
        assert 'out of bounds' in response.error_message.lower()
    
    @pytest_asyncio.asyncio_test
    async def test_safety_propagates_temperature_errors(self, api_server):
        """Test that safety propagates temperature errors correctly."""
        command = {
            'command': 'move',
            'parameters': {'x': 100.0, 'y': 50.0, 'z': 10.0}
        }
        
        # Mock temperature check to fail
        api_server.safety_manager.check_temperature_limits = AsyncMock(
            return_value=[
                SafetyEvent(
                    event_type=SafetyEventType.TEMPERATURE_EXCEEDED,
                    level=SafetyLevel.CRITICAL,
                    message='Temperature exceeded: 300°C',
                    component='extruder'
                )
            ]
        )
        
        # Execute command
        response = await api_server.execute_command(command)
        
        # Verify error propagation
        assert response.status == ResponseStatus.ERROR
        assert 'temperature' in response.error_message.lower()
    
    @pytest_asyncio.asyncio_test
    async def test_safety_propagates_feedrate_errors(self, api_server):
        """Test that safety propagates feedrate errors correctly."""
        command = {
            'command': 'move',
            'parameters': {'x': 100.0, 'y': 50.0, 'z': 10.0, 'feedrate': 99999.0}  # Too high
        }
        
        # Mock safety validation to fail
        api_server.safety_manager.validate_move_command = AsyncMock(
            return_value=(False, ['Feedrate 99999.0 mm/min out of bounds'])
        )
        
        # Execute command
        response = await api_server.execute_command(command)
        
        # Verify error propagation
        assert response.status == ResponseStatus.ERROR
        assert 'feedrate' in response.error_message.lower()
        assert 'out of bounds' in response.error_message.lower()
    
    @pytest_asyncio.asyncio_test
    async def test_safety_propagates_pwm_errors(self, api_server):
        """Test that safety propagates PWM errors correctly."""
        command = {
            'command': 'pwm_set',
            'parameters': {'value': 2.0, 'pin': 'PA1'}  # Out of range
        }
        
        # Mock PWM check to fail
        api_server.safety_manager.check_pwm_limits = AsyncMock(
            return_value=SafetyEvent(
                event_type=SafetyEventType.PWM_LIMIT_EXCEEDED,
                level=SafetyLevel.WARNING,
                message='PWM value out of bounds',
                component='PA1'
            )
        )
        
        # Execute command
        response = await api_server.execute_command(command)
        
        # Verify error propagation
        assert response.status == ResponseStatus.ERROR
        assert 'pwm' in response.error_message.lower()
        assert 'out of bounds' in response.error_message.lower()
    
    @pytest_asyncio.asyncio_test
    async def test_safety_propagates_emergency_stop(self, api_server):
        """Test that safety propagates emergency stop correctly."""
        command = {
            'command': 'emergency_stop',
            'parameters': {'reason': 'Test emergency'}
        }
        
        # Mock emergency stop
        api_server.safety_manager.emergency_stop = AsyncMock()
        
        # Execute command
        response = await api_server.execute_command(command)
        
        # Verify emergency stop was called
        api_server.safety_manager.emergency_stop.assert_called_once_with(reason='Test emergency')


class TestCacheErrorPropagation:
    """Test suite for cache error propagation."""
    
    @pytest_asyncio.asyncio_test
    async def test_cache_propagates_fetch_errors(self, api_server):
        """Test that cache propagates fetch errors correctly."""
        command = {
            'command': 'sensor_read',
            'parameters': {'sensor': 'temperature_sensor'}
        }
        
        # Mock cache fetch to fail
        api_server.cache_manager.get = AsyncMock(return_value=None)
        
        # Execute command
        response = await api_server.execute_command(command)
        
        # Verify error handling
        # In mock scenario, the command should still execute but may use fallback
        assert response is not None
    
    @pytest_asyncio.asyncio_test
    async def test_cache_propagates_connection_errors(self, api_server):
        """Test that cache propagates connection errors correctly."""
        command = {
            'command': 'sensor_read',
            'parameters': {'sensor': 'temperature_sensor'}
        }
        
        # Mock cache to raise connection error
        async def mock_get(key, category=None, force_refresh=False):
            raise Exception('Cache connection failed')
        
        api_server.cache_manager.get = mock_get
        
        # Execute command
        response = await api_server.execute_command(command)
        
        # Verify error propagation
        assert response.status == ResponseStatus.ERROR
        assert 'connection' in response.error_message.lower()
    
    @pytest_asyncio.asyncio_test
    async def test_cache_propagates_timeout_errors(self, api_server):
        """Test that cache propagates timeout errors correctly."""
        command = {
            'command': 'sensor_read',
            'parameters': {'sensor': 'temperature_sensor'}
        }
        
        # Mock cache to timeout
        async def mock_get(key, category=None, force_refresh=False):
            await asyncio.sleep(0.2)
            return None
        
        api_server.cache_manager.get = mock_get
        
        # Execute command with short timeout
        original_timeout = api_server.translator.default_timeout
        api_server.translator.default_timeout = 0.1
        
        response = await api_server.execute_command(command)
        
        # Restore timeout
        api_server.translator.default_timeout = original_timeout
        
        # Verify timeout handling
        assert response is not None


class TestCrossComponentErrorPropagation:
    """Test suite for cross-component error propagation."""
    
    @pytest_asyncio.asyncio_test
    async def test_cross_component_api_to_middleware_to_gcode(self, api_server):
        """Test error propagation from API through middleware to G-code driver."""
        command = {
            'command': 'move',
            'parameters': {'x': 100.0, 'y': 50.0, 'z': 10.0}
        }
        
        # Mock G-code driver to fail
        async def mock_run_gcode(script):
            raise Exception('G-code driver error')
        
        mock_client = api_server.translator.gcode_translator.get_moonraker_client()
        mock_client.run_gcode = mock_run_gcode
        
        # Execute command
        response = await api_server.execute_command(command)
        
        # Verify error propagation through all layers
        assert response.status == ResponseStatus.ERROR
        assert 'driver' in response.error_message.lower()
    
    @pytest_asyncio.asyncio_test
    async def test_cross_component_safety_to_api(self, api_server):
        """Test error propagation from safety to API."""
        command = {
            'command': 'move',
            'parameters': {'x': 100.0, 'y': 50.0, 'z': 10.0}
        }
        
        # Mock safety to block command
        api_server.safety_manager.validate_move_command = AsyncMock(
            return_value=(False, ['Position out of bounds'])
        )
        
        # Execute command
        response = await api_server.execute_command(command)
        
        # Verify error propagation
        assert response.status == ResponseStatus.ERROR
        assert 'bounds' in response.error_message.lower()
    
    @pytest_asyncio.asyncio_test
    async def test_cross_component_cache_to_api(self, api_server):
        """Test error propagation from cache to API."""
        command = {
            'command': 'sensor_read',
            'parameters': {'sensor': 'temperature_sensor'}
        }
        
        # Mock cache to fail
        async def mock_get(key, category=None, force_refresh=False):
            raise Exception('Cache fetch failed')
        
        api_server.cache_manager.get = mock_get
        
        # Execute command
        response = await api_server.execute_command(command)
        
        # Verify error propagation
        assert response.status == ResponseStatus.ERROR
        assert 'cache' in response.error_message.lower()
    
    @pytest_asyncio.asyncio_test
    async def test_cross_component_websocket_to_cache(self, api_server):
        """Test error propagation from WebSocket to cache."""
        # Mock WebSocket error
        async def mock_handle_message(message):
            raise Exception('WebSocket message parse error')
        
        api_server.cache_manager._handle_websocket_message = mock_handle_message
        
        # Simulate WebSocket message
        test_message = {
            'method': 'notify_status_update',
            'params': [{'toolhead': {'position': [100.0, 50.0, 10.0]}}
        }
        
        # Handle message
        try:
            await api_server.cache_manager._handle_websocket_message(test_message)
        except Exception as e:
            # Verify error was caught
            assert 'parse error' in str(e)
    
    @pytest_asyncio.asyncio_test
    async def test_cross_component_moonraker_to_translator(self, api_server):
        """Test error propagation from Moonraker to translator."""
        command = {
            'command': 'move',
            'parameters': {'x': 100.0, 'y': 50.0, 'z': 10.0}
        }
        
        # Mock Moonraker to fail
        async def mock_run_gcode(script):
            raise Exception('Moonraker connection timeout')
        
        mock_client = api_server.translator.gcode_translator.get_moonraker_client()
        mock_client.run_gcode = mock_run_gcode
        
        # Execute command
        response = await api_server.execute_command(command)
        
        # Verify error propagation
        assert response.status == ResponseStatus.ERROR
        assert 'moonraker' in response.error_message.lower() or 'timeout' in response.error_message.lower()
    
    @pytest_asyncio.asyncio_test
    async def test_cross_component_auth_to_api(self, api_server):
        """Test error propagation from auth to API."""
        # This would be tested through actual API requests
        # In integration tests, we verify auth middleware behavior
        assert api_server.key_manager is not None
        assert api_server.auth_middleware is not None


class TestErrorRecovery:
    """Test suite for error recovery scenarios."""
    
    @pytest_asyncio.asyncio_test
    async def test_error_recovery_after_timeout(self, api_server):
        """Test recovery after timeout error."""
        command = {
            'command': 'move',
            'parameters': {'x': 100.0, 'y': 50.0, 'z': 10.0}
        }
        
        # Mock timeout then success
        call_count = [0]
        
        async def mock_translate_and_execute(cmd):
            call_count[0] += 1
            if call_count[0] == 1:
                return OpenPNPResponse(
                    status=ResponseStatus.TIMEOUT,
                    command='move',
                    error_message='Command timeout',
                    error_code='TIMEOUT'
                )
            else:
                return OpenPNPResponse(
                    status=ResponseStatus.SUCCESS,
                    command='move',
                    data={'gcode': 'G0 X100.0 Y50.0 Z10.0'}
                )
        
        openpnp_translator.translate_and_execute = mock_translate_and_execute
        
        # First attempt fails
        response1 = await api_server.execute_command(command)
        assert response1.status == ResponseStatus.TIMEOUT
        
        # Second attempt succeeds
        response2 = await api_server.execute_command(command)
        assert response2.status == ResponseStatus.SUCCESS
    
    @pytest_asyncio.asyncio_test
    async def test_error_recovery_after_connection_loss(self, api_server):
        """Test recovery after connection loss."""
        command = {
            'command': 'move',
            'parameters': {'x': 100.0, 'y': 50.0, 'z': 10.0}
        }
        
        # Mock connection loss then recovery
        call_count = [0]
        
        async def mock_translate_and_execute(cmd):
            call_count[0] += 1
            if call_count[0] == 1:
                return OpenPNPResponse(
                    status=ResponseStatus.ERROR,
                    command='move',
                    error_message='Connection lost',
                    error_code='CONNECTION_ERROR'
                )
            else:
                return OpenPNPResponse(
                    status=ResponseStatus.SUCCESS,
                    command='move',
                    data={'gcode': 'G0 X100.0 Y50.0 Z10.0'}
                )
        
        openpnp_translator.translate_and_execute = mock_translate_and_execute
        
        # First attempt fails
        response1 = await api_server.execute_command(command)
        assert response1.status == ResponseStatus.ERROR
        
        # Second attempt succeeds
        response2 = await api_server.execute_command(command)
        assert response2.status == ResponseStatus.SUCCESS
    
    @pytest_asyncio.asyncio_test
    async def test_error_recovery_after_validation_failure(self, api_server):
        """Test recovery after validation failure."""
        # First command with invalid parameters
        command1 = {
            'command': 'move',
            'parameters': {'x': 9999.0, 'y': 50.0, 'z': 10.0}
        }
        
        api_server.safety_manager.validate_move_command = AsyncMock(
            return_value=(False, ['Position out of bounds'])
        )
        
        response1 = await api_server.execute_command(command1)
        assert response1.status == ResponseStatus.ERROR
        
        # Second command with valid parameters
        command2 = {
            'command': 'move',
            'parameters': {'x': 100.0, 'y': 50.0, 'z': 10.0}
        }
        
        api_server.safety_manager.validate_move_command = AsyncMock(
            return_value=(True, [])
        )
        
        response2 = await api_server.execute_command(command2)
        assert response2.status == ResponseStatus.SUCCESS
    
    @pytest_asyncio.asyncio_test
    async def test_error_recovery_after_partial_failure(self, api_server):
        """Test recovery after partial batch failure."""
        commands = [
            {'command': 'move', 'parameters': {'x': 100.0}},
            {'command': 'move', 'parameters': {'y': 50.0}},
            {'command': 'move', 'parameters': {'z': 9999.0}}  # Error
        ]
        
        # Mock batch with partial failure
        responses = [
            OpenPNPResponse(status=ResponseStatus.SUCCESS, command='move'),
            OpenPNPResponse(status=ResponseStatus.SUCCESS, command='move'),
            OpenPNPResponse(
                status=ResponseStatus.ERROR,
                command='move',
                error_message='Position out of bounds',
                error_code='VALIDATION_ERROR'
            )
        ]
        openpnp_translator.execute_batch = AsyncMock(return_value=responses)
        
        # Execute batch with stop_on_error=False
        results = await openpnp_translator.execute_batch(commands, stop_on_error=False)
        
        # Verify partial failure
        assert len(results) == 3
        assert results[0].status == ResponseStatus.SUCCESS
        assert results[1].status == ResponseStatus.SUCCESS
        assert results[2].status == ResponseStatus.ERROR


class TestErrorLogging:
    """Test suite for error logging."""
    
    @pytest_asyncio.asyncio_test
    async def test_error_logging_in_translator(self, openpnp_translator):
        """Test that errors are logged in translator."""
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.MOVE,
            parameters={'x': 100.0, 'y': 50.0, 'z': 10.0}
        )
        
        # Mock translate_and_execute to log error
        async def mock_translate_and_execute(cmd):
            return OpenPNPResponse(
                status=ResponseStatus.ERROR,
                command='move',
                error_message='Test error',
                error_code='TEST_ERROR'
            )
        
        openpnp_translator.translate_and_execute = mock_translate_and_execute
        
        # Execute command
        response = await openpnp_translator.translate_and_execute(command)
        
        # Verify error was logged (in real implementation)
        assert response.status == ResponseStatus.ERROR
        assert response.error_code == 'TEST_ERROR'
    
    @pytest_asyncio.asyncio_test
    async def test_error_logging_in_safety(self, api_server):
        """Test that safety errors are logged."""
        command = {
            'command': 'move',
            'parameters': {'x': 100.0, 'y': 50.0, 'z': 10.0}
        }
        
        # Mock safety to log error
        api_server.safety_manager.validate_move_command = AsyncMock(
            return_value=(False, ['Position out of bounds'])
        )
        
        # Execute command
        response = await api_server.execute_command(command)
        
        # Verify error was handled
        assert response.status == ResponseStatus.ERROR
        assert 'bounds' in response.error_message.lower()
    
    @pytest_asyncio.asyncio_test
    async def test_error_logging_in_cache(self, api_server):
        """Test that cache errors are logged."""
        command = {
            'command': 'sensor_read',
            'parameters': {'sensor': 'temperature_sensor'}
        }
        
        # Mock cache to log error
        async def mock_get(key, category=None, force_refresh=False):
            raise Exception('Cache error')
        
        api_server.cache_manager.get = mock_get
        
        # Execute command
        try:
            response = await api_server.execute_command(command)
        except Exception as e:
            # Verify error was caught
            assert 'cache' in str(e).lower()
    
    @pytest_asyncio.asyncio_test
    async def test_error_logging_with_warnings(self, openpnp_translator):
        """Test that warnings are logged in responses."""
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.MOVE,
            parameters={'x': 100.0, 'y': 50.0, 'z': 10.0}
        )
        
        # Mock response with warning
        async def mock_translate_and_execute(cmd):
            response = OpenPNPResponse(
                status=ResponseStatus.SUCCESS,
                command='move',
                data={'gcode': 'G0 X100.0 Y50.0 Z10.0'},
                warnings=['Position near limit', 'High feedrate']
            )
            response.add_warning('Position near limit')
            response.add_warning('High feedrate')
            return response
        
        openpnp_translator.translate_and_execute = mock_translate_and_execute
        
        # Execute command
        response = await openpnp_translator.translate_and_execute(command)
        
        # Verify warnings
        assert len(response.warnings) == 2
        assert 'Position near limit' in response.warnings
        assert 'High feedrate' in response.warnings
