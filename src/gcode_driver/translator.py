#!/usr/bin/env python3
# G-code Translator for KlipperPlace
# Provides command translation from OpenPNP to Klipper with Moonraker API integration

import logging
import asyncio
import json
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import aiohttp
import re

# Import from parser module
from .parser import (
    GCodeParser,
    GCodeCommand,
    GCodeCommandType,
    GCodeParameter,
    TranslationResult,
    CommandMapping,
    ConfigurationLoader,
    ParserError,
    TranslationError,
    ConfigurationError
)

# Component logging
logger = logging.getLogger(__name__)


class ExecutionStatus(Enum):
    """Status of G-code execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ExecutionResult:
    """Result of G-code execution."""
    status: ExecutionStatus
    gcode: str
    response: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    execution_time: float = 0.0
    
    def __repr__(self) -> str:
        return f"ExecutionResult(status={self.status.value}, gcode={self.gcode[:50]}...)"


@dataclass
class TranslationContext:
    """Context for command translation."""
    current_position: Dict[str, float] = field(default_factory=lambda: {'x': 0.0, 'y': 0.0, 'z': 0.0})
    feedrate: float = 1500.0
    positioning_mode: str = 'absolute'
    units: str = 'mm'
    tool_number: int = 0
    spindle_speed: int = 0
    custom_params: Dict[str, Any] = field(default_factory=dict)
    
    def update_position(self, axis: str, value: float) -> None:
        """Update position for an axis."""
        axis_lower = axis.lower()
        if axis_lower in self.current_position:
            self.current_position[axis_lower] = value
    
    def get_position(self, axis: Optional[str] = None) -> Union[float, Dict[str, float]]:
        """Get position for an axis or all positions."""
        if axis:
            return self.current_position.get(axis.lower(), 0.0)
        return self.current_position.copy()


class MoonrakerClient:
    """Client for interacting with Moonraker API."""
    
    def __init__(self, host: str = 'localhost', port: int = 7125, 
                 api_key: Optional[str] = None, timeout: float = 30.0):
        """Initialize Moonraker client.
        
        Args:
            host: Moonraker host address
            port: Moonraker port
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
        """
        self.host = host
        self.port = port
        self.api_key = api_key
        self.timeout = timeout
        self.base_url = f"http://{host}:{port}"
        self.session: Optional[aiohttp.ClientSession] = None
        
        logger.info(f"Moonraker client initialized: {self.base_url}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        headers = {
            'Content-Type': 'application/json'
        }
        if self.api_key:
            headers['X-API-Key'] = self.api_key
        return headers
    
    async def _make_request(self, method: str, endpoint: str, 
                           data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make an HTTP request to Moonraker.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            data: Optional request data
            
        Returns:
            Response data
            
        Raises:
            TranslationError: If request fails
        """
        if not self.session:
            raise TranslationError("Session not initialized. Use async context manager.")
        
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        
        try:
            async with self.session.request(method, url, json=data, headers=headers) as response:
                response_data = await response.json()
                
                if response.status != 200:
                    error_msg = response_data.get('error', {}).get('message', 'Unknown error')
                    raise TranslationError(f"Moonraker API error: {error_msg}")
                
                return response_data
        
        except aiohttp.ClientError as e:
            raise TranslationError(f"Moonraker connection error: {e}")
        except json.JSONDecodeError as e:
            raise TranslationError(f"Moonraker response decode error: {e}")
    
    async def run_gcode(self, script: str) -> ExecutionResult:
        """Execute G-code script via Moonraker.
        
        Args:
            script: G-code script to execute
            
        Returns:
            ExecutionResult object
        """
        import time
        start_time = time.time()
        
        try:
            logger.debug(f"Executing G-code: {script[:100]}")
            
            response = await self._make_request(
                'POST',
                '/api/printer/gcode/script',
                {'script': script}
            )
            
            execution_time = time.time() - start_time
            
            result = ExecutionResult(
                status=ExecutionStatus.COMPLETED,
                gcode=script,
                response=response,
                execution_time=execution_time
            )
            
            logger.info(f"G-code executed successfully in {execution_time:.3f}s")
            return result
        
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"G-code execution failed: {e}")
            
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                gcode=script,
                error_message=str(e),
                execution_time=execution_time
            )
    
    async def get_printer_status(self) -> Dict[str, Any]:
        """Get printer status from Moonraker.
        
        Returns:
            Printer status dictionary
        """
        try:
            response = await self._make_request('GET', '/api/printer/status')
            return response.get('result', {})
        except Exception as e:
            logger.error(f"Error getting printer status: {e}")
            return {}
    
    async def get_gcode_store(self) -> Dict[str, Any]:
        """Get G-code store from Moonraker.
        
        Returns:
            G-code store dictionary
        """
        try:
            response = await self._make_request('GET', '/api/printer/gcode/store')
            return response.get('result', {})
        except Exception as e:
            logger.error(f"Error getting G-code store: {e}")
            return {}
    
    async def get_klippy_state(self) -> str:
        """Get Klippy connection state.
        
        Returns:
            Klippy state string
        """
        try:
            response = await self._make_request('GET', '/api/server/connection')
            return response.get('result', {}).get('state', 'unknown')
        except Exception as e:
            logger.error(f"Error getting Klippy state: {e}")
            return 'unknown'


class CommandTranslator:
    """Translates OpenPNP commands to Klipper-compatible G-code."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None,
                 moonraker_host: str = 'localhost',
                 moonraker_port: int = 7125,
                 moonraker_api_key: Optional[str] = None):
        """Initialize command translator.
        
        Args:
            config: Optional configuration dictionary
            moonraker_host: Moonraker host address
            moonraker_port: Moonraker port
            moonraker_api_key: Optional Moonraker API key
        """
        self.config = config or {}
        self.parser = GCodeParser(config)
        self.command_mapping = CommandMapping(config)
        
        # Moonraker client (initialized lazily)
        self.moonraker_host = moonraker_host
        self.moonraker_port = moonraker_port
        self.moonraker_api_key = moonraker_api_key
        self._moonraker_client: Optional[MoonrakerClient] = None
        
        # Translation context
        self.context = TranslationContext()
        
        # Command templates
        self.templates: Dict[str, str] = {}
        self._load_default_templates()
        
        # Parameter validators
        self.validators: Dict[str, Callable[[Any], bool]] = {}
        self._load_default_validators()
        
        # Load custom configuration
        if config:
            self._load_custom_config(config)
        
        logger.info("Command translator initialized")
    
    def _load_default_templates(self) -> None:
        """Load default command templates."""
        self.templates.update({
            # OpenPNP move templates
            'move': 'G0 X{x} Y{y} Z{z} F{feedrate}',
            'move_xy': 'G0 X{x} Y{y} F{feedrate}',
            'move_z': 'G0 Z{z} F{feedrate}',
            
            # OpenPNP pick templates
            'pick': 'G0 Z{pick_height} F{feedrate}\nM106 S{vacuum_power}\nG0 Z{travel_height}',
            'pick_simple': 'G0 Z{z} F{feedrate}\nM106 S255',
            
            # OpenPNP place templates
            'place': 'G0 Z{place_height} F{feedrate}\nM107\nG0 Z{travel_height}',
            'place_simple': 'G0 Z{z} F{feedrate}\nM107',
            
            # OpenPNP actuator templates
            'actuate_on': 'SET_PIN PIN={pin} VALUE=1',
            'actuate_off': 'SET_PIN PIN={pin} VALUE=0',
            'actuate_pwm': 'SET_PIN PIN={pin} VALUE={value} CYCLE_TIME={cycle_time}',
            
            # OpenPNP vacuum templates
            'vacuum_on': 'M106 S{power}',
            'vacuum_off': 'M107',
            'vacuum_set': 'SET_FAN_SPEED FAN={fan} SPEED={speed}',
            
            # OpenPNP feeder templates
            'feeder_advance': 'G0 E{distance} F{feedrate}',
            'feeder_retract': 'G0 E-{distance} F{feedrate}',
            
            # Complex sequences
            'pick_and_place': '''G0 Z{safe_height} F{feedrate}
G0 X{x} Y{y} F{feedrate}
G0 Z{pick_height} F{feedrate}
M106 S{vacuum_power}
G0 Z{safe_height} F{feedrate}
G0 X{place_x} Y{place_y} F{feedrate}
G0 Z{place_height} F{feedrate}
M107
G0 Z{safe_height} F{feedrate}''',
            
            # Home operations
            'home_all': 'G28',
            'home_xy': 'G28 X Y',
            'home_z': 'G28 Z',
            
            # Wait operations
            'wait': 'G4 P{duration}',
            'wait_for_temp': 'M109 S{temperature}',
        })
    
    def _load_default_validators(self) -> None:
        """Load default parameter validators."""
        self.validators.update({
            'x': lambda v: isinstance(v, (int, float)) and -1000 <= v <= 1000,
            'y': lambda v: isinstance(v, (int, float)) and -1000 <= v <= 1000,
            'z': lambda v: isinstance(v, (int, float)) and -500 <= v <= 500,
            'feedrate': lambda v: isinstance(v, (int, float)) and v > 0,
            'vacuum_power': lambda v: isinstance(v, (int, float)) and 0 <= v <= 255,
            'pin': lambda v: isinstance(v, str) and len(v) > 0,
            'duration': lambda v: isinstance(v, (int, float)) and v >= 0,
            'temperature': lambda v: isinstance(v, (int, float)) and v >= 0,
        })
    
    def _load_custom_config(self, config: Dict[str, Any]) -> None:
        """Load custom configuration.
        
        Args:
            config: Configuration dictionary
        """
        # Load custom templates
        if 'templates' in config:
            self.templates.update(config['templates'])
        
        # Load custom validators
        if 'validators' in config:
            self.validators.update(config['validators'])
        
        # Update context defaults
        if 'context_defaults' in config:
            defaults = config['context_defaults']
            for key, value in defaults.items():
                if hasattr(self.context, key):
                    setattr(self.context, key, value)
    
    def get_moonraker_client(self) -> MoonrakerClient:
        """Get or create Moonraker client.
        
        Returns:
            MoonrakerClient instance
        """
        if self._moonraker_client is None:
            self._moonraker_client = MoonrakerClient(
                host=self.moonraker_host,
                port=self.moonraker_port,
                api_key=self.moonraker_api_key
            )
        return self._moonraker_client
    
    def translate_command(self, command: GCodeCommand,
                         context: Optional[Dict[str, Any]] = None) -> TranslationResult:
        """Translate a single G-code command.
        
        Args:
            command: G-code command to translate
            context: Optional translation context
            
        Returns:
            TranslationResult object
        """
        context = context or {}
        result = TranslationResult(success=True, original_command=command.raw_command)
        
        # Merge context with translator context (for defaults only)
        merged_context = {
            'x': self.context.get_position('x'),
            'y': self.context.get_position('y'),
            'z': self.context.get_position('z'),
            'feedrate': self.context.feedrate,
            'positioning_mode': self.context.positioning_mode,
            'units': self.context.units,
            **context,
            **self.context.custom_params
        }
        
        # If it's a standard G-code, pass through
        if self._is_standard_gcode(command.command_type):
            result.translated_commands = [command.raw_command]
            return result
        
        # If it's an OpenPNP command, translate it
        if command.command_type.value.startswith('OPENPNP_'):
            return self._translate_openpnp_command(command, merged_context)
        
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
        value = command_type.value
        if value.startswith('G') and value[1:].isdigit():
            num = int(value[1:])
            return 0 <= num <= 99
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
        cmd_name = command.command_type.value.replace('OPENPNP_', '').lower()
        
        # Try to get mapping from command mapping
        mapping = self.command_mapping.get_mapping(f"OPENPNP_{cmd_name.upper()}")
        
        # If no mapping, try template
        if not mapping and cmd_name in self.templates:
            template = self.templates[cmd_name]
            mapping = [template]
        
        if not mapping:
            result.success = False
            result.error_message = f"No mapping or template found for command: {cmd_name}"
            return result
        
        # Build parameter dictionary
        params = self._build_parameter_dict(command, context)
        
        # Validate parameters
        validation_errors = self._validate_parameters(params)
        if validation_errors:
            result.success = False
            result.error_message = f"Parameter validation failed: {', '.join(validation_errors)}"
            return result
        
        # Substitute parameters in each G-code command
        translated = []
        for gcode_template in mapping:
            try:
                gcode = self._substitute_parameters(gcode_template, params)
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
        logger.info(f"Translated {cmd_name} to {len(translated)} command(s)")
        
        return result
    
    def _build_parameter_dict(self, command: GCodeCommand,
                             context: Dict[str, Any]) -> Dict[str, Any]:
        """Build parameter dictionary from command and context.
        
        Args:
            command: G-code command
            context: Translation context
            
        Returns:
            Parameter dictionary
        """
        params = {}
        
        # Parameter name mappings (G-code parameter -> full parameter name)
        param_mappings = {
            'x': 'x',
            'y': 'y',
            'z': 'z',
            'e': 'e',
            'f': 'feedrate',
            's': 'spindle_speed',
            'p': 'power',
            't': 'tool_number'
        }
        
        # Add command parameters first (highest priority)
        for param in command.parameters:
            param_lower = param.name.lower()
            mapped_name = param_mappings.get(param_lower, param_lower)
            params[mapped_name] = param.value
        
        # Add context parameters only if not already set by command
        for key, value in context.items():
            if key not in params:
                params[key] = value
        
        # Add default values only if not already set
        params.setdefault('feedrate', self.context.feedrate)
        params.setdefault('travel_height', 5.0)
        params.setdefault('pick_height', 0.0)
        params.setdefault('place_height', 0.0)
        params.setdefault('safe_height', 10.0)
        params.setdefault('vacuum_power', 255)
        params.setdefault('cycle_time', 0.01)
        params.setdefault('fan', 0)
        params.setdefault('speed', 1.0)
        
        return params
    
    def _validate_parameters(self, params: Dict[str, Any]) -> List[str]:
        """Validate parameters.
        
        Args:
            params: Parameter dictionary
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        for param_name, param_value in params.items():
            if param_name in self.validators:
                validator = self.validators[param_name]
                try:
                    if not validator(param_value):
                        errors.append(f"Invalid value for parameter '{param_name}': {param_value}")
                except Exception as e:
                    errors.append(f"Validation error for parameter '{param_name}': {e}")
        
        return errors
    
    def _substitute_parameters(self, template: str, params: Dict[str, Any]) -> str:
        """Substitute parameters in template string.
        
        Args:
            template: Template string with {param} placeholders
            params: Parameter dictionary
            
        Returns:
            Substituted string
            
        Raises:
            KeyError: If required parameter is missing
            ValueError: If substitution fails
        """
        try:
            return template.format(**params)
        except KeyError as e:
            raise KeyError(f"Missing parameter: {e}")
        except ValueError as e:
            raise ValueError(f"Substitution error: {e}")
    
    def translate_commands(self, commands: List[GCodeCommand], 
                          context: Optional[Dict[str, Any]] = None) -> List[TranslationResult]:
        """Translate multiple G-code commands.
        
        Args:
            commands: List of G-code commands to translate
            context: Optional translation context
            
        Returns:
            List of TranslationResult objects
        """
        results = []
        current_context = context or {}
        
        for cmd in commands:
            result = self.translate_command(cmd, current_context)
            results.append(result)
            
            # Update context based on translated commands
            if result.success:
                self._update_context_from_commands(result.translated_commands, current_context)
        
        return results
    
    def _update_context_from_commands(self, commands: List[str], 
                                     context: Dict[str, Any]) -> None:
        """Update translation context from G-code commands.
        
        Args:
            commands: List of G-code commands
            context: Context dictionary to update
        """
        for cmd in commands:
            # Parse command to extract parameters
            try:
                parsed = self.parser.parse_line(cmd)
                if parsed:
                    # Update feedrate
                    if parsed.has_parameter('F'):
                        feedrate = parsed.get_parameter('F')
                        if feedrate > 0:
                            self.context.feedrate = feedrate
                            context['feedrate'] = feedrate
                    
                    # Update position for G0/G1 moves
                    if parsed.command_type in [GCodeCommandType.G0, GCodeCommandType.G1]:
                        for axis in ['X', 'Y', 'Z']:
                            if parsed.has_parameter(axis):
                                value = parsed.get_parameter(axis)
                                self.context.update_position(axis, value)
                                context[axis.lower()] = value
            except Exception as e:
                logger.warning(f"Error updating context from command: {e}")
    
    async def execute_command(self, command: GCodeCommand, 
                             context: Optional[Dict[str, Any]] = None) -> List[ExecutionResult]:
        """Translate and execute a G-code command.
        
        Args:
            command: G-code command to execute
            context: Optional translation context
            
        Returns:
            List of ExecutionResult objects
        """
        # Translate command
        result = self.translate_command(command, context)
        
        if not result.success:
            error_msg = result.error_message or "Translation failed"
            logger.error(f"Command translation failed: {error_msg}")
            return [ExecutionResult(
                status=ExecutionStatus.FAILED,
                gcode=command.raw_command,
                error_message=error_msg
            )]
        
        # Execute translated commands
        execution_results = []
        async with self.get_moonraker_client() as client:
            for gcode in result.translated_commands:
                exec_result = await client.run_gcode(gcode)
                execution_results.append(exec_result)
                
                # Stop if execution fails
                if exec_result.status == ExecutionStatus.FAILED:
                    break
        
        return execution_results
    
    async def execute_commands(self, commands: List[GCodeCommand], 
                              context: Optional[Dict[str, Any]] = None) -> List[List[ExecutionResult]]:
        """Translate and execute multiple G-code commands.
        
        Args:
            commands: List of G-code commands to execute
            context: Optional translation context
            
        Returns:
            List of lists of ExecutionResult objects
        """
        results = []
        current_context = context or {}
        
        async with self.get_moonraker_client() as client:
            for cmd in commands:
                # Translate command
                result = self.translate_command(cmd, current_context)
                
                if not result.success:
                    error_msg = result.error_message or "Translation failed"
                    logger.error(f"Command translation failed: {error_msg}")
                    results.append([ExecutionResult(
                        status=ExecutionStatus.FAILED,
                        gcode=cmd.raw_command,
                        error_message=error_msg
                    )])
                    continue
                
                # Execute translated commands
                exec_results = []
                for gcode in result.translated_commands:
                    exec_result = await client.run_gcode(gcode)
                    exec_results.append(exec_result)
                    
                    # Stop if execution fails
                    if exec_result.status == ExecutionStatus.FAILED:
                        break
                
                results.append(exec_results)
                
                # Update context
                if exec_results and exec_results[-1].status == ExecutionStatus.COMPLETED:
                    self._update_context_from_commands(result.translated_commands, current_context)
        
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
        # Parse G-code
        if isinstance(gcode, list):
            commands = []
            for line in gcode:
                try:
                    cmd = self.parser.parse_line(line)
                    if cmd:
                        commands.append(cmd)
                except ParserError as e:
                    logger.error(f"Parse error: {e}")
                    raise
        else:
            commands = self.parser.parse_string(gcode)
        
        # Translate commands
        return self.translate_commands(commands, context)
    
    def add_template(self, name: str, template: str) -> None:
        """Add or update a command template.
        
        Args:
            name: Template name
            template: Template string
        """
        self.templates[name] = template
        logger.info(f"Added template: {name}")
    
    def add_validator(self, param_name: str, 
                     validator: Callable[[Any], bool]) -> None:
        """Add or update a parameter validator.
        
        Args:
            param_name: Parameter name
            validator: Validator function
        """
        self.validators[param_name] = validator
        logger.info(f"Added validator for parameter: {param_name}")
    
    def get_context(self) -> TranslationContext:
        """Get current translation context.
        
        Returns:
            TranslationContext object
        """
        return self.context
    
    def reset_context(self) -> None:
        """Reset translation context to defaults."""
        self.context = TranslationContext()
        logger.info("Translation context reset")
    
    def get_templates(self) -> Dict[str, str]:
        """Get all command templates.
        
        Returns:
            Dictionary of templates
        """
        return self.templates.copy()


# Convenience functions

async def translate_and_execute(gcode: Union[str, List[str]], 
                                context: Optional[Dict[str, Any]] = None,
                                moonraker_host: str = 'localhost',
                                moonraker_port: int = 7125,
                                moonraker_api_key: Optional[str] = None) -> List[List[ExecutionResult]]:
    """Translate and execute G-code in one step.
    
    Args:
        gcode: G-code string or list of G-code strings
        context: Optional translation context
        moonraker_host: Moonraker host address
        moonraker_port: Moonraker port
        moonraker_api_key: Optional Moonraker API key
        
    Returns:
        List of lists of ExecutionResult objects
    """
    translator = CommandTranslator(
        moonraker_host=moonraker_host,
        moonraker_port=moonraker_port,
        moonraker_api_key=moonraker_api_key
    )
    
    results = translator.parse_and_translate(gcode, context)
    
    # Execute translated commands
    execution_results = []
    async with translator.get_moonraker_client() as client:
        for result in results:
            if not result.success:
                execution_results.append([ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    gcode=result.original_command or "",
                    error_message=result.error_message
                )])
                continue
            
            exec_results = []
            for gcode_cmd in result.translated_commands:
                exec_result = await client.run_gcode(gcode_cmd)
                exec_results.append(exec_result)
                
                if exec_result.status == ExecutionStatus.FAILED:
                    break
            
            execution_results.append(exec_results)
    
    return execution_results


def create_translator(config_path: Optional[str] = None,
                     moonraker_host: str = 'localhost',
                     moonraker_port: int = 7125,
                     moonraker_api_key: Optional[str] = None) -> CommandTranslator:
    """Create a CommandTranslator instance with configuration.
    
    Args:
        config_path: Optional path to Klipper config file
        moonraker_host: Moonraker host address
        moonraker_port: Moonraker port
        moonraker_api_key: Optional Moonraker API key
        
    Returns:
        CommandTranslator instance
    """
    config = None
    
    if config_path:
        try:
            loader = ConfigurationLoader(config_path)
            config = loader.config_data
        except Exception as e:
            logger.warning(f"Failed to load config from {config_path}: {e}")
    
    return CommandTranslator(
        config=config,
        moonraker_host=moonraker_host,
        moonraker_port=moonraker_port,
        moonraker_api_key=moonraker_api_key
    )
