#!/usr/bin/env python3
# Test suite for OpenPNP Translator

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from middleware.translator import (
    OpenPNPCommandType,
    ResponseStatus,
    OpenPNPResponse,
    OpenPNPCommand,
    TranslationStrategy,
    OpenPNPTranslator,
    execute_openpnp_command,
    execute_openpnp_batch,
    create_translator
)

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class TestResults:
    """Track test results."""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def record_pass(self, test_name):
        """Record a passed test."""
        self.passed += 1
        logger.info(f"✓ PASS: {test_name}")
    
    def record_fail(self, test_name, error):
        """Record a failed test."""
        self.failed += 1
        self.errors.append((test_name, error))
        logger.error(f"✗ FAIL: {test_name} - {error}")
    
    def summary(self):
        """Print test summary."""
        total = self.passed + self.failed
        logger.info(f"\n{'='*60}")
        logger.info(f"Test Summary: {self.passed}/{total} passed")
        logger.info(f"{'='*60}")
        if self.failed > 0:
            logger.error(f"\nFailed tests:")
            for test_name, error in self.errors:
                logger.error(f"  - {test_name}: {error}")
        return self.failed == 0


async def test_command_parsing():
    """Test OpenPNP command parsing."""
    results = TestResults()
    
    # Test 1: Parse command from dictionary
    try:
        cmd_dict = {
            'command': 'move',
            'parameters': {'x': 100.0, 'y': 50.0, 'z': 10.0, 'feedrate': 1500.0},
            'priority': 1
        }
        translator = create_translator()
        command = translator._parse_command_dict(cmd_dict)
        
        assert command.command_type == OpenPNPCommandType.MOVE
        assert command.parameters['x'] == 100.0
        assert command.parameters['y'] == 50.0
        assert command.priority == 1
        
        results.record_pass("Command parsing from dictionary")
    except Exception as e:
        results.record_fail("Command parsing from dictionary", str(e))
    
    # Test 2: Parse unknown command type
    try:
        cmd_dict = {'command': 'unknown_command'}
        translator = create_translator()
        
        try:
            command = translator._parse_command_dict(cmd_dict)
            results.record_fail("Unknown command type validation", "Should have raised ValueError")
        except ValueError:
            results.record_pass("Unknown command type validation")
    except Exception as e:
        results.record_fail("Unknown command type validation", str(e))
    
    return results


async def test_gcode_translation():
    """Test G-code translation."""
    results = TestResults()
    translator = create_translator()
    
    # Test 1: Move command translation
    try:
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.MOVE,
            parameters={'x': 100.0, 'y': 50.0, 'z': 10.0, 'feedrate': 1500.0}
        )
        gcode = translator._convert_to_gcode(command)
        
        assert 'X100.0' in gcode
        assert 'Y50.0' in gcode
        assert 'Z10.0' in gcode
        assert 'F1500.0' in gcode
        
        results.record_pass("Move command G-code translation")
    except Exception as e:
        results.record_fail("Move command G-code translation", str(e))
    
    # Test 2: Pick command translation
    try:
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.PICK,
            parameters={'pick_height': 0.0, 'vacuum_power': 255, 'travel_height': 5.0}
        )
        gcode = translator._convert_to_gcode(command)
        
        assert 'Z0.0' in gcode
        assert 'M106 S255' in gcode
        assert 'Z5.0' in gcode
        
        results.record_pass("Pick command G-code translation")
    except Exception as e:
        results.record_fail("Pick command G-code translation", str(e))
    
    # Test 3: Place command translation
    try:
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.PLACE,
            parameters={'place_height': 0.0, 'travel_height': 5.0}
        )
        gcode = translator._convert_to_gcode(command)
        
        assert 'Z0.0' in gcode
        assert 'M107' in gcode
        assert 'Z5.0' in gcode
        
        results.record_pass("Place command G-code translation")
    except Exception as e:
        results.record_fail("Place command G-code translation", str(e))
    
    # Test 4: Actuator command translation
    try:
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.ACTUATE,
            parameters={'pin': 'vacuum_pump', 'value': 1}
        )
        gcode = translator._convert_to_gcode(command)
        
        assert 'SET_PIN PIN=vacuum_pump VALUE=1' in gcode
        
        results.record_pass("Actuator command G-code translation")
    except Exception as e:
        results.record_fail("Actuator command G-code translation", str(e))
    
    # Test 5: Vacuum command translation
    try:
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.VACUUM_ON,
            parameters={'power': 200}
        )
        gcode = translator._convert_to_gcode(command)
        
        assert 'M106 S200' in gcode
        
        results.record_pass("Vacuum command G-code translation")
    except Exception as e:
        results.record_fail("Vacuum command G-code translation", str(e))
    
    # Test 6: Home command translation
    try:
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.HOME,
            parameters={'axes': 'X Y'}
        )
        gcode = translator._convert_to_gcode(command)
        
        assert 'G28 X Y' in gcode
        
        results.record_pass("Home command G-code translation")
    except Exception as e:
        results.record_fail("Home command G-code translation", str(e))
    
    return results


async def test_strategy_mapping():
    """Test translation strategy mapping."""
    results = TestResults()
    translator = create_translator()
    
    # Test 1: Direct API strategy for GPIO read
    try:
        strategy = translator._get_strategy(OpenPNPCommandType.GPIO_READ)
        assert strategy == TranslationStrategy.DIRECT_API
        results.record_pass("GPIO read strategy mapping")
    except Exception as e:
        results.record_fail("GPIO read strategy mapping", str(e))
    
    # Test 2: G-code strategy for move
    try:
        strategy = translator._get_strategy(OpenPNPCommandType.MOVE)
        assert strategy == TranslationStrategy.GCODE
        results.record_pass("Move strategy mapping")
    except Exception as e:
        results.record_fail("Move strategy mapping", str(e))
    
    # Test 3: Hybrid strategy for status
    try:
        strategy = translator._get_strategy(OpenPNPCommandType.GET_STATUS)
        assert strategy == TranslationStrategy.HYBRID
        results.record_pass("Status strategy mapping")
    except Exception as e:
        results.record_fail("Status strategy mapping", str(e))
    
    return results


async def test_response_format():
    """Test unified response format."""
    results = TestResults()
    
    # Test 1: Success response
    try:
        response = OpenPNPResponse(
            status=ResponseStatus.SUCCESS,
            command='move',
            data={'x': 100.0, 'y': 50.0}
        )
        
        response_dict = response.to_dict()
        
        assert response_dict['status'] == 'success'
        assert response_dict['command'] == 'move'
        assert response_dict['data']['x'] == 100.0
        assert 'command_id' in response_dict
        assert 'execution_time' in response_dict
        assert 'timestamp' in response_dict
        
        results.record_pass("Success response format")
    except Exception as e:
        results.record_fail("Success response format", str(e))
    
    # Test 2: Error response
    try:
        response = OpenPNPResponse(
            status=ResponseStatus.ERROR,
            command='move',
            error_message='Invalid parameter',
            error_code='INVALID_PARAM'
        )
        
        response_dict = response.to_dict()
        
        assert response_dict['status'] == 'error'
        assert response_dict['error_message'] == 'Invalid parameter'
        assert response_dict['error_code'] == 'INVALID_PARAM'
        
        results.record_pass("Error response format")
    except Exception as e:
        results.record_fail("Error response format", str(e))
    
    # Test 3: Warning addition
    try:
        response = OpenPNPResponse(
            status=ResponseStatus.SUCCESS,
            command='move'
        )
        response.add_warning('Deprecated parameter used')
        
        assert len(response.warnings) == 1
        assert 'Deprecated parameter used' in response.warnings[0]
        
        results.record_pass("Warning addition to response")
    except Exception as e:
        results.record_fail("Warning addition to response", str(e))
    
    return results


async def test_state_management():
    """Test internal state management."""
    results = TestResults()
    translator = create_translator()
    
    # Test 1: Initial state
    try:
        state = translator.get_state()
        
        assert 'current_position' in state
        assert 'vacuum_enabled' in state
        assert 'fan_speed' in state
        assert 'actuators' in state
        
        results.record_pass("Initial state structure")
    except Exception as e:
        results.record_fail("Initial state structure", str(e))
    
    # Test 2: State update on vacuum on
    try:
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.VACUUM_ON,
            parameters={}
        )
        response = OpenPNPResponse(
            status=ResponseStatus.SUCCESS,
            command='vacuum_on'
        )
        translator._update_state(command, response)
        
        state = translator.get_state()
        assert state['vacuum_enabled'] == True
        
        results.record_pass("State update on vacuum on")
    except Exception as e:
        results.record_fail("State update on vacuum on", str(e))
    
    # Test 3: State update on vacuum off
    try:
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.VACUUM_OFF,
            parameters={}
        )
        response = OpenPNPResponse(
            status=ResponseStatus.SUCCESS,
            command='vacuum_off'
        )
        translator._update_state(command, response)
        
        state = translator.get_state()
        assert state['vacuum_enabled'] == False
        
        results.record_pass("State update on vacuum off")
    except Exception as e:
        results.record_fail("State update on vacuum off", str(e))
    
    # Test 4: State reset
    try:
        translator._state['vacuum_enabled'] = True
        translator._state['fan_speed'] = 0.5
        
        translator.reset_state()
        
        state = translator.get_state()
        assert state['vacuum_enabled'] == False
        assert state['fan_speed'] == 0.0
        
        results.record_pass("State reset")
    except Exception as e:
        results.record_fail("State reset", str(e))
    
    return results


async def test_command_types():
    """Test OpenPNP command type enumeration."""
    results = TestResults()
    
    # Test 1: Motion command types
    try:
        assert OpenPNPCommandType.MOVE.value == 'move'
        assert OpenPNPCommandType.HOME.value == 'home'
        assert OpenPNPCommandType.PICK.value == 'pick'
        assert OpenPNPCommandType.PLACE.value == 'place'
        
        results.record_pass("Motion command types")
    except Exception as e:
        results.record_fail("Motion command types", str(e))
    
    # Test 2: Actuator command types
    try:
        assert OpenPNPCommandType.ACTUATE.value == 'actuate'
        assert OpenPNPCommandType.VACUUM_ON.value == 'vacuum_on'
        assert OpenPNPCommandType.FAN_ON.value == 'fan_on'
        
        results.record_pass("Actuator command types")
    except Exception as e:
        results.record_fail("Actuator command types", str(e))
    
    # Test 3: System command types
    try:
        assert OpenPNPCommandType.GET_STATUS.value == 'get_status'
        assert OpenPNPCommandType.CANCEL.value == 'cancel'
        assert OpenPNPCommandType.PAUSE.value == 'pause'
        assert OpenPNPCommandType.RESET.value == 'reset'
        
        results.record_pass("System command types")
    except Exception as e:
        results.record_fail("System command types", str(e))
    
    return results


async def test_batch_operations():
    """Test batch command operations."""
    results = TestResults()
    translator = create_translator()
    
    # Test 1: Create batch commands
    try:
        commands = [
            OpenPNPCommand(
                command_type=OpenPNPCommandType.MOVE,
                parameters={'x': 100.0, 'y': 50.0}
            ),
            OpenPNPCommand(
                command_type=OpenPNPCommandType.MOVE,
                parameters={'z': 10.0}
            ),
            OpenPNPCommand(
                command_type=OpenPNPCommandType.HOME
            )
        ]
        
        assert len(commands) == 3
        
        results.record_pass("Batch command creation")
    except Exception as e:
        results.record_fail("Batch command creation", str(e))
    
    # Test 2: Command with priority
    try:
        high_priority = OpenPNPCommand(
            command_type=OpenPNPCommandType.MOVE,
            parameters={'x': 100.0},
            priority=10
        )
        low_priority = OpenPNPCommand(
            command_type=OpenPNPCommandType.MOVE,
            parameters={'x': 200.0},
            priority=1
        )
        
        assert high_priority.priority == 10
        assert low_priority.priority == 1
        
        results.record_pass("Command with priority")
    except Exception as e:
        results.record_fail("Command with priority", str(e))
    
    # Test 3: Command with metadata
    try:
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.MOVE,
            parameters={'x': 100.0},
            metadata={'source': 'test', 'user': 'test_user'}
        )
        
        assert command.metadata['source'] == 'test'
        assert command.metadata['user'] == 'test_user'
        
        results.record_pass("Command with metadata")
    except Exception as e:
        results.record_fail("Command with metadata", str(e))
    
    return results


async def test_custom_templates():
    """Test custom template addition."""
    results = TestResults()
    translator = create_translator()
    
    # Test 1: Add custom template
    try:
        translator.add_custom_template(
            'custom_move',
            'G0 X{x} Y{y} F{feedrate} ; Custom move'
        )
        
        templates = translator.gcode_translator.get_templates()
        assert 'custom_move' in templates
        
        results.record_pass("Add custom template")
    except Exception as e:
        results.record_fail("Add custom template", str(e))
    
    # Test 2: Add custom validator
    try:
        def custom_validator(value):
            return isinstance(value, (int, float)) and 0 <= value <= 1000
        
        translator.add_custom_validator('custom_param', custom_validator)
        
        assert 'custom_param' in translator.gcode_translator.validators
        
        results.record_pass("Add custom validator")
    except Exception as e:
        results.record_fail("Add custom validator", str(e))
    
    return results


async def run_all_tests():
    """Run all test suites."""
    logger.info("Starting OpenPNP Translator Test Suite")
    logger.info("="*60)
    
    all_passed = True
    
    # Run test suites
    test_suites = [
        ("Command Parsing", test_command_parsing),
        ("G-code Translation", test_gcode_translation),
        ("Strategy Mapping", test_strategy_mapping),
        ("Response Format", test_response_format),
        ("State Management", test_state_management),
        ("Command Types", test_command_types),
        ("Batch Operations", test_batch_operations),
        ("Custom Templates", test_custom_templates)
    ]
    
    for suite_name, test_func in test_suites:
        logger.info(f"\n\nRunning: {suite_name}")
        logger.info("-"*60)
        results = await test_func()
        if not results.summary():
            all_passed = False
    
    # Final summary
    logger.info("\n\n" + "="*60)
    if all_passed:
        logger.info("✓ ALL TESTS PASSED")
        logger.info("="*60)
        return 0
    else:
        logger.error("✗ SOME TESTS FAILED")
        logger.error("="*60)
        return 1


if __name__ == '__main__':
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
