#!/usr/bin/env python3
# G-code Parser for KlipperPlace
# Provides G-code parsing and translation capabilities for OpenPNP to Klipper

import logging
import re
import time
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

# Component logging
logger = logging.getLogger(__name__)


class GCodeCommandType(Enum):
    """Enumeration of G-code command types."""
    
    # Motion commands
    G0 = "G0"  # Rapid move
    G1 = "G1"  # Linear move
    G2 = "G2"  # Arc clockwise
    G3 = "G3"  # Arc counter-clockwise
    G4 = "G4"  # Dwell
    
    # Coordinate system
    G17 = "G17"  # XY plane
    G18 = "G18"  # XZ plane
    G19 = "G19"  # YZ plane
    G20 = "G20"  # Inches
    G21 = "G21"  # Millimeters
    G28 = "G28"  # Home
    G29 = "G29"  # Bed leveling
    G90 = "G90"  # Absolute positioning
    G91 = "G91"  # Relative positioning
    G92 = "G92"  # Set position
    
    # Spindle/Fan
    M3 = "M3"  # Spindle on clockwise
    M4 = "M4"  # Spindle on counter-clockwise
    M5 = "M5"  # Spindle off
    M106 = "M106"  # Fan on
    M107 = "M107"  # Fan off
    
    # Misc
    M0 = "M0"  # Unconditional stop
    M1 = "M1"  # Optional stop
    M17 = "M17"  # Enable motors
    M18 = "M18"  # Disable motors
    M84 = "M84"  # Disable steppers
    M104 = "M104"  # Set extruder temp
    M105 = "M105"  # Get temp
    M109 = "M109"  # Wait for temp
    M140 = "M140"  # Set bed temp
    M190 = "M190"  # Wait for bed temp
    
    # Klipper-specific
    SET_FAN_SPEED = "SET_FAN_SPEED"
    SET_PIN = "SET_PIN"
    SET_HEATER_TEMPERATURE = "SET_HEATER_TEMPERATURE"
    QUERY_ENDSTOPS = "QUERY_ENDSTOPS"
    STEPPER_ENABLE = "STEPPER_ENABLE"
    STEPPER_DISABLE = "STEPPER_DISABLE"
    
    # OpenPNP-specific (to be translated)
    OPENPNP_MOVE = "OPENPNP_MOVE"
    OPENPNP_PICK = "OPENPNP_PICK"
    OPENPNP_PLACE = "OPENPNP_PLACE"
    OPENPNP_ACTUATE = "OPENPNP_ACTUATE"
    OPENPNP_ACTUATE_ON = "OPENPNP_ACTUATE_ON"
    OPENPNP_ACTUATE_OFF = "OPENPNP_ACTUATE_OFF"
    OPENPNP_VACUUM = "OPENPNP_VACUUM"
    OPENPNP_VACUUM_ON = "OPENPNP_VACUUM_ON"
    OPENPNP_VACUUM_OFF = "OPENPNP_VACUUM_OFF"
    OPENPNP_FEEDER = "OPENPNP_FEEDER"
    OPENPNP_FEEDER_ADVANCE = "OPENPNP_FEEDER_ADVANCE"


class ParserError(Exception):
    """Base exception for G-code parser errors."""
    pass


class GCodeSyntaxError(ParserError):
    """Exception raised for G-code syntax errors."""
    pass


class TranslationError(ParserError):
    """Exception raised for command translation errors."""
    pass


class ConfigurationError(ParserError):
    """Exception raised for configuration errors."""
    pass


@dataclass
class GCodeParameter:
    """Represents a G-code parameter."""
    
    name: str
    value: Union[float, int, str]
    raw_value: str
    
    def __repr__(self) -> str:
        return f"{self.name}{self.raw_value}"


@dataclass
class GCodeCommand:
    """Represents a parsed G-code command."""
    
    command_type: GCodeCommandType
    raw_command: str
    parameters: List[GCodeParameter] = field(default_factory=list)
    comment: Optional[str] = None
    line_number: Optional[int] = None
    
    def get_parameter(self, name: str, default: Any = None) -> Any:
        """Get a parameter value by name.
        
        Args:
            name: Parameter name (e.g., 'X', 'Y', 'F')
            default: Default value if parameter not found
            
        Returns:
            Parameter value or default
        """
        for param in self.parameters:
            if param.name.upper() == name.upper():
                return param.value
        return default
    
    def has_parameter(self, name: str) -> bool:
        """Check if command has a specific parameter.
        
        Args:
            name: Parameter name to check
            
        Returns:
            True if parameter exists, False otherwise
        """
        return any(param.name.upper() == name.upper() for param in self.parameters)
    
    def __repr__(self) -> str:
        params = " ".join(str(param) for param in self.parameters)
        comment = f" ; {self.comment}" if self.comment else ""
        return f"{self.command_type.value} {params}{comment}".strip()


@dataclass
class TranslationResult:
    """Result of a command translation operation."""
    
    success: bool
    translated_commands: List[str] = field(default_factory=list)
    original_command: Optional[str] = None
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    
    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        self.warnings.append(warning)
        logger.warning(f"Translation warning: {warning}")


class CommandMapping:
    """Manages command mappings for translation."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize command mappings.
        
        Args:
            config: Optional configuration dictionary
        """
        self.mappings: Dict[str, List[str]] = {}
        self._load_default_mappings()
        
        if config:
            self._load_config_mappings(config)
    
    def _load_default_mappings(self) -> None:
        """Load default command mappings."""
        # OpenPNP to Klipper mappings
        self.mappings.update({
            # OpenPNP vacuum control
            'OPENPNP_VACUUM_ON': ['M106 S255'],
            'OPENPNP_VACUUM_OFF': ['M107'],
            
            # OpenPNP actuator control
            'OPENPNP_ACTUATE_ON': ['SET_PIN PIN={pin} VALUE=1'],
            'OPENPNP_ACTUATE_OFF': ['SET_PIN PIN={pin} VALUE=0'],
            
            # OpenPNP feeder control
            'OPENPNP_FEEDER_ADVANCE': ['G0 E{distance} F{feedrate}'],
            
            # OpenPNP move operations
            'OPENPNP_MOVE': ['G0 X{x} Y{y} Z{z} F{feedrate}'],
            'OPENPNP_PICK': ['G0 Z{pick_height} F{feedrate}', 'M106 S255', 'G0 Z{travel_height}'],
            'OPENPNP_PLACE': ['G0 Z{place_height} F{feedrate}', 'M107', 'G0 Z{travel_height}'],
        })
    
    def _load_config_mappings(self, config: Dict[str, Any]) -> None:
        """Load custom mappings from configuration.
        
        Args:
            config: Configuration dictionary
        """
        if 'command_mappings' in config:
            custom_mappings = config['command_mappings']
            for command, gcode_list in custom_mappings.items():
                if isinstance(gcode_list, list):
                    self.mappings[command] = gcode_list
                elif isinstance(gcode_list, str):
                    self.mappings[command] = [gcode_list]
                else:
                    logger.warning(f"Invalid mapping for command {command}: {gcode_list}")
    
    def get_mapping(self, command: str) -> Optional[List[str]]:
        """Get G-code mapping for a command.
        
        Args:
            command: Command name
            
        Returns:
            List of G-code strings or None if not found
        """
        return self.mappings.get(command)
    
    def add_mapping(self, command: str, gcode: Union[str, List[str]]) -> None:
        """Add or update a command mapping.
        
        Args:
            command: Command name
            gcode: G-code string or list of G-code strings
        """
        if isinstance(gcode, str):
            self.mappings[command] = [gcode]
        else:
            self.mappings[command] = gcode
        logger.info(f"Added mapping: {command} -> {gcode}")


class GCodeParser:
    """Main G-code parser class."""
    
    # Regular expression for parsing G-code
    GCODE_PATTERN = re.compile(
        r'^\s*'  # Leading whitespace
        r'(?:(?P<ln>N\d+)\s+)?'  # Line number (optional)
        r'(?P<cmd>[GM]\d+|[A-Z_]+)'  # Command (G0, M106, SET_FAN_SPEED, etc.)
        r'(?P<params>(?:\s*[A-Z][-+]?\d*\.?\d*(?:e[+-]?\d+)?)*)'  # Parameters
        r'(?:\s*;\s*(?P<comment>.*))?'  # Comment (optional)
        r'\s*$',  # Trailing whitespace
        re.IGNORECASE
    )
    
    # Pattern for extracting individual parameters
    PARAM_PATTERN = re.compile(r'([A-Z])([-+]?\d*\.?\d*(?:e[+-]?\d+)?)', re.IGNORECASE)
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the G-code parser.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.command_mapping = CommandMapping(config)
        self.parser_state: Dict[str, Any] = {
            'positioning_mode': 'absolute',  # 'absolute' or 'relative'
            'units': 'mm',  # 'mm' or 'inches'
            'feedrate': 1500,  # Default feedrate in mm/min
            'current_position': {'x': 0.0, 'y': 0.0, 'z': 0.0, 'e': 0.0}
        }
        
        logger.info("G-code parser initialized")
    
    def parse_line(self, line: str, line_number: Optional[int] = None) -> Optional[GCodeCommand]:
        """Parse a single G-code line.
        
        Args:
            line: G-code line to parse
            line_number: Optional line number for error reporting
            
        Returns:
            GCodeCommand object or None if line is empty/comment
            
        Raises:
            GCodeSyntaxError: If line has invalid syntax
        """
        # Strip whitespace
        line = line.strip()
        
        # Skip empty lines
        if not line:
            return None
        
        # Match G-code pattern (pattern handles comments)
        match = self.GCODE_PATTERN.match(line)
        
        # Skip full-line comments
        if not match:
            if line.startswith(';'):
                return None
            raise GCodeSyntaxError(f"Invalid G-code syntax at line {line_number}: {line}")
        if not match:
            raise GCodeSyntaxError(f"Invalid G-code syntax at line {line_number}: {line}")
        
        groups = match.groupdict()
        
        # Extract command
        cmd_str = groups['cmd'].upper()
        
        # Determine command type
        try:
            if cmd_str.startswith('G'):
                cmd_num = int(cmd_str[1:])
                cmd_type = GCodeCommandType(f"G{cmd_num}")
            elif cmd_str.startswith('M'):
                cmd_num = int(cmd_str[1:])
                cmd_type = GCodeCommandType(f"M{cmd_num}")
            else:
                # Try to match as Klipper-specific or OpenPNP command
                cmd_type = GCodeCommandType(cmd_str)
        except ValueError:
            # Unknown command, create a generic one
            cmd_type = GCodeCommandType.G0  # Default to G0
            logger.warning(f"Unknown command type: {cmd_str}, treating as G0")
        
        # Extract parameters
        params_str = groups['params'] or ''
        parameters = self._parse_parameters(params_str)
        
        # Extract comment
        comment = groups['comment']
        
        # Extract line number from G-code if present
        ln_str = groups['ln']
        if ln_str:
            line_number = int(ln_str[1:])  # Remove 'N' prefix
        
        # Create command object
        command = GCodeCommand(
            command_type=cmd_type,
            raw_command=line,
            parameters=parameters,
            comment=comment,
            line_number=line_number
        )
        
        # Update parser state based on command
        self._update_parser_state(command)
        
        return command
    
    def _parse_parameters(self, params_str: str) -> List[GCodeParameter]:
        """Parse parameters from G-code string.
        
        Args:
            params_str: Parameter string (e.g., "X100 Y50 F1500")
            
        Returns:
            List of GCodeParameter objects
        """
        parameters = []
        
        for match in self.PARAM_PATTERN.finditer(params_str):
            name = match.group(1).upper()
            raw_value = match.group(2)
            
            # Try to parse as float, then int
            try:
                value = float(raw_value)
                if value.is_integer():
                    value = int(value)
            except ValueError:
                value = raw_value
            
            parameters.append(GCodeParameter(
                name=name,
                value=value,
                raw_value=raw_value
            ))
        
        return parameters
    
    def _update_parser_state(self, command: GCodeCommand) -> None:
        """Update parser state based on command.
        
        Args:
            command: Parsed G-code command
        """
        # Update positioning mode
        if command.command_type == GCodeCommandType.G90:
            self.parser_state['positioning_mode'] = 'absolute'
        elif command.command_type == GCodeCommandType.G91:
            self.parser_state['positioning_mode'] = 'relative'
        
        # Update units
        if command.command_type == GCodeCommandType.G20:
            self.parser_state['units'] = 'inches'
        elif command.command_type == GCodeCommandType.G21:
            self.parser_state['units'] = 'mm'
        
        # Update feedrate
        if command.has_parameter('F'):
            feedrate = command.get_parameter('F', 0)
            if feedrate > 0:
                self.parser_state['feedrate'] = feedrate
        
        # Update position (for G0/G1 moves)
        if command.command_type in [GCodeCommandType.G0, GCodeCommandType.G1]:
            pos = self.parser_state['current_position']
            mode = self.parser_state['positioning_mode']
            
            for axis in ['X', 'Y', 'Z', 'E']:
                if command.has_parameter(axis):
                    value = command.get_parameter(axis)
                    if mode == 'absolute':
                        pos[axis.lower()] = value
                    else:
                        pos[axis.lower()] += value
    
    def parse_file(self, file_path: str) -> List[GCodeCommand]:
        """Parse a G-code file.
        
        Args:
            file_path: Path to G-code file
            
        Returns:
            List of GCodeCommand objects
            
        Raises:
            ParserError: If file cannot be read or has errors
        """
        commands = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        command = self.parse_line(line, line_num)
                        if command:
                            commands.append(command)
                    except GCodeSyntaxError as e:
                        logger.error(f"Error parsing line {line_num}: {e}")
                        raise ParserError(f"Error in file {file_path}, line {line_num}: {e}")
        except FileNotFoundError:
            raise ParserError(f"G-code file not found: {file_path}")
        except IOError as e:
            raise ParserError(f"Error reading G-code file {file_path}: {e}")
        
        logger.info(f"Parsed {len(commands)} commands from {file_path}")
        return commands
    
    def parse_string(self, gcode_string: str) -> List[GCodeCommand]:
        """Parse a multi-line G-code string.
        
        Args:
            gcode_string: Multi-line G-code string
            
        Returns:
            List of GCodeCommand objects
        """
        commands = []
        lines = gcode_string.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            try:
                command = self.parse_line(line, line_num)
                if command:
                    commands.append(command)
            except GCodeSyntaxError as e:
                logger.error(f"Error parsing line {line_num}: {e}")
                raise ParserError(f"Error at line {line_num}: {e}")
        
        return commands
    
    def translate_command(self, command: GCodeCommand, 
                         context: Optional[Dict[str, Any]] = None) -> TranslationResult:
        """Translate a G-code command to Klipper-compatible G-code.
        
        Args:
            command: G-code command to translate
            context: Optional translation context (e.g., current position, state)
            
        Returns:
            TranslationResult object
        """
        context = context or {}
        result = TranslationResult(success=True, original_command=command.raw_command)
        
        # If it's a standard G-code, pass through
        if self._is_standard_gcode(command.command_type):
            result.translated_commands = [command.raw_command]
            return result
        
        # If it's an OpenPNP command, translate it
        if command.command_type.value.startswith('OPENPNP_'):
            return self._translate_openpnp_command(command, context)
        
        # If it's a Klipper-specific command, pass through
        result.translated_commands = [command.raw_command]
        return result
    
    def _is_standard_gcode(self, command_type: GCodeCommandType) -> bool:
        """Check if command is standard G-code.
        
        Args:
            command_type: Command type to check
            
        Returns:
            True if standard G-code, False otherwise
        """
        # Standard G-codes are G0-G4, M0-M999
        value = command_type.value
        if value.startswith('G') and value[1:].isdigit():
            num = int(value[1:])
            return 0 <= num <= 4
        if value.startswith('M') and value[1:].isdigit():
            num = int(value[1:])
            return 0 <= num <= 999
        return False
    
    def _translate_openpnp_command(self, command: GCodeCommand, 
                                   context: Dict[str, Any]) -> TranslationResult:
        """Translate OpenPNP command to Klipper G-code.
        
        Args:
            command: OpenPNP command to translate
            context: Translation context
            
        Returns:
            TranslationResult object
        """
        result = TranslationResult(success=True, original_command=command.raw_command)
        
        # Get command name without OPENPNP_ prefix
        cmd_name = command.command_type.value.replace('OPENPNP_', '')
        
        # Get mapping
        mapping = self.command_mapping.get_mapping(f"OPENPNP_{cmd_name}")
        
        if not mapping:
            result.success = False
            result.error_message = f"No mapping found for command: {cmd_name}"
            return result
        
        # Build parameter dictionary for substitution
        params = {param.name.lower(): param.value for param in command.parameters}
        
        # Add context parameters
        params.update(context)
        
        # Add default values from parser state
        params.setdefault('feedrate', self.parser_state['feedrate'])
        params.setdefault('travel_height', 5.0)
        params.setdefault('pick_height', 0.0)
        params.setdefault('place_height', 0.0)
        
        # Substitute parameters in each G-code command
        translated = []
        for gcode_template in mapping:
            try:
                # Substitute parameters
                gcode = gcode_template.format(**params)
                translated.append(gcode)
            except KeyError as e:
                result.success = False
                result.error_message = f"Missing required parameter: {e}"
                return result
            except ValueError as e:
                result.success = False
                result.error_message = f"Parameter substitution error: {e}"
                return result
        
        result.translated_commands = translated
        logger.info(f"Translated {cmd_name} to: {translated}")
        
        return result
    
    def get_parser_state(self) -> Dict[str, Any]:
        """Get current parser state.
        
        Returns:
            Dictionary containing parser state
        """
        return self.parser_state.copy()
    
    def reset_parser_state(self) -> None:
        """Reset parser state to defaults."""
        self.parser_state = {
            'positioning_mode': 'absolute',
            'units': 'mm',
            'feedrate': 1500,
            'current_position': {'x': 0.0, 'y': 0.0, 'z': 0.0, 'e': 0.0}
        }
        logger.info("Parser state reset")


class ConfigurationLoader:
    """Loads and validates configuration from Klipper config files."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration loader.
        
        Args:
            config_path: Optional path to Klipper config file
        """
        self.config_path = config_path
        self.config_data: Dict[str, Any] = {}
        
        if config_path:
            self.load_config(config_path)
    
    def load_config(self, config_path: str) -> None:
        """Load configuration from Klipper config file.
        
        Args:
            config_path: Path to Klipper config file
            
        Raises:
            ConfigurationError: If config file cannot be loaded
        """
        config_file = Path(config_path)
        
        if not config_file.exists():
            raise ConfigurationError(f"Config file not found: {config_path}")
        
        try:
            self.config_data = self._parse_klipper_config(config_file)
            logger.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            raise ConfigurationError(f"Error loading config file {config_path}: {e}")
    
    def _parse_klipper_config(self, config_file: Path) -> Dict[str, Any]:
        """Parse Klipper configuration file.
        
        Args:
            config_file: Path to config file
            
        Returns:
            Dictionary containing parsed configuration
        """
        config = {}
        current_section = None
        
        with open(config_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Section header
                if line.startswith('[') and line.endswith(']'):
                    section_name = line[1:-1]
                    current_section = section_name
                    config[current_section] = {}
                elif current_section:
                    # Key-value pair
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Remove inline comments
                        if '#' in value:
                            value = value.split('#')[0].strip()
                        
                        # Parse value
                        config[current_section][key] = self._parse_config_value(value)
        
        return config
    
    def _parse_config_value(self, value: str) -> Union[str, int, float, bool, List[str]]:
        """Parse a configuration value.
        
        Args:
            value: String value to parse
            
        Returns:
            Parsed value (int, float, bool, string, or list)
        """
        # Try boolean
        if value.lower() in ('true', 'yes', 'on', '1'):
            return True
        if value.lower() in ('false', 'no', 'off', '0'):
            return False
        
        # Try integer
        try:
            return int(value)
        except ValueError:
            pass
        
        # Try float
        try:
            return float(value)
        except ValueError:
            pass
        
        # Try list (comma-separated)
        if ',' in value:
            return [item.strip() for item in value.split(',')]
        
        # Return as string
        return value
    
    def get_section(self, section_name: str) -> Optional[Dict[str, Any]]:
        """Get a configuration section.
        
        Args:
            section_name: Name of section to retrieve
            
        Returns:
            Dictionary containing section data or None if not found
        """
        return self.config_data.get(section_name)
    
    def get_value(self, section: str, key: str, default: Any = None) -> Any:
        """Get a configuration value.
        
        Args:
            section: Section name
            key: Key name
            default: Default value if not found
            
        Returns:
            Configuration value or default
        """
        section_data = self.get_section(section)
        if section_data:
            return section_data.get(key, default)
        return default
    
    def validate_config(self) -> Tuple[bool, List[str]]:
        """Validate configuration.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check for required sections
        required_sections = ['printer', 'stepper_x', 'stepper_y']
        for section in required_sections:
            if section not in self.config_data:
                errors.append(f"Missing required section: [{section}]")
        
        # Validate stepper configurations
        for axis in ['x', 'y', 'z']:
            section = f'stepper_{axis}'
            if section in self.config_data:
                stepper_config = self.config_data[section]
                required_keys = ['step_pin', 'dir_pin', 'enable_pin']
                for key in required_keys:
                    if key not in stepper_config:
                        errors.append(f"Missing {key} in [{section}]")
        
        return (len(errors) == 0, errors)
    
    def get_command_mappings(self) -> Dict[str, List[str]]:
        """Get custom command mappings from config.
        
        Returns:
            Dictionary of command mappings
        """
        mappings = {}
        
        # Check for gcode_driver section
        driver_section = self.get_section('gcode_driver')
        if driver_section:
            custom_mappings = driver_section.get('command_mappings', {})
            if isinstance(custom_mappings, dict):
                mappings.update(custom_mappings)
        
        return mappings


class GCodeDriver:
    """Main G-code driver class that integrates parser and translation."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the G-code driver.
        
        Args:
            config_path: Optional path to Klipper config file
        """
        # Load configuration
        self.config_loader = ConfigurationLoader(config_path)
        config_data = self.config_loader.config_data
        
        # Initialize parser
        self.parser = GCodeParser(config_data)
        
        # Validate configuration
        is_valid, errors = self.config_loader.validate_config()
        if not is_valid:
            logger.warning(f"Configuration validation errors: {errors}")
        
        logger.info("G-code driver initialized")
    
    def parse(self, gcode: Union[str, List[str]]) -> List[GCodeCommand]:
        """Parse G-code input.
        
        Args:
            gcode: G-code string or list of G-code strings
            
        Returns:
            List of parsed G-codeCommand objects
        """
        if isinstance(gcode, list):
            # Parse each line in the list
            commands = []
            for line in gcode:
                try:
                    cmd = self.parser.parse_line(line)
                    if cmd:
                        commands.append(cmd)
                except GCodeSyntaxError as e:
                    logger.error(f"Parse error: {e}")
                    raise
            return commands
        else:
            # Parse as multi-line string
            return self.parser.parse_string(gcode)
    
    def translate(self, commands: Union[GCodeCommand, List[GCodeCommand]], 
                  context: Optional[Dict[str, Any]] = None) -> List[TranslationResult]:
        """Translate G-code commands to Klipper-compatible G-code.
        
        Args:
            commands: Single command or list of commands
            context: Optional translation context
            
        Returns:
            List of TranslationResult objects
        """
        if isinstance(commands, GCodeCommand):
            commands = [commands]
        
        results = []
        for cmd in commands:
            result = self.parser.translate_command(cmd, context)
            results.append(result)
        
        return results
    
    def parse_and_translate(self, gcode: Union[str, List[str]], 
                           context: Optional[Dict[str, Any]] = None) -> List[TranslationResult]:
        """Parse and translate G-code in one step.
        
        Args:
            gcode: G-code string or list of G-code strings
            context: Optional translation context
            
        Returns:
            List of TranslationResult objects
        """
        commands = self.parse(gcode)
        return self.translate(commands, context)
    
    def get_state(self) -> Dict[str, Any]:
        """Get current driver state.
        
        Returns:
            Dictionary containing driver state
        """
        return {
            'parser_state': self.parser.get_parser_state(),
            'config_loaded': bool(self.config_loader.config_data)
        }
    
    def reset_state(self) -> None:
        """Reset driver state."""
        self.parser.reset_parser_state()
        logger.info("Driver state reset")


# Convenience functions for common operations

def parse_gcode(gcode: Union[str, List[str]], 
               config_path: Optional[str] = None) -> List[GCodeCommand]:
    """Parse G-code input.
    
    Args:
        gcode: G-code string or list of G-code strings
        config_path: Optional path to Klipper config file
        
    Returns:
        List of parsed GCodeCommand objects
    """
    driver = GCodeDriver(config_path)
    return driver.parse(gcode)


def translate_to_klipper(gcode: Union[str, List[str]], 
                       context: Optional[Dict[str, Any]] = None,
                       config_path: Optional[str] = None) -> List[str]:
    """Translate G-code to Klipper-compatible G-code.
    
    Args:
        gcode: G-code string or list of G-code strings
        context: Optional translation context
        config_path: Optional path to Klipper config file
        
    Returns:
        List of translated G-code strings
    """
    driver = GCodeDriver(config_path)
    results = driver.parse_and_translate(gcode, context)
    
    # Flatten all translated commands
    translated = []
    for result in results:
        if result.success:
            translated.extend(result.translated_commands)
    
    return translated
