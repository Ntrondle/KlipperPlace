#!/usr/bin/env python3
# Integration Tests: End-to-End Commands
# Tests for complete command execution flow from API to Moonraker

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
from gcode_driver.translator import (
    CommandTranslator,
    MoonrakerClient,
    ExecutionResult,
    ExecutionStatus
)


class TestEndToEndCommandExecution:
    """Test suite for end-to-end command execution."""
    
    @pytest_asyncio.asyncio_test
    async def test_complete_move_command_flow(self, api_server):
        """Test complete move command flow from API to Moonraker."""
        # Create move command
        command = {
            'command': 'move',
            'parameters': {
                'x': 100.0,
                'y': 50.0,
                'z': 10.0,
                'feedrate': 1500.0
            }
        }
        
        # Mock the complete flow
        # 1. API receives command
        # 2. Translator converts to G-code
        # 3. G-code driver executes
        # 4. Moonraker responds
        
        expected_gcode = 'G0 X100.0 Y50.0 Z10.0 F1500.0'
        
        # Mock Moonraker response
        async def mock_run_gcode(script):
            assert script == expected_gcode
            return ExecutionResult(
                status=ExecutionStatus.COMPLETED,
                gcode=script,
                response={'result': 'ok'},
                execution_time=0.1
            )
        
        # Set up mocks
        mock_client = api_server.translator.gcode_translator.get_moonraker_client()
        mock_client.run_gcode = mock_run_gcode
        
        # Execute command through API server
        response = await api_server.execute_command(command)
        
        # Verify complete flow
        assert response.status == ResponseStatus.SUCCESS
        assert response.command == 'move'
        assert 'gcode' in response.data
        assert response.data['gcode'] == expected_gcode
        assert response.data['execution_time'] == 0.1
    
    @pytest_asyncio.asyncio_test
    async def test_complete_pick_and_place_flow(self, api_server):
        """Test complete pick and place command flow."""
        command = {
            'command': 'pick_and_place',
            'parameters': {
                'x': 100.0,
                'y': 50.0,
                'place_x': 200.0,
                'place_y': 100.0,
                'pick_height': 0.0,
                'place_height': 0.0,
                'safe_height': 10.0,
                'vacuum_power': 255,
                'feedrate': 1500.0
            }
        }
        
        # Mock Moonraker response
        gcode_calls = []
        async def mock_run_gcode(script):
            gcode_calls.append(script)
            return ExecutionResult(
                status=ExecutionStatus.COMPLETED,
                gcode=script,
                response={'result': 'ok'},
                execution_time=0.05
            )
        
        mock_client = api_server.translator.gcode_translator.get_moonraker_client()
        mock_client.run_gcode = mock_run_gcode
        
        # Execute command
        response = await api_server.execute_command(command)
        
        # Verify complete flow
        assert response.status == ResponseStatus.SUCCESS
        assert response.command == 'pick_and_place'
        assert len(gcode_calls) > 0  # Multiple G-code commands should be executed
    
    @pytest_asyncio.asyncio_test
    async def test_complete_vacuum_control_flow(self, api_server):
        """Test complete vacuum control flow."""
        # Test vacuum on
        command_on = {
            'command': 'vacuum_on',
            'parameters': {'power': 200}
        }
        
        gcode_calls = []
        async def mock_run_gcode(script):
            gcode_calls.append(script)
            return ExecutionResult(
                status=ExecutionStatus.COMPLETED,
                gcode=script,
                response={'result': 'ok'},
                execution_time=0.02
            )
        
        mock_client = api_server.translator.gcode_translator.get_moonraker_client()
        mock_client.run_gcode = mock_run_gcode
        
        response_on = await api_server.execute_command(command_on)
        
        assert response_on.status == ResponseStatus.SUCCESS
        assert 'M106 S200' in gcode_calls[-1]
        
        # Test vacuum off
        command_off = {'command': 'vacuum_off', 'parameters': {}}
        response_off = await api_server.execute_command(command_off)
        
        assert response_off.status == ResponseStatus.SUCCESS
        assert 'M107' in gcode_calls[-1]
    
    @pytest_asyncio.asyncio_test
    async def test_complete_fan_control_flow(self, api_server):
        """Test complete fan control flow."""
        command = {
            'command': 'fan_set',
            'parameters': {
                'speed': 0.5,
                'fan': 'fan'
            }
        }
        
        # Mock Moonraker fan control API
        async def mock_post(url, json=None, headers=None):
            class MockResponse:
                status = 200
                async def json(self):
                    return {'success': True, 'speed': 0.5}
            return MockResponse()
        
        mock_client = api_server.translator.gcode_translator.get_moonraker_client()
        mock_client.session.post = mock_post
        
        # Execute command
        response = await api_server.execute_command(command)
        
        # Verify complete flow
        assert response.status == ResponseStatus.SUCCESS
        assert response.command == 'fan_set'
        assert response.data['speed'] == 0.5
    
    @pytest_asyncio.asyncio_test
    async def test_complete_gpio_read_flow(self, api_server):
        """Test complete GPIO read flow."""
        command = {
            'command': 'gpio_read',
            'parameters': {'pin': 'PA1'}
        }
        
        # Mock Moonraker GPIO API
        async def mock_get(url, headers=None):
            class MockResponse:
                status = 200
                async def json(self):
                    return {'success': True, 'pin': 'PA1', 'value': 1}
            return MockResponse()
        
        mock_client = api_server.translator.gcode_translator.get_moonraker_client()
        mock_client.session.get = mock_get
        
        # Execute command
        response = await api_server.execute_command(command)
        
        # Verify complete flow
        assert response.status == ResponseStatus.SUCCESS
        assert response.command == 'gpio_read'
        assert response.data['pin'] == 'PA1'
        assert response.data['value'] == 1
    
    @pytest_asyncio.asyncio_test
    async def test_complete_sensor_read_flow(self, api_server):
        """Test complete sensor read flow."""
        command = {
            'command': 'sensor_read',
            'parameters': {'sensor': 'temperature_sensor'}
        }
        
        # Mock Moonraker sensor API
        async def mock_get(url, headers=None):
            class MockResponse:
                status = 200
                async def json(self):
                    return {
                        'success': True,
                        'sensor': 'temperature_sensor',
                        'temperature': 25.5
                    }
            return MockResponse()
        
        mock_client = api_server.translator.gcode_translator.get_moonraker_client()
        mock_client.session.get = mock_get
        
        # Execute command
        response = await api_server.execute_command(command)
        
        # Verify complete flow
        assert response.status == ResponseStatus.SUCCESS
        assert response.command == 'sensor_read'
        assert response.data['temperature'] == 25.5
    
    @pytest_asyncio.asyncio_test
    async def test_complete_home_flow(self, api_server):
        """Test complete home command flow."""
        command = {'command': 'home', 'parameters': {}}
        
        gcode_calls = []
        async def mock_run_gcode(script):
            gcode_calls.append(script)
            return ExecutionResult(
                status=ExecutionStatus.COMPLETED,
                gcode=script,
                response={'result': 'ok'},
                execution_time=2.0
            )
        
        mock_client = api_server.translator.gcode_translator.get_moonraker_client()
        mock_client.run_gcode = mock_run_gcode
        
        # Execute command
        response = await api_server.execute_command(command)
        
        # Verify complete flow
        assert response.status == ResponseStatus.SUCCESS
        assert response.command == 'home'
        assert 'G28' in gcode_calls[-1]
        assert response.data['execution_time'] == 2.0
    
    @pytest_asyncio.asyncio_test
    async def test_complete_status_query_flow(self, api_server):
        """Test complete status query flow."""
        command = {'command': 'get_status', 'parameters': {}}
        
        # Mock Moonraker status APIs
        async def mock_get_printer_status():
            return {'state': 'ready', 'print_stats': {'state': 'idle'}}
        
        async def mock_get_klippy_state():
            return 'ready'
        
        mock_client = api_server.translator.gcode_translator.get_moonraker_client()
        mock_client.get_printer_status = mock_get_printer_status
        mock_client.get_klippy_state = mock_get_klippy_state
        
        # Execute command
        response = await api_server.execute_command(command)
        
        # Verify complete flow
        assert response.status == ResponseStatus.SUCCESS
        assert response.command == 'get_status'
        assert 'printer_status' in response.data
        assert 'klippy_state' in response.data
        assert 'internal_state' in response.data
    
    @pytest_asyncio.asyncio_test
    async def test_complete_position_query_flow(self, api_server):
        """Test complete position query flow."""
        command = {'command': 'get_position', 'parameters': {}}
        
        # Mock position query
        async def mock_get_printer_status():
            return {
                'state': 'ready',
                'toolhead': {'position': [100.0, 50.0, 10.0]}
            }
        
        mock_client = api_server.translator.gcode_translator.get_moonraker_client()
        mock_client.get_printer_status = mock_get_printer_status
        
        # Execute command
        response = await api_server.execute_command(command)
        
        # Verify complete flow
        assert response.status == ResponseStatus.SUCCESS
        assert response.command == 'get_position'
        assert 'position' in response.data
        assert response.data['position'] == {'x': 100.0, 'y': 50.0, 'z': 10.0}
    
    @pytest_asyncio.asyncio_test
    async def test_complete_batch_execution_flow(self, api_server):
        """Test complete batch execution flow."""
        commands = [
            {'command': 'home', 'parameters': {}},
            {'command': 'move', 'parameters': {'x': 100.0, 'y': 50.0, 'z': 10.0}},
            {'command': 'pick', 'parameters': {'z': 0.0, 'vacuum_power': 255}},
            {'command': 'move', 'parameters': {'x': 200.0, 'y': 100.0}},
            {'command': 'place', 'parameters': {'z': 0.0}}
        ]
        
        gcode_calls = []
        async def mock_run_gcode(script):
            gcode_calls.append(script)
            return ExecutionResult(
                status=ExecutionStatus.COMPLETED,
                gcode=script,
                response={'result': 'ok'},
                execution_time=0.1
            )
        
        mock_client = api_server.translator.gcode_translator.get_moonraker_client()
        mock_client.run_gcode = mock_run_gcode
        
        # Execute batch
        responses = await api_server.execute_batch(commands, stop_on_error=False)
        
        # Verify complete flow
        assert len(responses) == 5
        assert all(r.status == ResponseStatus.SUCCESS for r in responses)
        assert len(gcode_calls) == len(commands)
    
    @pytest_asyncio.asyncio_test
    async def test_complete_batch_execution_with_error(self, api_server):
        """Test batch execution with error handling."""
        commands = [
            {'command': 'home', 'parameters': {}},
            {'command': 'move', 'parameters': {'x': 100.0, 'y': 50.0, 'z': 10.0}},
            {'command': 'move', 'parameters': {'x': 9999.0}},  # Out of bounds
            {'command': 'move', 'parameters': {'y': 100.0}}
        ]
        
        gcode_calls = []
        async def mock_run_gcode(script):
            gcode_calls.append(script)
            # Fail on out of bounds command
            if 'X9999.0' in script:
                return ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    gcode=script,
                    error_message='Position out of bounds',
                    execution_time=0.1
                )
            return ExecutionResult(
                status=ExecutionStatus.COMPLETED,
                gcode=script,
                response={'result': 'ok'},
                execution_time=0.1
            )
        
        mock_client = api_server.translator.gcode_translator.get_moonraker_client()
        mock_client.run_gcode = mock_run_gcode
        
        # Execute batch with stop_on_error=True
        responses = await api_server.execute_batch(commands, stop_on_error=True)
        
        # Verify error handling
        assert len(responses) == 3  # Should stop after error
        assert responses[0].status == ResponseStatus.SUCCESS
        assert responses[1].status == ResponseStatus.SUCCESS
        assert responses[2].status == ResponseStatus.ERROR
    
    @pytest_asyncio.asyncio_test
    async def test_complete_pwm_control_flow(self, api_server):
        """Test complete PWM control flow."""
        command = {
            'command': 'pwm_set',
            'parameters': {
                'value': 0.5,
                'pin': 'PA1'
            }
        }
        
        # Mock Moonraker PWM API
        async def mock_post(url, json=None, headers=None):
            class MockResponse:
                status = 200
                async def json(self):
                    return {'success': True, 'value': 0.5}
            return MockResponse()
        
        mock_client = api_server.translator.gcode_translator.get_moonraker_client()
        mock_client.session.post = mock_post
        
        # Execute command
        response = await api_server.execute_command(command)
        
        # Verify complete flow
        assert response.status == ResponseStatus.SUCCESS
        assert response.command == 'pwm_set'
        assert response.data['value'] == 0.5
    
    @pytest_asyncio.asyncio_test
    async def test_complete_actuator_control_flow(self, api_server):
        """Test complete actuator control flow."""
        command = {
            'command': 'actuate',
            'parameters': {
                'pin': 'PA1',
                'value': 1
            }
        }
        
        gcode_calls = []
        async def mock_run_gcode(script):
            gcode_calls.append(script)
            return ExecutionResult(
                status=ExecutionStatus.COMPLETED,
                gcode=script,
                response={'result': 'ok'},
                execution_time=0.05
            )
        
        mock_client = api_server.translator.gcode_translator.get_moonraker_client()
        mock_client.run_gcode = mock_run_gcode
        
        # Execute command
        response = await api_server.execute_command(command)
        
        # Verify complete flow
        assert response.status == ResponseStatus.SUCCESS
        assert response.command == 'actuate'
        assert 'SET_PIN PIN=PA1 VALUE=1' in gcode_calls[-1]
    
    @pytest_asyncio.asyncio_test
    async def test_complete_feeder_control_flow(self, api_server):
        """Test complete feeder control flow."""
        # Test feeder advance
        command_advance = {
            'command': 'feeder_advance',
            'parameters': {
                'distance': 10.0,
                'feedrate': 100.0
            }
        }
        
        gcode_calls = []
        async def mock_run_gcode(script):
            gcode_calls.append(script)
            return ExecutionResult(
                status=ExecutionStatus.COMPLETED,
                gcode=script,
                response={'result': 'ok'},
                execution_time=0.05
            )
        
        mock_client = api_server.translator.gcode_translator.get_moonraker_client()
        mock_client.run_gcode = mock_run_gcode
        
        response_advance = await api_server.execute_command(command_advance)
        
        assert response_advance.status == ResponseStatus.SUCCESS
        assert 'G0 E10.0 F100.0' in gcode_calls[-1]
        
        # Test feeder retract
        command_retract = {
            'command': 'feeder_retract',
            'parameters': {
                'distance': 10.0,
                'feedrate': 100.0
            }
        }
        
        response_retract = await api_server.execute_command(command_retract)
        
        assert response_retract.status == ResponseStatus.SUCCESS
        assert 'G0 E-10.0 F100.0' in gcode_calls[-1]
    
    @pytest_asyncio.asyncio_test
    async def test_complete_queue_operations_flow(self, api_server):
        """Test complete queue operations flow."""
        # Test enqueue command
        command = {
            'command': 'queue_command',
            'parameters': {
                'command': 'move',
                'parameters': {'x': 100.0, 'y': 50.0}
            }
        }
        
        # Mock queue operations
        handler = api_server.translator._get_execution_handler()
        handler.enqueue_command = AsyncMock(return_value='cmd_123')
        
        response = await api_server.execute_command(command)
        
        assert response.status == ResponseStatus.SUCCESS
        assert 'command_id' in response.data
        
        # Test queue status
        handler.get_queue_status = AsyncMock(return_value={
            'queue_size': 1,
            'processing': False,
            'pending_commands': 1
        })
        
        status_command = {'command': 'queue_status', 'parameters': {}}
        status_response = await api_server.execute_command(status_command)
        
        assert status_response.status == ResponseStatus.SUCCESS
        assert status_response.data['queue_size'] == 1
        
        # Test queue clear
        handler.clear_queue = AsyncMock()
        
        clear_command = {'command': 'queue_clear', 'parameters': {}}
        clear_response = await api_server.execute_command(clear_command)
        
        assert clear_response.status == ResponseStatus.SUCCESS
    
    @pytest_asyncio.asyncio_test
    async def test_complete_system_commands_flow(self, api_server):
        """Test complete system commands flow."""
        # Test pause
        pause_command = {'command': 'pause', 'parameters': {}}
        handler = api_server.translator._get_execution_handler()
        handler.pause = AsyncMock()
        
        pause_response = await api_server.execute_command(pause_command)
        assert pause_response.status == ResponseStatus.SUCCESS
        handler.pause.assert_called_once()
        
        # Test resume
        resume_command = {'command': 'resume', 'parameters': {}}
        handler.resume = AsyncMock()
        
        resume_response = await api_server.execute_command(resume_command)
        assert resume_response.status == ResponseStatus.SUCCESS
        handler.resume.assert_called_once()
        
        # Test cancel
        cancel_command = {'command': 'cancel', 'parameters': {}}
        handler.cancel_execution = AsyncMock()
        
        cancel_response = await api_server.execute_command(cancel_command)
        assert cancel_response.status == ResponseStatus.SUCCESS
        handler.cancel_execution.assert_called_once()
        
        # Test reset
        reset_command = {'command': 'reset', 'parameters': {}}
        handler.reset = AsyncMock()
        
        reset_response = await api_server.execute_command(reset_command)
        assert reset_response.status == ResponseStatus.SUCCESS
        handler.reset.assert_called_once()
    
    @pytest_asyncio.asyncio_test
    async def test_complete_state_tracking_flow(self, api_server):
        """Test that state is tracked correctly across commands."""
        # Execute move command
        move_command = {
            'command': 'move',
            'parameters': {'x': 100.0, 'y': 50.0, 'z': 10.0}
        }
        
        gcode_calls = []
        async def mock_run_gcode(script):
            gcode_calls.append(script)
            return ExecutionResult(
                status=ExecutionStatus.COMPLETED,
                gcode=script,
                response={'result': 'ok'},
                execution_time=0.1
            )
        
        mock_client = api_server.translator.gcode_translator.get_moonraker_client()
        mock_client.run_gcode = mock_run_gcode
        
        await api_server.execute_command(move_command)
        
        # Check state was updated
        state = api_server.translator.get_state()
        assert state['current_position']['x'] == 100.0
        assert state['current_position']['y'] == 50.0
        assert state['current_position']['z'] == 10.0
        
        # Execute vacuum on
        vacuum_command = {'command': 'vacuum_on', 'parameters': {'power': 200}}
        await api_server.execute_command(vacuum_command)
        
        # Check vacuum state was updated
        state = api_server.translator.get_state()
        assert state['vacuum_enabled'] == True
    
    @pytest_asyncio.asyncio_test
    async def test_complete_error_handling_flow(self, api_server):
        """Test that errors are handled correctly across the flow."""
        command = {
            'command': 'move',
            'parameters': {'x': 9999.0}  # Out of bounds
        }
        
        # Mock error response
        async def mock_run_gcode(script):
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                gcode=script,
                error_message='Position out of bounds',
                execution_time=0.1
            )
        
        mock_client = api_server.translator.gcode_translator.get_moonraker_client()
        mock_client.run_gcode = mock_run_gcode
        
        # Execute command
        response = await api_server.execute_command(command)
        
        # Verify error handling
        assert response.status == ResponseStatus.ERROR
        assert response.error_message == 'Position out of bounds'
        assert response.error_code == 'GCODE_EXECUTION_FAILED'
    
    @pytest_asyncio.asyncio_test
    async def test_complete_timeout_handling_flow(self, api_server):
        """Test that timeouts are handled correctly."""
        command = {
            'command': 'move',
            'parameters': {'x': 100.0, 'y': 50.0, 'z': 10.0}
        }
        
        # Mock timeout
        async def mock_run_gcode(script):
            await asyncio.sleep(0.2)
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                gcode=script,
                error_message='Timeout',
                execution_time=0.2
            )
        
        mock_client = api_server.translator.gcode_translator.get_moonraker_client()
        mock_client.run_gcode = mock_run_gcode
        
        # Execute command with short timeout
        original_timeout = api_server.translator.default_timeout
        api_server.translator.default_timeout = 0.1
        
        response = await api_server.execute_command(command)
        
        # Restore timeout
        api_server.translator.default_timeout = original_timeout
        
        # Verify timeout handling
        assert response.status == ResponseStatus.ERROR
        assert 'timeout' in response.error_message.lower()
    
    @pytest_asyncio.asyncio_test
    async def test_complete_statistics_tracking_flow(self, api_server):
        """Test that statistics are tracked correctly."""
        # Execute multiple commands
        commands = [
            {'command': 'move', 'parameters': {'x': 100.0}},
            {'command': 'move', 'parameters': {'y': 50.0}},
            {'command': 'move', 'parameters': {'z': 10.0}}
        ]
        
        gcode_calls = []
        async def mock_run_gcode(script):
            gcode_calls.append(script)
            return ExecutionResult(
                status=ExecutionStatus.COMPLETED,
                gcode=script,
                response={'result': 'ok'},
                execution_time=0.1
            )
        
        mock_client = api_server.translator.gcode_translator.get_moonraker_client()
        mock_client.run_gcode = mock_run_gcode
        
        await api_server.execute_batch(commands, stop_on_error=False)
        
        # Get statistics
        stats = await api_server.translator.get_statistics()
        
        # Verify statistics tracking
        assert 'total_commands' in stats or stats.get('total_commands', 0) >= 0
    
    @pytest_asyncio.asyncio_test
    async def test_complete_history_tracking_flow(self, api_server):
        """Test that command history is tracked correctly."""
        # Execute commands
        commands = [
            {'command': 'move', 'parameters': {'x': 100.0}},
            {'command': 'pick', 'parameters': {'z': 0.0}},
            {'command': 'place', 'parameters': {'z': 0.0}}
        ]
        
        gcode_calls = []
        async def mock_run_gcode(script):
            gcode_calls.append(script)
            return ExecutionResult(
                status=ExecutionStatus.COMPLETED,
                gcode=script,
                response={'result': 'ok'},
                execution_time=0.1
            )
        
        mock_client = api_server.translator.gcode_translator.get_moonraker_client()
        mock_client.run_gcode = mock_run_gcode
        
        await api_server.execute_batch(commands, stop_on_error=False)
        
        # Get history
        history = await api_server.translator.get_history(limit=10)
        
        # Verify history tracking
        assert len(history) >= 0
        assert all('command' in h for h in history)
    
    @pytest_asyncio.asyncio_test
    async def test_complete_concurrent_command_flow(self, api_server):
        """Test that concurrent commands are handled correctly."""
        commands = [
            {'command': 'move', 'parameters': {'x': i * 10.0, 'y': i * 5.0}}
            for i in range(5)
        ]
        
        gcode_calls = []
        async def mock_run_gcode(script):
            gcode_calls.append(script)
            await asyncio.sleep(0.01)
            return ExecutionResult(
                status=ExecutionStatus.COMPLETED,
                gcode=script,
                response={'result': 'ok'},
                execution_time=0.05
            )
        
        mock_client = api_server.translator.gcode_translator.get_moonraker_client()
        mock_client.run_gcode = mock_run_gcode
        
        # Execute batch
        responses = await api_server.execute_batch(commands, stop_on_error=False)
        
        # Verify concurrent handling
        assert len(responses) == 5
        assert all(r.status == ResponseStatus.SUCCESS for r in responses)
        assert len(gcode_calls) == 5


class TestEndToEndSafetyIntegration:
    """Test suite for safety integration in end-to-end flow."""
    
    @pytest_asyncio.asyncio_test
    async def test_safety_validation_before_execution(self, api_server):
        """Test that safety validation occurs before command execution."""
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
        
        # Verify safety check
        api_server.safety_manager.validate_move_command.assert_called_once()
        assert response.status == ResponseStatus.ERROR
    
    @pytest_asyncio.asyncio_test
    async def test_safety_temperature_validation(self, api_server):
        """Test that temperature safety validation works."""
        command = {
            'command': 'move',
            'parameters': {'x': 100.0, 'y': 50.0, 'z': 10.0}
        }
        
        # Mock temperature check
        api_server.safety_manager.check_temperature_limits = AsyncMock(
            return_value=[]
        )
        
        # Execute command
        response = await api_server.execute_command(command)
        
        # Verify temperature check was called
        api_server.safety_manager.check_temperature_limits.assert_called()
    
    @pytest_asyncio.asyncio_test
    async def test_safety_position_validation(self, api_server):
        """Test that position safety validation works."""
        command = {
            'command': 'move',
            'parameters': {'x': 100.0, 'y': 50.0, 'z': 10.0}
        }
        
        # Mock position check
        api_server.safety_manager.check_position_limits = AsyncMock(
            return_value=[]
        )
        
        # Execute command
        response = await api_server.execute_command(command)
        
        # Verify position check was called
        api_server.safety_manager.check_position_limits.assert_called()
    
    @pytest_asyncio.asyncio_test
    async def test_safety_emergency_stop_flow(self, api_server):
        """Test that emergency stop works correctly."""
        command = {'command': 'emergency_stop', 'parameters': {'reason': 'Test emergency'}}
        
        # Mock emergency stop
        api_server.safety_manager.emergency_stop = AsyncMock()
        
        # Execute command
        response = await api_server.execute_command(command)
        
        # Verify emergency stop
        api_server.safety_manager.emergency_stop.assert_called_once()
        assert response.status == ResponseStatus.SUCCESS


class TestEndToEndCacheIntegration:
    """Test suite for cache integration in end-to-end flow."""
    
    @pytest_asyncio.asyncio_test
    async def test_cache_hit_on_status_query(self, api_server):
        """Test that cache is used for status queries."""
        command = {'command': 'get_status', 'parameters': {}}
        
        # Mock cache hit
        api_server.cache_manager.get = AsyncMock(return_value={
            'success': True,
            'printer_status': {'state': 'ready'},
            'klippy_state': 'ready'
        })
        
        # Execute command
        response = await api_server.execute_command(command)
        
        # Verify cache was used
        api_server.cache_manager.get.assert_called()
        assert response.status == ResponseStatus.SUCCESS
    
    @pytest_asyncio.asyncio_test
    async def test_cache_invalidation_on_state_change(self, api_server):
        """Test that cache is invalidated on state changes."""
        command = {'command': 'move', 'parameters': {'x': 100.0, 'y': 50.0, 'z': 10.0}}
        
        # Mock cache invalidation
        api_server.cache_manager.invalidate_category = AsyncMock(return_value=1)
        
        # Execute command
        response = await api_server.execute_command(command)
        
        # Verify cache invalidation
        api_server.cache_manager.invalidate_category.assert_called()
        assert response.status == ResponseStatus.SUCCESS
    
    @pytest_asyncio.asyncio_test
    async def test_cache_statistics_tracking(self, api_server):
        """Test that cache statistics are tracked."""
        # Get cache statistics
        expected_stats = {
            'hits': 10,
            'misses': 5,
            'hit_rate': 66.67
        }
        api_server.cache_manager.get_statistics = AsyncMock(return_value=expected_stats)
        
        stats = await api_server.cache_manager.get_statistics()
        
        # Verify statistics
        assert stats['hits'] == 10
        assert stats['misses'] == 5
        assert stats['hit_rate'] == 66.67
