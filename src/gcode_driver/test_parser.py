#!/usr/bin/env python3
# Test script for G-code parser

import sys
import os

# Add parent directory to path to import parser
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gcode_driver.parser import (
    GCodeParser, GCodeCommand, GCodeCommandType, GCodeDriver,
    parse_gcode, translate_to_klipper, ParserError
)


def test_basic_parsing():
    """Test basic G-code parsing."""
    print("Testing basic G-code parsing...")
    
    parser = GCodeParser()
    
    # Test simple G-code
    cmd = parser.parse_line("G0 X100 Y50 F1500")
    assert cmd is not None
    assert cmd.command_type == GCodeCommandType.G0
    assert cmd.get_parameter('X') == 100
    assert cmd.get_parameter('Y') == 50
    assert cmd.get_parameter('F') == 1500
    print("[PASS] Basic G-code parsing works")
    
    # Test with comment
    cmd = parser.parse_line("G1 X10 Y20 ; Move to position")
    assert cmd is not None
    assert cmd.comment == "Move to position"
    print("[PASS] Comment parsing works")
    
    # Test with line number
    cmd = parser.parse_line("N100 G0 X0 Y0")
    assert cmd is not None
    assert cmd.line_number == 100
    print("[PASS] Line number parsing works")
    
    # Test empty line
    cmd = parser.parse_line("")
    assert cmd is None
    print("[PASS] Empty line handling works")
    
    # Test comment-only line
    cmd = parser.parse_line("; This is a comment")
    assert cmd is None
    print("[PASS] Comment-only line handling works")


def test_multi_line_parsing():
    """Test multi-line G-code parsing."""
    print("\nTesting multi-line G-code parsing...")
    
    parser = GCodeParser()
    
    gcode = """G28 ; Home all axes
G0 X10 Y10 Z5 F3000
G1 X20 Y20 F1500
M106 S255 ; Turn fan on"""
    
    commands = parser.parse_string(gcode)
    assert len(commands) == 4
    assert commands[0].command_type == GCodeCommandType.G28
    assert commands[1].command_type == GCodeCommandType.G0
    assert commands[2].command_type == GCodeCommandType.G1
    assert commands[3].command_type == GCodeCommandType.M106
    print("[PASS] Multi-line parsing works")


def test_parser_state():
    """Test parser state tracking."""
    print("\nTesting parser state tracking...")
    
    parser = GCodeParser()
    
    # Initial state
    state = parser.get_parser_state()
    assert state['positioning_mode'] == 'absolute'
    assert state['units'] == 'mm'
    print("[PASS] Initial state is correct")
    
    # Change to relative positioning
    parser.parse_line("G91")
    state = parser.get_parser_state()
    assert state['positioning_mode'] == 'relative'
    print("[PASS] Positioning mode change works")
    
    # Change to absolute positioning
    parser.parse_line("G90")
    state = parser.get_parser_state()
    assert state['positioning_mode'] == 'absolute'
    print("[PASS] Positioning mode change back works")
    
    # Change feedrate
    parser.parse_line("G0 F2000")
    state = parser.get_parser_state()
    assert state['feedrate'] == 2000
    print("[PASS] Feedrate tracking works")


def test_command_translation():
    """Test OpenPNP command translation."""
    print("\nTesting command translation...")
    
    driver = GCodeDriver()
    
    # Test vacuum on command
    gcode = "OPENPNP_VACUUM_ON"
    results = driver.parse_and_translate(gcode)
    assert len(results) == 1
    assert results[0].success
    assert "M106 S255" in results[0].translated_commands
    print("[PASS] Vacuum on translation works")
    
    # Test vacuum off command
    gcode = "OPENPNP_VACUUM_OFF"
    results = driver.parse_and_translate(gcode)
    assert len(results) == 1
    assert results[0].success
    assert "M107" in results[0].translated_commands
    print("[PASS] Vacuum off translation works")
    
    # Test move command with parameters
    gcode = "OPENPNP_MOVE X100 Y50 Z10"
    results = driver.parse_and_translate(gcode)
    assert len(results) == 1
    assert results[0].success
    translated = results[0].translated_commands[0]
    assert "X100" in translated
    assert "Y50" in translated
    assert "Z10" in translated
    print("[PASS] Move command translation works")
    
    # Test pick command
    gcode = "OPENPNP_PICK"
    results = driver.parse_and_translate(gcode)
    assert len(results) == 1
    assert results[0].success
    assert len(results[0].translated_commands) == 3
    print("[PASS] Pick command translation works")


def test_standard_gcode_passthrough():
    """Test that standard G-code passes through unchanged."""
    print("\nTesting standard G-code passthrough...")
    
    driver = GCodeDriver()
    
    # Test standard G-code
    gcode = "G0 X100 Y50 F1500"
    results = driver.parse_and_translate(gcode)
    assert len(results) == 1
    assert results[0].success
    assert results[0].translated_commands[0] == gcode
    print("[PASS] Standard G-code passthrough works")
    
    # Test M-code
    gcode = "M106 S128"
    results = driver.parse_and_translate(gcode)
    assert len(results) == 1
    assert results[0].success
    assert results[0].translated_commands[0] == gcode
    print("[PASS] M-code passthrough works")


def test_convenience_functions():
    """Test convenience functions."""
    print("\nTesting convenience functions...")
    
    # Test parse_gcode
    commands = parse_gcode("G0 X100 Y50")
    assert len(commands) == 1
    assert commands[0].command_type == GCodeCommandType.G0
    print("[PASS] parse_gcode convenience function works")
    
    # Test translate_to_klipper
    translated = translate_to_klipper("OPENPNP_VACUUM_ON")
    assert "M106 S255" in translated
    print("[PASS] translate_to_klipper convenience function works")


def test_error_handling():
    """Test error handling."""
    print("\nTesting error handling...")
    
    parser = GCodeParser()
    
    # Test invalid G-code
    try:
        parser.parse_line("INVALID_COMMAND")
        assert False, "Should have raised an error"
    except Exception:
        print("[PASS] Invalid command handling works")
    
    # Test missing parameter in translation
    driver = GCodeDriver()
    gcode = "OPENPNP_ACTUATE_ON"  # Missing required 'pin' parameter
    results = driver.parse_and_translate(gcode)
    assert len(results) == 1
    assert not results[0].success
    assert "Missing required parameter" in results[0].error_message
    print("[PASS] Missing parameter error handling works")


def test_parameter_types():
    """Test different parameter types."""
    print("\nTesting parameter types...")
    
    parser = GCodeParser()
    
    # Test integer parameters
    cmd = parser.parse_line("G0 X100")
    assert cmd.get_parameter('X') == 100
    assert isinstance(cmd.get_parameter('X'), int)
    print("[PASS] Integer parameter parsing works")
    
    # Test float parameters
    cmd = parser.parse_line("G0 X100.5")
    assert cmd.get_parameter('X') == 100.5
    assert isinstance(cmd.get_parameter('X'), float)
    print("[PASS] Float parameter parsing works")
    
    # Test negative values
    cmd = parser.parse_line("G0 X-50")
    assert cmd.get_parameter('X') == -50
    print("[PASS] Negative value parsing works")
    
    # Test scientific notation
    cmd = parser.parse_line("G0 X1.5e2")
    assert abs(cmd.get_parameter('X') - 150.0) < 0.01
    print("[PASS] Scientific notation parsing works")


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("Running G-code Parser Tests")
    print("=" * 60)
    
    try:
        test_basic_parsing()
        test_multi_line_parsing()
        test_parser_state()
        test_command_translation()
        test_standard_gcode_passthrough()
        test_convenience_functions()
        test_error_handling()
        test_parameter_types()
        
        print("\n" + "=" * 60)
        print("All tests passed! [SUCCESS]")
        print("=" * 60)
        return True
    except AssertionError as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n[FAIL] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
