#!/usr/bin/env python3
# Integration Tests: Middleware to G-code Driver
# Tests the integration between middleware translator and G-code driver components

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from middleware.translator import (
    OpenPNPTranslator,
    OpenPNPCommand,
    OpenPNPCommandType,
    OpenPNPResponse,
    ResponseStatus,
    TranslationStrategy
)
from gcode_driver.translator import (
    CommandTranslator,
    MoonrakerClient,
    ExecutionResult,
    ExecutionStatus,
    TranslationContext
)
from gcode_driver.parser import (
    GCodeParser,
    GCodeCommand,
    GCodeCommandType
)


class TestMiddlewareToGCodeDriverIntegration:
    """Test suite for middleware to G-code driver integration."""
    
    @pytest_asyncio.asyncio_test
    async def test_translator_initializes_gcode_translator(self, openpnp_translator):
        """Test that OpenPNP translator initializes G-code translator."""
        assert openpnp_translator.gcode_translator is not None
        assert isinstance(openpnp_translator.gcode_translator, CommandTranslator)
        assert openpnp_translator.gcode_translator.moonraker_host == 'localhost'
        assert openpnp_translator.gcode_translator.moonraker_port == 7125
    
    @pytest_asyncio.asyncio_test
    async def test_translator_initializes_execution_handler(self, openpnp_translator):
        """Test that OpenPNP translator initializes execution handler."""
        # Access execution handler
        handler = openpnp_translator._get_execution_handler()
        
        assert handler is not None
        assert hasattr(handler, 'execute_single')
        assert hasattr(handler, 'enqueue_command')
        assert hasattr(handler, 'process_queue')
    
    @pytest_asyncio.asyncio_test
    async def test_translator_strategy_mapping(self, openpnp_translator):
        """Test that translator has correct strategy mappings."""
        # Check direct API commands
        assert openpnp_translator._get_strategy(OpenPNPCommandType.GPIO_READ) == TranslationStrategy.DIRECT_API
        assert openpnp_translator._get_strategy(OpenPNPCommandType.SENSOR_READ) == TranslationStrategy.DIRECT_API
        assert openpnp_translator._get_strategy(OpenPNPCommandType.FAN_SET) == TranslationStrategy.DIRECT_API
        assert openpnp_translator._get_strategy(OpenPNPCommandType.PWM_SET) == TranslationStrategy.DIRECT_API
        
        # Check G-code commands
        assert openpnp_translator._get_strategy(OpenPNPCommandType.MOVE) == TranslationStrategy.GCODE
        assert openpnp_translator._get_strategy(OpenPNPCommandType.PICK) == TranslationStrategy.GCODE
        assert openpnp_translator._get_strategy(OpenPNPCommandType.PLACE) == TranslationStrategy.GCODE
        assert openpnp_translator._get_strategy(OpenPNPCommandType.VACUUM_ON) == TranslationStrategy.GCODE
        
        # Check hybrid commands
        assert openpnp_translator._get_strategy(OpenPNPCommandType.GET_STATUS) == TranslationStrategy.HYBRID
        assert openpnp_translator._get_strategy(OpenPNPCommandType.GET_POSITION) == TranslationStrategy.HYBRID
    
    @pytest_asyncio.asyncio_test
    async def test_translator_convert_to_gcode_move(self, openpnp_translator):
        """Test G-code conversion for move command."""
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.MOVE,
            parameters={'x': 100.0, 'y': 50.0, 'z': 10.0, 'feedrate': 1500.0}
        )
        
        gcode = openpnp_translator._convert_to_gcode(command)
        
        assert 'G0' in gcode
        assert 'X100.0' in gcode
        assert 'Y50.0' in gcode
        assert 'Z10.0' in gcode
        assert 'F1500.0' in gcode
    
    @pytest_asyncio.asyncio_test
    async def test_translator_convert_to_gcode_pick(self, openpnp_translator):
        """Test G-code conversion for pick command."""
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.PICK,
            parameters={'z': 0.0, 'vacuum_power': 255, 'travel_height': 5.0, 'feedrate': 1500.0}
        )
        
        gcode = openpnp_translator._convert_to_gcode(command)
        
        assert 'G0 Z0.0' in gcode
        assert 'M106 S255' in gcode
        assert 'G0 Z5.0' in gcode
    
    @pytest_asyncio.asyncio_test
    async def test_translator_convert_to_gcode_place(self, openpnp_translator):
        """Test G-code conversion for place command."""
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.PLACE,
            parameters={'z': 0.0, 'travel_height': 5.0, 'feedrate': 1500.0}
        )
        
        gcode = openpnp_translator._convert_to_gcode(command)
        
        assert 'G0 Z0.0' in gcode
        assert 'M107' in gcode
        assert 'G0 Z5.0' in gcode
    
    @pytest_asyncio.asyncio_test
    async def test_translator_convert_to_gcode_pick_and_place(self, openpnp_translator):
        """Test G-code conversion for pick and place command."""
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.PICK_AND_PLACE,
            parameters={
                'x': 100.0, 'y': 50.0,
                'place_x': 200.0, 'place_y': 100.0,
                'pick_height': 0.0, 'place_height': 0.0,
                'safe_height': 10.0, 'vacuum_power': 255,
                'feedrate': 1500.0
            }
        )
        
        gcode = openpnp_translator._convert_to_gcode(command)
        
        # Verify all expected G-code commands are present
        assert 'G0 Z10.0' in gcode
        assert 'G0 X100.0 Y50.0' in gcode
        assert 'G0 Z0.0' in gcode
        assert 'M106 S255' in gcode
        assert 'G0 X200.0 Y100.0' in gcode
        assert 'M107' in gcode
    
    @pytest_asyncio.asyncio_test
    async def test_translator_convert_to_gcode_vacuum(self, openpnp_translator):
        """Test G-code conversion for vacuum commands."""
        # Test vacuum on
        command_on = OpenPNPCommand(
            command_type=OpenPNPCommandType.VACUUM_ON,
            parameters={'power': 200}
        )
        gcode_on = openpnp_translator._convert_to_gcode(command_on)
        assert 'M106 S200' in gcode_on
        
        # Test vacuum off
        command_off = OpenPNPCommand(
            command_type=OpenPNPCommandType.VACUUM_OFF,
            parameters={}
        )
        gcode_off = openpnp_translator._convert_to_gcode(command_off)
        assert 'M107' in gcode_off
    
    @pytest_asyncio.asyncio_test
    async def test_translator_convert_to_gcode_fan(self, openpnp_translator):
        """Test G-code conversion for fan commands."""
        # Test fan on
        command_on = OpenPNPCommand(
            command_type=OpenPNPCommandType.FAN_ON,
            parameters={'speed': 200}
        )
        gcode_on = openpnp_translator._convert_to_gcode(command_on)
        assert 'M106 S200' in gcode_on
        
        # Test fan off
        command_off = OpenPNPCommand(
            command_type=OpenPNPCommandType.FAN_OFF,
            parameters={}
        )
        gcode_off = openpnp_translator._convert_to_gcode(command_off)
        assert 'M107' in gcode_off
    
    @pytest_asyncio.asyncio_test
    async def test_translator_convert_to_gcode_home(self, openpnp_translator):
        """Test G-code conversion for home command."""
        # Test home all
        command_all = OpenPNPCommand(
            command_type=OpenPNPCommandType.HOME,
            parameters={'axes': 'all'}
        )
        gcode_all = openpnp_translator._convert_to_gcode(command_all)
        assert gcode_all == 'G28'
        
        # Test home specific axis
        command_xy = OpenPNPCommand(
            command_type=OpenPNPCommandType.HOME,
            parameters={'axes': 'XY'}
        )
        gcode_xy = openpnp_translator._convert_to_gcode(command_xy)
        assert gcode_xy == 'G28 XY'
    
    @pytest_asyncio.asyncio_test
    async def test_translator_convert_to_gcode_actuator(self, openpnp_translator):
        """Test G-code conversion for actuator commands."""
        # Test actuate
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.ACTUATE,
            parameters={'pin': 'PA1', 'value': 1}
        )
        gcode = openpnp_translator._convert_to_gcode(command)
        assert 'SET_PIN PIN=PA1 VALUE=1' in gcode
    
    @pytest_asyncio.asyncio_test
    async def test_translator_execute_gcode_delegates_to_handler(self, openpnp_translator):
        """Test that G-code execution delegates to execution handler."""
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.MOVE,
            parameters={'x': 100.0, 'y': 50.0, 'z': 10.0}
        )
        
        # Mock execution handler
        handler = openpnp_translator._get_execution_handler()
        expected_result = ExecutionResult(
            status=ExecutionStatus.COMPLETED,
            gcode='G0 X100.0 Y50.0 Z10.0',
            execution_time=0.1
        )
        handler.execute_single = AsyncMock(return_value=expected_result)
        
        # Execute command
        response = await openpnp_translator._execute_gcode(command)
        
        # Verify delegation
        handler.execute_single.assert_called_once()
        assert response.status == ResponseStatus.SUCCESS
        assert 'gcode' in response.data
    
    @pytest_asyncio.asyncio_test
    async def test_translator_execute_direct_api(self, openpnp_translator):
        """Test that direct API commands are executed correctly."""
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.GPIO_READ,
            parameters={'pin': 'PA1'}
        )
        
        # Mock Moonraker client
        mock_client = openpnp_translator.gcode_translator.get_moonraker_client()
        
        async def mock_get(url, headers=None):
            class MockResponse:
                status = 200
                async def json(self):
                    return {'success': True, 'pin': 'PA1', 'value': 1}
            return MockResponse()
        
        mock_client.session.get = mock_get
        
        # Execute command
        response = await openpnp_translator._execute_direct_api(command)
        
        # Verify execution
        assert response.status == ResponseStatus.SUCCESS
        assert response.data is not None
    
    @pytest_asyncio.asyncio_test
    async def test_translator_execute_hybrid(self, openpnp_translator):
        """Test that hybrid commands combine API and G-code."""
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.GET_STATUS,
            parameters={}
        )
        
        # Mock required methods
        async def mock_get_printer_status():
            return {'state': 'ready', 'print_stats': {'state': 'idle'}}
        
        async def mock_get_klippy_state():
            return 'ready'
        
        mock_client = openpnp_translator.gcode_translator.get_moonraker_client()
        mock_client.get_printer_status = mock_get_printer_status
        mock_client.get_klippy_state = mock_get_klippy_state
        
        # Execute command
        response = await openpnp_translator._execute_hybrid(command)
        
        # Verify execution
        assert response.status == ResponseStatus.SUCCESS
        assert 'printer_status' in response.data
        assert 'klippy_state' in response.data
        assert 'internal_state' in response.data
    
    @pytest_asyncio.asyncio_test
    async def test_translator_state_updates_on_success(self, openpnp_translator):
        """Test that translator state updates on successful commands."""
        # Execute move command
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.MOVE,
            parameters={'x': 100.0, 'y': 50.0, 'z': 10.0}
        )
        
        expected_response = OpenPNPResponse(
            status=ResponseStatus.SUCCESS,
            command='move',
            data={'gcode': 'G0 X100.0 Y50.0 Z10.0'}
        )
        openpnp_translator.translate_and_execute = AsyncMock(return_value=expected_response)
        
        await openpnp_translator.translate_and_execute(command)
        
        # Verify state was updated
        state = openpnp_translator.get_state()
        assert state['current_position']['x'] == 100.0
        assert state['current_position']['y'] == 50.0
        assert state['current_position']['z'] == 10.0
    
    @pytest_asyncio.asyncio_test
    async def test_translator_state_updates_vacuum(self, openpnp_translator):
        """Test that vacuum state updates correctly."""
        # Test vacuum on
        command_on = OpenPNPCommand(
            command_type=OpenPNPCommandType.VACUUM_ON,
            parameters={'power': 200}
        )
        expected_response_on = OpenPNPResponse(
            status=ResponseStatus.SUCCESS,
            command='vacuum_on'
        )
        openpnp_translator.translate_and_execute = AsyncMock(return_value=expected_response_on)
        
        await openpnp_translator.translate_and_execute(command_on)
        state_on = openpnp_translator.get_state()
        assert state_on['vacuum_enabled'] == True
        
        # Test vacuum off
        command_off = OpenPNPCommand(
            command_type=OpenPNPCommandType.VACUUM_OFF,
            parameters={}
        )
        expected_response_off = OpenPNPResponse(
            status=ResponseStatus.SUCCESS,
            command='vacuum_off'
        )
        openpnp_translator.translate_and_execute = AsyncMock(return_value=expected_response_off)
        
        await openpnp_translator.translate_and_execute(command_off)
        state_off = openpnp_translator.get_state()
        assert state_off['vacuum_enabled'] == False
    
    @pytest_asyncio.asyncio_test
    async def test_translator_state_updates_fan(self, openpnp_translator):
        """Test that fan state updates correctly."""
        # Test fan set
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.FAN_SET,
            parameters={'speed': 0.5}
        )
        expected_response = OpenPNPResponse(
            status=ResponseStatus.SUCCESS,
            command='fan_set'
        )
        openpnp_translator.translate_and_execute = AsyncMock(return_value=expected_response)
        
        await openpnp_translator.translate_and_execute(command)
        state = openpnp_translator.get_state()
        assert state['fan_speed'] == 0.5
    
    @pytest_asyncio.asyncio_test
    async def test_translator_enqueue_command(self, openpnp_translator):
        """Test that commands can be enqueued."""
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.MOVE,
            parameters={'x': 100.0, 'y': 50.0, 'z': 10.0}
        )
        
        # Mock execution handler
        handler = openpnp_translator._get_execution_handler()
        handler.enqueue_command = AsyncMock(return_value='cmd_123')
        
        # Enqueue command
        command_id = await openpnp_translator.enqueue_command(command, priority=0)
        
        # Verify enqueue
        handler.enqueue_command.assert_called_once()
        assert command_id == 'cmd_123'
    
    @pytest_asyncio.asyncio_test
    async def test_translator_process_queue(self, openpnp_translator):
        """Test that queue can be processed."""
        # Mock execution handler
        handler = openpnp_translator._get_execution_handler()
        
        expected_results = [
            ExecutionResult(status=ExecutionStatus.COMPLETED, gcode='G0 X100'),
            ExecutionResult(status=ExecutionStatus.COMPLETED, gcode='G0 Y50')
        ]
        handler.process_queue = AsyncMock(return_value=expected_results)
        
        # Process queue
        responses = await openpnp_translator.process_queue(stop_on_error=False)
        
        # Verify processing
        handler.process_queue.assert_called_once_with(stop_on_error=False)
        assert len(responses) == 2
        assert all(r.status == ResponseStatus.SUCCESS for r in responses)
    
    @pytest_asyncio.asyncio_test
    async def test_translator_batch_execution(self, openpnp_translator):
        """Test batch command execution."""
        commands = [
            {'command': 'move', 'parameters': {'x': 100.0}},
            {'command': 'move', 'parameters': {'y': 50.0}},
            {'command': 'move', 'parameters': {'z': 10.0}}
        ]
        
        # Mock translate_and_execute
        responses = [
            OpenPNPResponse(status=ResponseStatus.SUCCESS, command='move'),
            OpenPNPResponse(status=ResponseStatus.SUCCESS, command='move'),
            OpenPNPResponse(status=ResponseStatus.SUCCESS, command='move')
        ]
        openpnp_translator.translate_and_execute = AsyncMock(side_effect=responses)
        
        # Execute batch
        results = await openpnp_translator.execute_batch(commands, stop_on_error=False)
        
        # Verify batch execution
        assert len(results) == 3
        assert all(r.status == ResponseStatus.SUCCESS for r in results)
        assert openpnp_translator.translate_and_execute.call_count == 3
    
    @pytest_asyncio.asyncio_test
    async def test_translator_error_handling(self, openpnp_translator):
        """Test that translator handles errors gracefully."""
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.MOVE,
            parameters={'x': 100.0}
        )
        
        # Mock translate_and_execute to raise an exception
        openpnp_translator.translate_and_execute = AsyncMock(
            side_effect=Exception('Test error')
        )
        
        # Execute command
        response = await openpnp_translator.translate_and_execute(command)
        
        # Verify error handling
        assert response.status == ResponseStatus.ERROR
        assert response.error_message == 'Test error'
        assert response.error_code == 'EXECUTION_ERROR'
    
    @pytest_asyncio.asyncio_test
    async def test_gcode_translator_context_management(self, openpnp_translator):
        """Test that G-code translator manages context correctly."""
        gcode_translator = openpnp_translator.gcode_translator
        
        # Get initial context
        initial_context = gcode_translator.get_context()
        assert initial_context.feedrate == 1500.0
        assert initial_context.positioning_mode == 'absolute'
        assert initial_context.units == 'mm'
        
        # Update context
        gcode_translator.context.feedrate = 2000.0
        gcode_translator.context.positioning_mode = 'relative'
        
        # Verify context update
        updated_context = gcode_translator.get_context()
        assert updated_context.feedrate == 2000.0
        assert updated_context.positioning_mode == 'relative'
    
    @pytest_asyncio.asyncio_test
    async def test_gcode_translator_template_usage(self, openpnp_translator):
        """Test that G-code translator uses templates correctly."""
        gcode_translator = openpnp_translator.gcode_translator
        
        # Get templates
        templates = gcode_translator.get_templates()
        
        # Verify default templates exist
        assert 'move' in templates
        assert 'pick' in templates
        assert 'place' in templates
        assert 'pick_and_place' in templates
        assert 'vacuum_on' in templates
        assert 'vacuum_off' in templates
    
    @pytest_asyncio.asyncio_test
    async def test_gcode_translator_add_custom_template(self, openpnp_translator):
        """Test that custom templates can be added."""
        gcode_translator = openpnp_translator.gcode_translator
        
        # Add custom template
        template_name = 'custom_move'
        template = 'G0 X{x} Y{y} Z{z} F{feedrate}\nM400'
        gcode_translator.add_template(template_name, template)
        
        # Verify template was added
        templates = gcode_translator.get_templates()
        assert template_name in templates
        assert templates[template_name] == template
    
    @pytest_asyncio.asyncio_test
    async def test_gcode_translator_add_custom_validator(self, openpnp_translator):
        """Test that custom validators can be added."""
        gcode_translator = openpnp_translator.gcode_translator
        
        # Add custom validator
        param_name = 'custom_x'
        validator = lambda x: 0 <= x <= 500
        gcode_translator.add_validator(param_name, validator)
        
        # Verify validator was added
        assert param_name in gcode_translator.validators
        assert gcode_translator.validators[param_name] == validator
    
    @pytest_asyncio.asyncio_test
    async def test_gcode_translator_reset_context(self, openpnp_translator):
        """Test that G-code translator context can be reset."""
        gcode_translator = openpnp_translator.gcode_translator
        
        # Modify context
        gcode_translator.context.feedrate = 2000.0
        gcode_translator.context.current_position = {'x': 100.0, 'y': 50.0, 'z': 10.0}
        
        # Reset context
        gcode_translator.reset_context()
        
        # Verify reset
        context = gcode_translator.get_context()
        assert context.feedrate == 1500.0
        assert context.current_position == {'x': 0.0, 'y': 0.0, 'z': 0.0}
        assert context.positioning_mode == 'absolute'
    
    @pytest_asyncio.asyncio_test
    async def test_translator_command_parsing(self, openpnp_translator):
        """Test that translator can parse command dictionaries."""
        command_dict = {
            'command': 'move',
            'parameters': {'x': 100.0, 'y': 50.0, 'z': 10.0},
            'metadata': {'source': 'test'},
            'priority': 1
        }
        
        # Parse command
        command = openpnp_translator._parse_command_dict(command_dict)
        
        # Verify parsing
        assert command.command_type == OpenPNPCommandType.MOVE
        assert command.parameters == {'x': 100.0, 'y': 50.0, 'z': 10.0}
        assert command.metadata == {'source': 'test'}
        assert command.priority == 1
    
    @pytest_asyncio.asyncio_test
    async def test_translator_invalid_command_type(self, openpnp_translator):
        """Test that translator handles invalid command types."""
        command_dict = {
            'command': 'invalid_command',
            'parameters': {}
        }
        
        # Attempt to parse command
        try:
            command = openpnp_translator._parse_command_dict(command_dict)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert 'Unknown command type' in str(e)
    
    @pytest_asyncio.asyncio_test
    async def test_translator_response_serialization(self, openpnp_translator):
        """Test that OpenPNP responses can be serialized."""
        response = OpenPNPResponse(
            status=ResponseStatus.SUCCESS,
            command='move',
            data={'x': 100.0, 'y': 50.0, 'z': 10.0},
            execution_time=0.123
        )
        
        # Serialize to dict
        response_dict = response.to_dict()
        
        # Verify serialization
        assert response_dict['status'] == 'success'
        assert response_dict['command'] == 'move'
        assert response_dict['data'] == {'x': 100.0, 'y': 50.0, 'z': 10.0}
        assert response_dict['execution_time'] == 0.123
        assert 'command_id' in response_dict
        assert 'timestamp' in response_dict
    
    @pytest_asyncio.asyncio_test
    async def test_translator_response_warnings(self, openpnp_translator):
        """Test that warnings can be added to responses."""
        response = OpenPNPResponse(
            status=ResponseStatus.SUCCESS,
            command='move',
            data={'x': 100.0}
        )
        
        # Add warnings
        response.add_warning('Position out of bounds')
        response.add_warning('High feedrate')
        
        # Verify warnings
        assert len(response.warnings) == 2
        assert 'Position out of bounds' in response.warnings
        assert 'High feedrate' in response.warnings
    
    @pytest_asyncio.asyncio_test
    async def test_translator_get_statistics(self, openpnp_translator):
        """Test that translator statistics can be retrieved."""
        # Mock statistics
        expected_stats = {
            'total_commands': 10,
            'successful_commands': 8,
            'failed_commands': 2,
            'average_execution_time': 0.15
        }
        openpnp_translator.get_statistics = AsyncMock(return_value=expected_stats)
        
        # Get statistics
        stats = await openpnp_translator.get_statistics()
        
        # Verify statistics
        assert stats == expected_stats
        openpnp_translator.get_statistics.assert_called_once()
    
    @pytest_asyncio.asyncio_test
    async def test_translator_get_history(self, openpnp_translator):
        """Test that translator history can be retrieved."""
        # Mock history
        expected_history = [
            {'command': 'move', 'status': 'success', 'timestamp': 1234567890.0},
            {'command': 'pick', 'status': 'success', 'timestamp': 1234567891.0}
        ]
        openpnp_translator.get_history = AsyncMock(return_value=expected_history)
        
        # Get history
        history = await openpnp_translator.get_history(limit=10)
        
        # Verify history
        assert history == expected_history
        openpnp_translator.get_history.assert_called_once_with(limit=10)
    
    @pytest_asyncio.asyncio_test
    async def test_translator_get_queue_info(self, openpnp_translator):
        """Test that translator queue info can be retrieved."""
        # Mock queue info
        expected_queue_info = {
            'queue_size': 5,
            'processing': False,
            'pending_commands': 5
        }
        openpnp_translator.get_queue_info = AsyncMock(return_value=expected_queue_info)
        
        # Get queue info
        queue_info = await openpnp_translator.get_queue_info()
        
        # Verify queue info
        assert queue_info == expected_queue_info
        openpnp_translator.get_queue_info.assert_called_once()
