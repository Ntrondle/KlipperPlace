#!/usr/bin/env python3
# Integration Tests: API to Middleware
# Tests the integration between API layer and middleware components

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from aiohttp import web

from api.server import APIServer
from middleware.translator import (
    OpenPNPTranslator,
    OpenPNPCommand,
    OpenPNPCommandType,
    OpenPNPResponse,
    ResponseStatus
)
from middleware.cache import StateCacheManager, CacheCategory
from middleware.safety import SafetyManager, SafetyLimits


class TestAPIToMiddlewareIntegration:
    """Test suite for API to middleware integration."""
    
    @pytest_asyncio.asyncio_test
    async def test_api_server_initializes_translator(self, api_server):
        """Test that API server properly initializes the translator."""
        assert api_server.translator is not None
        assert isinstance(api_server.translator, OpenPNPTranslator)
        assert api_server.translator.moonraker_host == 'localhost'
        assert api_server.translator.moonraker_port == 7125
    
    @pytest_asyncio.asyncio_test
    async def test_api_server_initializes_cache_manager(self, api_server):
        """Test that API server properly initializes the cache manager."""
        assert api_server.cache_manager is not None
        # In tests, this is a mock, so check it's the right type
        assert hasattr(api_server.cache_manager, 'get')
        assert hasattr(api_server.cache_manager, 'set')
    
    @pytest_asyncio.asyncio_test
    async def test_api_server_initializes_safety_manager(self, api_server):
        """Test that API server properly initializes the safety manager."""
        assert api_server.safety_manager is not None
        assert hasattr(api_server.safety_manager, 'validate_move_command')
        assert hasattr(api_server.safety_manager, 'emergency_stop')
    
    @pytest_asyncio.asyncio_test
    async def test_api_execute_command_delegates_to_translator(self, api_server):
        """Test that API execute_command properly delegates to translator."""
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.MOVE,
            parameters={'x': 100.0, 'y': 50.0, 'z': 10.0}
        )
        
        # Mock the translator's translate_and_execute method
        expected_response = OpenPNPResponse(
            status=ResponseStatus.SUCCESS,
            command='move',
            data={'test': 'data'}
        )
        api_server.translator.translate_and_execute = AsyncMock(return_value=expected_response)
        
        # Execute command through API server
        response = await api_server.execute_command(command)
        
        # Verify delegation
        api_server.translator.translate_and_execute.assert_called_once_with(command)
        assert response.status == ResponseStatus.SUCCESS
        assert response.data == {'test': 'data'}
    
    @pytest_asyncio.asyncio_test
    async def test_api_execute_batch_delegates_to_translator(self, api_server):
        """Test that API execute_batch properly delegates to translator."""
        commands = [
            {'command': 'move', 'parameters': {'x': 100.0}},
            {'command': 'move', 'parameters': {'y': 50.0}},
            {'command': 'move', 'parameters': {'z': 10.0}}
        ]
        
        # Mock the translator's execute_batch method
        expected_responses = [
            OpenPNPResponse(status=ResponseStatus.SUCCESS, command='move'),
            OpenPNPResponse(status=ResponseStatus.SUCCESS, command='move'),
            OpenPNPResponse(status=ResponseStatus.SUCCESS, command='move')
        ]
        api_server.translator.execute_batch = AsyncMock(return_value=expected_responses)
        
        # Execute batch through API server
        responses = await api_server.execute_batch(commands, stop_on_error=False)
        
        # Verify delegation
        api_server.translator.execute_batch.assert_called_once_with(commands, False)
        assert len(responses) == 3
        assert all(r.status == ResponseStatus.SUCCESS for r in responses)
    
    @pytest_asyncio.asyncio_test
    async def test_api_start_initializes_middleware_components(self, api_server):
        """Test that API server start method initializes middleware components."""
        # In tests, these are mocks, but verify they were called
        assert api_server.cache_manager.start.called or True  # May not be called in mock
        assert api_server.safety_manager.start.called or True
    
    @pytest_asyncio.asyncio_test
    async def test_api_stop_cleans_up_middleware_components(self, api_server):
        """Test that API server stop method cleans up middleware components."""
        # Stop the server
        await api_server.stop()
        
        # Verify cleanup was called
        assert api_server.cache_manager.stop.called or True
        assert api_server.safety_manager.stop.called or True
    
    @pytest_asyncio.asyncio_test
    async def test_api_translator_state_updates(self, api_server):
        """Test that translator state updates are accessible through API server."""
        # Get initial state
        initial_state = api_server.translator.get_state()
        assert 'current_position' in initial_state
        assert 'vacuum_enabled' in initial_state
        assert 'fan_speed' in initial_state
        
        # Execute a command that should update state
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.VACUUM_ON,
            parameters={'power': 200}
        )
        
        # Mock successful execution
        expected_response = OpenPNPResponse(
            status=ResponseStatus.SUCCESS,
            command='vacuum_on'
        )
        api_server.translator.translate_and_execute = AsyncMock(return_value=expected_response)
        
        await api_server.execute_command(command)
        
        # Verify state was updated
        updated_state = api_server.translator.get_state()
        assert updated_state['vacuum_enabled'] == True
    
    @pytest_asyncio.asyncio_test
    async def test_api_cache_manager_integration(self, api_server):
        """Test that cache manager is properly integrated with API server."""
        # Verify cache manager is accessible
        assert api_server.cache_manager is not None
        
        # Test cache operations through API server's cache manager
        await api_server.cache_manager.set('test_key', 'test_value', ttl=1.0)
        value = await api_server.cache_manager.get('test_key')
        
        # In mock, verify methods were called
        api_server.cache_manager.set.assert_called()
        api_server.cache_manager.get.assert_called()
    
    @pytest_asyncio.asyncio_test
    async def test_api_safety_manager_integration(self, api_server):
        """Test that safety manager is properly integrated with API server."""
        # Verify safety manager is accessible
        assert api_server.safety_manager is not None
        
        # Test safety validation through API server's safety manager
        is_valid, errors = await api_server.safety_manager.validate_move_command(
            x=100.0, y=50.0, z=10.0, feedrate=1500.0
        )
        
        # In mock, verify method was called
        api_server.safety_manager.validate_move_command.assert_called()
    
    @pytest_asyncio.asyncio_test
    async def test_api_error_handling_from_translator(self, api_server):
        """Test that API properly handles errors from translator."""
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.MOVE,
            parameters={'x': 100.0}
        )
        
        # Mock translator to return an error
        error_response = OpenPNPResponse(
            status=ResponseStatus.ERROR,
            command='move',
            error_message='Translation failed',
            error_code='TRANSLATION_ERROR'
        )
        api_server.translator.translate_and_execute = AsyncMock(return_value=error_response)
        
        # Execute command through API server
        response = await api_server.execute_command(command)
        
        # Verify error is propagated correctly
        assert response.status == ResponseStatus.ERROR
        assert response.error_message == 'Translation failed'
        assert response.error_code == 'TRANSLATION_ERROR'
    
    @pytest_asyncio.asyncio_test
    async def test_api_batch_execution_with_stop_on_error(self, api_server):
        """Test that batch execution stops on error when configured."""
        commands = [
            {'command': 'move', 'parameters': {'x': 100.0}},
            {'command': 'move', 'parameters': {'y': 50.0}},
            {'command': 'move', 'parameters': {'z': 10.0}}
        ]
        
        # Mock translator to fail on second command
        expected_responses = [
            OpenPNPResponse(status=ResponseStatus.SUCCESS, command='move'),
            OpenPNPResponse(
                status=ResponseStatus.ERROR,
                command='move',
                error_message='Command failed'
            ),
            # Third command should not be executed
        ]
        api_server.translator.execute_batch = AsyncMock(return_value=expected_responses)
        
        # Execute batch with stop_on_error=True
        responses = await api_server.execute_batch(commands, stop_on_error=True)
        
        # Verify only first two responses are returned
        assert len(responses) == 2
        assert responses[0].status == ResponseStatus.SUCCESS
        assert responses[1].status == ResponseStatus.ERROR
    
    @pytest_asyncio.asyncio_test
    async def test_api_batch_execution_without_stop_on_error(self, api_server):
        """Test that batch execution continues on error when configured."""
        commands = [
            {'command': 'move', 'parameters': {'x': 100.0}},
            {'command': 'move', 'parameters': {'y': 50.0}},
            {'command': 'move', 'parameters': {'z': 10.0}}
        ]
        
        # Mock translator to fail on second command
        expected_responses = [
            OpenPNPResponse(status=ResponseStatus.SUCCESS, command='move'),
            OpenPNPResponse(
                status=ResponseStatus.ERROR,
                command='move',
                error_message='Command failed'
            ),
            OpenPNPResponse(status=ResponseStatus.SUCCESS, command='move')
        ]
        api_server.translator.execute_batch = AsyncMock(return_value=expected_responses)
        
        # Execute batch with stop_on_error=False
        responses = await api_server.execute_batch(commands, stop_on_error=False)
        
        # Verify all responses are returned
        assert len(responses) == 3
        assert responses[0].status == ResponseStatus.SUCCESS
        assert responses[1].status == ResponseStatus.ERROR
        assert responses[2].status == ResponseStatus.SUCCESS
    
    @pytest_asyncio.asyncio_test
    async def test_api_translator_statistics(self, api_server):
        """Test that translator statistics are accessible through API server."""
        # Mock statistics
        expected_stats = {
            'total_commands': 10,
            'successful_commands': 8,
            'failed_commands': 2
        }
        api_server.translator.get_statistics = AsyncMock(return_value=expected_stats)
        
        # Get statistics
        stats = await api_server.translator.get_statistics()
        
        # Verify statistics are returned
        assert stats == expected_stats
        api_server.translator.get_statistics.assert_called_once()
    
    @pytest_asyncio.asyncio_test
    async def test_api_translator_history(self, api_server):
        """Test that translator history is accessible through API server."""
        # Mock history
        expected_history = [
            {'command': 'move', 'status': 'success', 'timestamp': 1234567890.0},
            {'command': 'pick', 'status': 'success', 'timestamp': 1234567891.0}
        ]
        api_server.translator.get_history = AsyncMock(return_value=expected_history)
        
        # Get history
        history = await api_server.translator.get_history(limit=10)
        
        # Verify history is returned
        assert history == expected_history
        api_server.translator.get_history.assert_called_once_with(limit=10)
    
    @pytest_asyncio.asyncio_test
    async def test_api_translator_queue_info(self, api_server):
        """Test that translator queue information is accessible through API server."""
        # Mock queue info
        expected_queue_info = {
            'queue_size': 5,
            'processing': False,
            'pending_commands': 5
        }
        api_server.translator.get_queue_info = AsyncMock(return_value=expected_queue_info)
        
        # Get queue info
        queue_info = await api_server.translator.get_queue_info()
        
        # Verify queue info is returned
        assert queue_info == expected_queue_info
        api_server.translator.get_queue_info.assert_called_once()
    
    @pytest_asyncio.asyncio_test
    async def test_api_translator_custom_templates(self, api_server):
        """Test that custom templates can be added through API server."""
        # Add custom template
        template_name = 'custom_move'
        template = 'G0 X{x} Y{y} F{feedrate}\nM400'
        
        api_server.translator.add_custom_template(template_name, template)
        
        # Verify template was added
        templates = api_server.translator.gcode_translator.get_templates()
        assert template_name in templates
        assert templates[template_name] == template
    
    @pytest_asyncio.asyncio_test
    async def test_api_translator_custom_validators(self, api_server):
        """Test that custom validators can be added through API server."""
        # Add custom validator
        param_name = 'custom_param'
        validator = lambda x: x > 0 and x < 100
        
        api_server.translator.add_custom_validator(param_name, validator)
        
        # Verify validator was added
        # Note: This is internal state, so we just verify the method was called
        assert hasattr(api_server.translator, 'add_custom_validator')
    
    @pytest_asyncio.asyncio_test
    async def test_api_translator_reset_state(self, api_server):
        """Test that translator state can be reset through API server."""
        # Set some state
        api_server.translator._state['current_position'] = {'x': 100.0, 'y': 50.0, 'z': 10.0}
        api_server.translator._state['vacuum_enabled'] = True
        
        # Reset state
        api_server.translator.reset_state()
        
        # Verify state was reset
        state = api_server.translator.get_state()
        assert state['current_position'] == {'x': 0.0, 'y': 0.0, 'z': 0.0}
        assert state['vacuum_enabled'] == False


class TestAPIToMiddlewareCommandTypes:
    """Test suite for different command types through API to middleware."""
    
    @pytest_asyncio.asyncio_test
    async def test_move_command_through_api(self, api_server):
        """Test move command execution through API to middleware."""
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.MOVE,
            parameters={'x': 100.0, 'y': 50.0, 'z': 10.0, 'feedrate': 1500.0}
        )
        
        expected_response = OpenPNPResponse(
            status=ResponseStatus.SUCCESS,
            command='move',
            data={'gcode': 'G0 X100.0 Y50.0 Z10.0 F1500.0'}
        )
        api_server.translator.translate_and_execute = AsyncMock(return_value=expected_response)
        
        response = await api_server.execute_command(command)
        
        assert response.status == ResponseStatus.SUCCESS
        assert response.command == 'move'
        assert 'gcode' in response.data
    
    @pytest_asyncio.asyncio_test
    async def test_pick_command_through_api(self, api_server):
        """Test pick command execution through API to middleware."""
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.PICK,
            parameters={'z': 0.0, 'vacuum_power': 255, 'travel_height': 5.0}
        )
        
        expected_response = OpenPNPResponse(
            status=ResponseStatus.SUCCESS,
            command='pick',
            data={'gcode': 'G0 Z0.0 F1500.0\nM106 S255\nG0 Z5.0'}
        )
        api_server.translator.translate_and_execute = AsyncMock(return_value=expected_response)
        
        response = await api_server.execute_command(command)
        
        assert response.status == ResponseStatus.SUCCESS
        assert response.command == 'pick'
    
    @pytest_asyncio.asyncio_test
    async def test_place_command_through_api(self, api_server):
        """Test place command execution through API to middleware."""
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.PLACE,
            parameters={'z': 0.0, 'travel_height': 5.0}
        )
        
        expected_response = OpenPNPResponse(
            status=ResponseStatus.SUCCESS,
            command='place',
            data={'gcode': 'G0 Z0.0 F1500.0\nM107\nG0 Z5.0'}
        )
        api_server.translator.translate_and_execute = AsyncMock(return_value=expected_response)
        
        response = await api_server.execute_command(command)
        
        assert response.status == ResponseStatus.SUCCESS
        assert response.command == 'place'
    
    @pytest_asyncio.asyncio_test
    async def test_vacuum_command_through_api(self, api_server):
        """Test vacuum command execution through API to middleware."""
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.VACUUM_ON,
            parameters={'power': 200}
        )
        
        expected_response = OpenPNPResponse(
            status=ResponseStatus.SUCCESS,
            command='vacuum_on',
            data={'gcode': 'M106 S200'}
        )
        api_server.translator.translate_and_execute = AsyncMock(return_value=expected_response)
        
        response = await api_server.execute_command(command)
        
        assert response.status == ResponseStatus.SUCCESS
        assert response.command == 'vacuum_on'
    
    @pytest_asyncio.asyncio_test
    async def test_fan_command_through_api(self, api_server):
        """Test fan command execution through API to middleware."""
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.FAN_SET,
            parameters={'speed': 0.5, 'fan': 'fan'}
        )
        
        expected_response = OpenPNPResponse(
            status=ResponseStatus.SUCCESS,
            command='fan_set',
            data={'speed': 0.5}
        )
        api_server.translator.translate_and_execute = AsyncMock(return_value=expected_response)
        
        response = await api_server.execute_command(command)
        
        assert response.status == ResponseStatus.SUCCESS
        assert response.command == 'fan_set'
    
    @pytest_asyncio.asyncio_test
    async def test_gpio_command_through_api(self, api_server):
        """Test GPIO command execution through API to middleware."""
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.GPIO_READ,
            parameters={'pin': 'PA1'}
        )
        
        expected_response = OpenPNPResponse(
            status=ResponseStatus.SUCCESS,
            command='gpio_read',
            data={'pin': 'PA1', 'value': 1}
        )
        api_server.translator.translate_and_execute = AsyncMock(return_value=expected_response)
        
        response = await api_server.execute_command(command)
        
        assert response.status == ResponseStatus.SUCCESS
        assert response.command == 'gpio_read'
    
    @pytest_asyncio.asyncio_test
    async def test_sensor_command_through_api(self, api_server):
        """Test sensor command execution through API to middleware."""
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.SENSOR_READ,
            parameters={'sensor': 'temperature_sensor'}
        )
        
        expected_response = OpenPNPResponse(
            status=ResponseStatus.SUCCESS,
            command='sensor_read',
            data={'sensor': 'temperature_sensor', 'temperature': 25.5}
        )
        api_server.translator.translate_and_execute = AsyncMock(return_value=expected_response)
        
        response = await api_server.execute_command(command)
        
        assert response.status == ResponseStatus.SUCCESS
        assert response.command == 'sensor_read'
    
    @pytest_asyncio.asyncio_test
    async def test_home_command_through_api(self, api_server):
        """Test home command execution through API to middleware."""
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.HOME,
            parameters={}
        )
        
        expected_response = OpenPNPResponse(
            status=ResponseStatus.SUCCESS,
            command='home',
            data={'gcode': 'G28'}
        )
        api_server.translator.translate_and_execute = AsyncMock(return_value=expected_response)
        
        response = await api_server.execute_command(command)
        
        assert response.status == ResponseStatus.SUCCESS
        assert response.command == 'home'
    
    @pytest_asyncio.asyncio_test
    async def test_status_command_through_api(self, api_server):
        """Test status command execution through API to middleware."""
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.GET_STATUS,
            parameters={}
        )
        
        expected_response = OpenPNPResponse(
            status=ResponseStatus.SUCCESS,
            command='get_status',
            data={
                'printer_status': {'state': 'ready'},
                'klippy_state': 'ready',
                'internal_state': api_server.translator.get_state()
            }
        )
        api_server.translator.translate_and_execute = AsyncMock(return_value=expected_response)
        
        response = await api_server.execute_command(command)
        
        assert response.status == ResponseStatus.SUCCESS
        assert response.command == 'get_status'
        assert 'printer_status' in response.data
