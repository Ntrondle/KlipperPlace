#!/usr/bin/env python3
# Test suite for G-code Translator

import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from gcode_driver.translator import (
    CommandTranslator,
    MoonrakerClient,
    TranslationContext,
    ExecutionResult,
    ExecutionStatus,
    create_translator,
    translate_and_execute
)
from gcode_driver.parser import GCodeCommand, GCodeCommandType, GCodeParameter

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set UTF-8 encoding for stdout
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def test_translator_initialization():
    """Test translator initialization."""
    print("\n=== Test: Translator Initialization ===")
    
    # Test basic initialization
    translator = CommandTranslator()
    assert translator is not None
    assert translator.context is not None
    assert len(translator.templates) > 0
    assert len(translator.validators) > 0
    
    print("✓ Basic initialization successful")
    
    # Test initialization with config
    config = {
        'context_defaults': {
            'feedrate': 2000.0,
            'units': 'mm'
        },
        'templates': {
            'custom_move': 'G0 X{x} Y{y} F{feedrate}'
        }
    }
    
    translator_with_config = CommandTranslator(config=config)
    assert translator_with_config.context.feedrate == 2000.0
    assert 'custom_move' in translator_with_config.templates
    
    print("✓ Initialization with config successful")
    
    print("✓ All initialization tests passed")


def test_command_translation():
    """Test basic command translation."""
    print("\n=== Test: Command Translation ===")
    
    translator = CommandTranslator()
    
    # Test standard G-code (should pass through)
    standard_cmd = GCodeCommand(
        command_type=GCodeCommandType.G0,
        raw_command="G0 X100 Y50 F1500",
        parameters=[
            GCodeParameter(name='X', value=100.0, raw_value='100'),
            GCodeParameter(name='Y', value=50.0, raw_value='50'),
            GCodeParameter(name='F', value=1500.0, raw_value='1500')
        ]
    )
    
    result = translator.translate_command(standard_cmd)
    assert result.success is True
    assert len(result.translated_commands) == 1
    assert result.translated_commands[0] == "G0 X100 Y50 F1500"
    
    print("✓ Standard G-code translation successful")
    
    # Test OpenPNP vacuum command
    vacuum_cmd = GCodeCommand(
        command_type=GCodeCommandType.OPENPNP_VACUUM_ON,
        raw_command="OPENPNP_VACUUM_ON",
        parameters=[]
    )
    
    result = translator.translate_command(vacuum_cmd)
    assert result.success is True
    assert len(result.translated_commands) == 1
    assert "M106" in result.translated_commands[0]
    
    print("✓ OpenPNP vacuum translation successful")
    
    # Test OpenPNP move command
    move_cmd = GCodeCommand(
        command_type=GCodeCommandType.OPENPNP_MOVE,
        raw_command="OPENPNP_MOVE X100 Y50 Z10 F1500",
        parameters=[
            GCodeParameter(name='X', value=100.0, raw_value='100'),
            GCodeParameter(name='Y', value=50.0, raw_value='50'),
            GCodeParameter(name='Z', value=10.0, raw_value='10'),
            GCodeParameter(name='F', value=1500.0, raw_value='1500')
        ]
    )
    
    result = translator.translate_command(move_cmd)
    assert result.success is True
    assert len(result.translated_commands) >= 1
    assert any("G0" in cmd for cmd in result.translated_commands)
    
    print("✓ OpenPNP move translation successful")
    
    print("✓ All command translation tests passed")


def test_parameter_validation():
    """Test parameter validation."""
    print("\n=== Test: Parameter Validation ===")
    
    translator = CommandTranslator()
    
    # Test valid parameters
    valid_cmd = GCodeCommand(
        command_type=GCodeCommandType.OPENPNP_MOVE,
        raw_command="OPENPNP_MOVE X100 Y50 Z10 F1500",
        parameters=[
            GCodeParameter(name='X', value=100.0, raw_value='100'),
            GCodeParameter(name='Y', value=50.0, raw_value='50'),
            GCodeParameter(name='Z', value=10.0, raw_value='10'),
            GCodeParameter(name='F', value=1500.0, raw_value='1500')
        ]
    )
    
    result = translator.translate_command(valid_cmd)
    assert result.success is True
    
    print("✓ Valid parameters accepted")
    
    # Test invalid feedrate (negative)
    invalid_cmd = GCodeCommand(
        command_type=GCodeCommandType.OPENPNP_MOVE,
        raw_command="OPENPNP_MOVE X100 Y50 Z10 F-100",
        parameters=[
            GCodeParameter(name='X', value=100.0, raw_value='100'),
            GCodeParameter(name='Y', value=50.0, raw_value='50'),
            GCodeParameter(name='Z', value=10.0, raw_value='10'),
            GCodeParameter(name='F', value=-100.0, raw_value='-100')
        ]
    )
    
    result = translator.translate_command(invalid_cmd)
    assert result.success is False
    assert "validation" in result.error_message.lower()
    
    print("✓ Invalid feedrate rejected")
    
    print("✓ All parameter validation tests passed")


def test_command_templates():
    """Test command templates."""
    print("\n=== Test: Command Templates ===")
    
    translator = CommandTranslator()
    
    # Test existing template
    templates = translator.get_templates()
    assert 'move' in templates
    assert 'pick' in templates
    assert 'place' in templates
    assert 'pick_and_place' in templates
    
    print("✓ Default templates loaded")
    
    # Test adding custom template
    translator.add_template('custom_template', 'G0 X{x} Y{y} Z{z} F{feedrate}')
    assert 'custom_template' in translator.get_templates()
    
    print("✓ Custom template added")
    
    # Test using template for translation
    cmd = GCodeCommand(
        command_type=GCodeCommandType.OPENPNP_MOVE,
        raw_command="OPENPNP_MOVE X100 Y50 Z10",
        parameters=[
            GCodeParameter(name='X', value=100.0, raw_value='100'),
            GCodeParameter(name='Y', value=50.0, raw_value='50'),
            GCodeParameter(name='Z', value=10.0, raw_value='10')
        ]
    )
    
    result = translator.translate_command(cmd)
    assert result.success is True
    
    print("✓ Template used for translation")
    
    print("✓ All command template tests passed")


def test_context_management():
    """Test translation context management."""
    print("\n=== Test: Context Management ===")
    
    translator = CommandTranslator()
    
    # Test initial context
    context = translator.get_context()
    assert context.feedrate == 1500.0
    assert context.positioning_mode == 'absolute'
    assert context.units == 'mm'
    
    print("✓ Initial context correct")
    
    # Test context update
    context.feedrate = 2000.0
    context.update_position('x', 100.0)
    context.update_position('y', 50.0)
    context.update_position('z', 10.0)
    
    assert context.feedrate == 2000.0
    assert context.get_position('x') == 100.0
    assert context.get_position('y') == 50.0
    assert context.get_position('z') == 10.0
    
    print("✓ Context update successful")
    
    # Test context reset
    translator.reset_context()
    new_context = translator.get_context()
    assert new_context.feedrate == 1500.0
    assert new_context.get_position('x') == 0.0
    
    print("✓ Context reset successful")
    
    print("✓ All context management tests passed")


def test_parse_and_translate():
    """Test parse and translate combined operation."""
    print("\n=== Test: Parse and Translate ===")
    
    translator = CommandTranslator()
    
    # Test parsing and translating a string
    gcode_string = """
    G0 X100 Y50 F1500
    OPENPNP_VACUUM_ON
    OPENPNP_MOVE X200 Y100 Z10
    OPENPNP_VACUUM_OFF
    """
    
    results = translator.parse_and_translate(gcode_string)
    
    assert len(results) == 4
    assert all(result.success for result in results)
    
    print("✓ Parse and translate from string successful")
    
    # Test parsing and translating from list
    gcode_list = [
        "G0 X100 Y50 F1500",
        "OPENPNP_VACUUM_ON",
        "OPENPNP_MOVE X200 Y100 Z10",
        "OPENPNP_VACUUM_OFF"
    ]
    
    results = translator.parse_and_translate(gcode_list)
    
    assert len(results) == 4
    assert all(result.success for result in results)
    
    print("✓ Parse and translate from list successful")
    
    print("✓ All parse and translate tests passed")


def test_complex_sequences():
    """Test complex command sequences."""
    print("\n=== Test: Complex Sequences ===")
    
    translator = CommandTranslator()
    
    # Test pick and place sequence
    gcode_sequence = """
    OPENPNP_VACUUM_ON
    OPENPNP_MOVE X100 Y50 Z0
    OPENPNP_MOVE X100 Y50 Z5
    OPENPNP_MOVE X200 Y100 Z5
    OPENPNP_MOVE X200 Y100 Z0
    OPENPNP_VACUUM_OFF
    OPENPNP_MOVE X200 Y100 Z5
    """
    
    results = translator.parse_and_translate(gcode_sequence)
    
    assert len(results) == 7
    assert all(result.success for result in results)
    
    # Verify translated commands
    all_commands = []
    for result in results:
        all_commands.extend(result.translated_commands)
    
    # Check for expected commands
    assert any("M106" in cmd for cmd in all_commands)  # Vacuum on
    assert any("M107" in cmd for cmd in all_commands)  # Vacuum off
    assert any("G0" in cmd for cmd in all_commands)    # Moves
    
    print("✓ Pick and place sequence successful")
    
    print("✓ All complex sequence tests passed")


def test_custom_validators():
    """Test custom parameter validators."""
    print("\n=== Test: Custom Validators ===")
    
    translator = CommandTranslator()
    
    # Add custom validator
    def custom_feedrate_validator(value):
        return isinstance(value, (int, float)) and 500 <= value <= 5000
    
    translator.add_validator('feedrate', custom_feedrate_validator)
    
    # Test valid feedrate
    cmd = GCodeCommand(
        command_type=GCodeCommandType.OPENPNP_MOVE,
        raw_command="OPENPNP_MOVE X100 Y50 Z10 F1500",
        parameters=[
            GCodeParameter(name='X', value=100.0, raw_value='100'),
            GCodeParameter(name='Y', value=50.0, raw_value='50'),
            GCodeParameter(name='Z', value=10.0, raw_value='10'),
            GCodeParameter(name='F', value=1500.0, raw_value='1500')
        ]
    )
    
    result = translator.translate_command(cmd)
    assert result.success is True
    
    print("✓ Valid feedrate with custom validator accepted")
    
    # Test invalid feedrate (too low)
    cmd = GCodeCommand(
        command_type=GCodeCommandType.OPENPNP_MOVE,
        raw_command="OPENPNP_MOVE X100 Y50 Z10 F100",
        parameters=[
            GCodeParameter(name='X', value=100.0, raw_value='100'),
            GCodeParameter(name='Y', value=50.0, raw_value='50'),
            GCodeParameter(name='Z', value=10.0, raw_value='10'),
            GCodeParameter(name='F', value=100.0, raw_value='100')
        ]
    )
    
    result = translator.translate_command(cmd)
    assert result.success is False
    
    print("✓ Invalid feedrate with custom validator rejected")
    
    print("✓ All custom validator tests passed")


def test_error_handling():
    """Test error handling."""
    print("\n=== Test: Error Handling ===")
    
    translator = CommandTranslator()
    
    # Test unknown command
    unknown_cmd = GCodeCommand(
        command_type=GCodeCommandType.OPENPNP_FEEDER,  # No mapping
        raw_command="OPENPNP_FEEDER",
        parameters=[]
    )
    
    result = translator.translate_command(unknown_cmd)
    assert result.success is False
    assert result.error_message is not None
    
    print("✓ Unknown command error handled")
    
    # Test missing parameter
    cmd = GCodeCommand(
        command_type=GCodeCommandType.OPENPNP_MOVE,
        raw_command="OPENPNP_MOVE",  # No parameters
        parameters=[]
    )
    
    # This should use default values, so it should succeed
    result = translator.translate_command(cmd)
    assert result.success is True
    
    print("✓ Missing parameter handled with defaults")
    
    print("✓ All error handling tests passed")


def test_moonraker_client():
    """Test Moonraker client (without actual connection)."""
    print("\n=== Test: Moonraker Client ===")
    
    # Test client initialization
    client = MoonrakerClient(
        host='localhost',
        port=7125,
        api_key=None
    )
    
    assert client.host == 'localhost'
    assert client.port == 7125
    assert client.base_url == 'http://localhost:7125'
    
    print("✓ Moonraker client initialized")
    
    # Test with API key
    client_with_key = MoonrakerClient(
        host='localhost',
        port=7125,
        api_key='test_key'
    )
    
    assert client_with_key.api_key == 'test_key'
    
    print("✓ Moonraker client with API key initialized")
    
    print("✓ All Moonraker client tests passed")


def test_convenience_functions():
    """Test convenience functions."""
    print("\n=== Test: Convenience Functions ===")
    
    # Test create_translator
    translator = create_translator(
        moonraker_host='localhost',
        moonraker_port=7125
    )
    
    assert translator is not None
    assert translator.moonraker_host == 'localhost'
    assert translator.moonraker_port == 7125
    
    print("✓ create_translator function works")
    
    print("✓ All convenience function tests passed")


def run_all_tests():
    """Run all tests."""
    print("\n" + "="*60)
    print("Running G-code Translator Test Suite")
    print("="*60)
    
    try:
        test_translator_initialization()
        test_command_translation()
        test_parameter_validation()
        test_command_templates()
        test_context_management()
        test_parse_and_translate()
        test_complex_sequences()
        test_custom_validators()
        test_error_handling()
        test_moonraker_client()
        test_convenience_functions()
        
        print("\n" + "="*60)
        print("✓ ALL TESTS PASSED")
        print("="*60)
        return True
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
