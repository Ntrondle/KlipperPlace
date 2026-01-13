#!/usr/bin/env python3
# Translation Layer for KlipperPlace Middleware
# Provides OpenPNP to Moonraker/G-code translation with unified response format

import logging
import asyncio
import json
import time
import uuid
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import aiohttp

# Import from G-code driver
from gcode_driver.parser import (
    GCodeParser,
    GCodeCommand,
    GCodeCommandType,
    TranslationResult,
    ParserError
)
from gcode_driver.translator import (
    CommandTranslator,
    MoonrakerClient,
    ExecutionResult,
    ExecutionStatus,
    TranslationContext
)
from gcode_driver.handlers import (
    ExecutionHandler,
    CommandQueue,
    ExecutionHistory,
    ExecutionState,
    HandlerError
)

# Component logging
logger = logging.getLogger(__name__)


class OpenPNPCommandType(Enum):
    """Enumeration of OpenPNP command types."""
    
    # Motion commands
    MOVE = "move"
    MOVE_ABSOLUTE = "move_absolute"
    MOVE_RELATIVE = "move_relative"
    HOME = "home"
    
    # Pick and place commands
    PICK = "pick"
    PLACE = "place"
    PICK_AND_PLACE = "pick_and_place"
    
    # Actuator commands
    ACTUATE = "actuate"
    ACTUATE_ON = "actuate_on"
    ACTUATE_OFF = "actuate_off"
    
    # Vacuum commands
    VACUUM_ON = "vacuum_on"
    VACUUM_OFF = "vacuum_off"
    VACUUM_SET = "vacuum_set"
    
    # Fan commands
    FAN_ON = "fan_on"
    FAN_OFF = "fan_off"
    FAN_SET = "fan_set"
    
    # PWM commands
    PWM_SET = "pwm_set"
    PWM_RAMP = "pwm_ramp"
    
    # GPIO commands
    GPIO_READ = "gpio_read"
    GPIO_WRITE = "gpio_write"
    
    # Sensor commands
    SENSOR_READ = "sensor_read"
    SENSOR_READ_ALL = "sensor_read_all"
    
    # Feeder commands
    FEEDER_ADVANCE = "feeder_advance"
    FEEDER_RETRACT = "feeder_retract"
    
    # Status commands
    GET_STATUS = "get_status"
    GET_POSITION = "get_position"
    GET_PRINTER_STATE = "get_printer_state"
    
    # Queue commands
    QUEUE_COMMAND = "queue_command"
    QUEUE_BATCH = "queue_batch"
    QUEUE_STATUS = "queue_status"
    QUEUE_CLEAR = "queue_clear"
    
    # System commands
    CANCEL = "cancel"
    PAUSE = "pause"
    RESUME = "resume"
    RESET = "reset"


class ResponseStatus(Enum):
    """Status of OpenPNP command response."""
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class OpenPNPResponse:
    """Unified response format for OpenPNP commands."""
    
    status: ResponseStatus
    command: str
    command_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary."""
        return {
            'status': self.status.value,
            'command': self.command,
            'command_id': self.command_id,
            'data': self.data,
            'error_message': self.error_message,
            'error_code': self.error_code,
            'warnings': self.warnings,
            'execution_time': self.execution_time,
            'timestamp': self.timestamp
        }
    
    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        self.warnings.append(warning)
        logger.warning(f"Response warning: {warning}")


@dataclass
class OpenPNPCommand:
    """Represents an OpenPNP command."""
    
    command_type: OpenPNPCommandType
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())


class TranslationStrategy(Enum):
    """Strategy for translating OpenPNP commands."""
    DIRECT_API = "direct_api"  # Use Moonraker extension API directly
    GCODE = "gcode"  # Translate to G-code and execute
    HYBRID = "hybrid"  # Use combination of API and G-code


class OpenPNPTranslator:
    """Main translator for OpenPNP to Moonraker/G-code."""
    
    def __init__(self,
                 moonraker_host: str = 'localhost',
                 moonraker_port: int = 7125,
                 moonraker_api_key: Optional[str] = None,
                 max_queue_size: int = 1000,
                 max_history_entries: int = 1000,
                 default_timeout: float = 30.0):
        """Initialize OpenPNP translator.
        
        Args:
            moonraker_host: Moonraker host address
            moonraker_port: Moonraker port
            moonraker_api_key: Optional Moonraker API key
            max_queue_size: Maximum queue size
            max_history_entries: Maximum history entries
            default_timeout: Default execution timeout
        """
        self.moonraker_host = moonraker_host
        self.moonraker_port = moonraker_port
        self.moonraker_api_key = moonraker_api_key
        self.default_timeout = default_timeout
        
        # Initialize components
        self.gcode_translator = CommandTranslator(
            moonraker_host=moonraker_host,
            moonraker_port=moonraker_port,
            moonraker_api_key=moonraker_api_key
        )
        
        # Moonraker client for direct API calls
        self._moonraker_client: Optional[MoonrakerClient] = None
        
        # Execution handler
        self._execution_handler: Optional[ExecutionHandler] = None
        self._handler_lock = asyncio.Lock()
        
        # Configuration
        self.max_queue_size = max_queue_size
        self.max_history_entries = max_history_entries
        
        # Command strategy mapping
        self._strategy_map: Dict[OpenPNPCommandType, TranslationStrategy] = {}
        self._initialize_strategy_map()
        
        # State management
        self._state = {
            'current_position': {'x': 0.0, 'y': 0.0, 'z': 0.0},
            'vacuum_enabled': False,
            'fan_speed': 0.0,
            'actuators': {},
            'klippy_connected': False
        }
        
        logger.info("OpenPNP translator initialized")
    
    def _initialize_strategy_map(self) -> None:
        """Initialize command translation strategies."""
        self._strategy_map.update({
            # Direct API commands
            OpenPNPCommandType.GPIO_READ: TranslationStrategy.DIRECT_API,
            OpenPNPCommandType.SENSOR_READ: TranslationStrategy.DIRECT_API,
            OpenPNPCommandType.SENSOR_READ_ALL: TranslationStrategy.DIRECT_API,
            OpenPNPCommandType.FAN_SET: TranslationStrategy.DIRECT_API,
            OpenPNPCommandType.PWM_SET: TranslationStrategy.DIRECT_API,
            OpenPNPCommandType.PWM_RAMP: TranslationStrategy.DIRECT_API,
            
            # G-code commands
            OpenPNPCommandType.MOVE: TranslationStrategy.GCODE,
            OpenPNPCommandType.MOVE_ABSOLUTE: TranslationStrategy.GCODE,
            OpenPNPCommandType.MOVE_RELATIVE: TranslationStrategy.GCODE,
            OpenPNPCommandType.HOME: TranslationStrategy.GCODE,
            OpenPNPCommandType.PICK: TranslationStrategy.GCODE,
            OpenPNPCommandType.PLACE: TranslationStrategy.GCODE,
            OpenPNPCommandType.PICK_AND_PLACE: TranslationStrategy.GCODE,
            OpenPNPCommandType.ACTUATE: TranslationStrategy.GCODE,
            OpenPNPCommandType.ACTUATE_ON: TranslationStrategy.GCODE,
            OpenPNPCommandType.ACTUATE_OFF: TranslationStrategy.GCODE,
            OpenPNPCommandType.VACUUM_ON: TranslationStrategy.GCODE,
            OpenPNPCommandType.VACUUM_OFF: TranslationStrategy.GCODE,
            OpenPNPCommandType.VACUUM_SET: TranslationStrategy.GCODE,
            OpenPNPCommandType.FAN_ON: TranslationStrategy.GCODE,
            OpenPNPCommandType.FAN_OFF: TranslationStrategy.GCODE,
            OpenPNPCommandType.GPIO_WRITE: TranslationStrategy.GCODE,
            OpenPNPCommandType.FEEDER_ADVANCE: TranslationStrategy.GCODE,
            OpenPNPCommandType.FEEDER_RETRACT: TranslationStrategy.GCODE,
            
            # Hybrid commands
            OpenPNPCommandType.GET_STATUS: TranslationStrategy.HYBRID,
            OpenPNPCommandType.GET_POSITION: TranslationStrategy.HYBRID,
            OpenPNPCommandType.GET_PRINTER_STATE: TranslationStrategy.HYBRID,
            
            # System commands (special handling)
            OpenPNPCommandType.QUEUE_COMMAND: TranslationStrategy.GCODE,
            OpenPNPCommandType.QUEUE_BATCH: TranslationStrategy.GCODE,
            OpenPNPCommandType.QUEUE_STATUS: TranslationStrategy.DIRECT_API,
            OpenPNPCommandType.QUEUE_CLEAR: TranslationStrategy.DIRECT_API,
            OpenPNPCommandType.CANCEL: TranslationStrategy.DIRECT_API,
            OpenPNPCommandType.PAUSE: TranslationStrategy.DIRECT_API,
            OpenPNPCommandType.RESUME: TranslationStrategy.DIRECT_API,
            OpenPNPCommandType.RESET: TranslationStrategy.DIRECT_API,
        })
    
    def _get_strategy(self, command_type: OpenPNPCommandType) -> TranslationStrategy:
        """Get translation strategy for a command type.
        
        Args:
            command_type: OpenPNP command type
            
        Returns:
            Translation strategy
        """
        return self._strategy_map.get(command_type, TranslationStrategy.GCODE)
    
    def _get_execution_handler(self) -> ExecutionHandler:
        """Get or create execution handler.
        
        Returns:
            ExecutionHandler instance
        """
        if self._execution_handler is None:
            moonraker_client = self.gcode_translator.get_moonraker_client()
            self._execution_handler = ExecutionHandler(
                moonraker_client=moonraker_client,
                translator=self.gcode_translator,
                max_queue_size=self.max_queue_size,
                max_history_entries=self.max_history_entries,
                default_timeout=self.default_timeout
            )
        return self._execution_handler
    
    async def translate_and_execute(self,
                                  command: Union[OpenPNPCommand, Dict[str, Any]]) -> OpenPNPResponse:
        """Translate and execute an OpenPNP command.
        
        Args:
            command: OpenPNP command or command dictionary
            
        Returns:
            OpenPNPResponse object
        """
        start_time = time.time()
        
        # Parse command
        if isinstance(command, dict):
            command = self._parse_command_dict(command)
        
        logger.info(f"Executing OpenPNP command: {command.command_type.value} (id: {command.id})")
        
        try:
            # Get translation strategy
            strategy = self._get_strategy(command.command_type)
            
            # Execute based on strategy
            if strategy == TranslationStrategy.DIRECT_API:
                response = await self._execute_direct_api(command)
            elif strategy == TranslationStrategy.GCODE:
                response = await self._execute_gcode(command)
            elif strategy == TranslationStrategy.HYBRID:
                response = await self._execute_hybrid(command)
            else:
                response = OpenPNPResponse(
                    status=ResponseStatus.ERROR,
                    command=command.command_type.value,
                    error_message=f"Unknown translation strategy: {strategy}",
                    error_code="UNKNOWN_STRATEGY"
                )
            
            # Update execution time
            response.execution_time = time.time() - start_time
            
            # Update state on success
            if response.status == ResponseStatus.SUCCESS:
                self._update_state(command, response)
            
            return response
        
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Error executing command {command.command_type.value}: {e}")
            
            return OpenPNPResponse(
                status=ResponseStatus.ERROR,
                command=command.command_type.value,
                command_id=command.id,
                error_message=str(e),
                error_code="EXECUTION_ERROR",
                execution_time=execution_time
            )
    
    def _parse_command_dict(self, command_dict: Dict[str, Any]) -> OpenPNPCommand:
        """Parse command dictionary to OpenPNPCommand.
        
        Args:
            command_dict: Command dictionary
            
        Returns:
            OpenPNPCommand object
        """
        command_type_str = command_dict.get('command', command_dict.get('type'))
        
        try:
            command_type = OpenPNPCommandType(command_type_str.lower())
        except ValueError:
            raise ValueError(f"Unknown command type: {command_type_str}")
        
        return OpenPNPCommand(
            command_type=command_type,
            parameters=command_dict.get('parameters', {}),
            metadata=command_dict.get('metadata', {}),
            priority=command_dict.get('priority', 0),
            id=command_dict.get('id', str(uuid.uuid4()))
        )
    
    async def _execute_direct_api(self, command: OpenPNPCommand) -> OpenPNPResponse:
        """Execute command via direct Moonraker API calls.
        
        Args:
            command: OpenPNP command to execute
            
        Returns:
            OpenPNPResponse object
        """
        async with self.gcode_translator.get_moonraker_client() as client:
            try:
                # Route to appropriate API endpoint
                if command.command_type == OpenPNPCommandType.GPIO_READ:
                    return await self._api_gpio_read(command, client)
                elif command.command_type == OpenPNPCommandType.SENSOR_READ:
                    return await self._api_sensor_read(command, client)
                elif command.command_type == OpenPNPCommandType.SENSOR_READ_ALL:
                    return await self._api_sensor_read_all(command, client)
                elif command.command_type == OpenPNPCommandType.FAN_SET:
                    return await self._api_fan_set(command, client)
                elif command.command_type == OpenPNPCommandType.PWM_SET:
                    return await self._api_pwm_set(command, client)
                elif command.command_type == OpenPNPCommandType.PWM_RAMP:
                    return await self._api_pwm_ramp(command, client)
                elif command.command_type == OpenPNPCommandType.QUEUE_STATUS:
                    return await self._api_queue_status(command)
                elif command.command_type == OpenPNPCommandType.QUEUE_CLEAR:
                    return await self._api_queue_clear(command)
                elif command.command_type == OpenPNPCommandType.CANCEL:
                    return await self._api_cancel(command)
                elif command.command_type == OpenPNPCommandType.PAUSE:
                    return await self._api_pause(command)
                elif command.command_type == OpenPNPCommandType.RESUME:
                    return await self._api_resume(command)
                elif command.command_type == OpenPNPCommandType.RESET:
                    return await self._api_reset(command)
                else:
                    return OpenPNPResponse(
                        status=ResponseStatus.ERROR,
                        command=command.command_type.value,
                        error_message=f"Direct API not implemented for: {command.command_type.value}",
                        error_code="NOT_IMPLEMENTED"
                    )
            except Exception as e:
                return OpenPNPResponse(
                    status=ResponseStatus.ERROR,
                    command=command.command_type.value,
                    error_message=str(e),
                    error_code="API_ERROR"
                )
    
    async def _execute_gcode(self, command: OpenPNPCommand) -> OpenPNPResponse:
        """Execute command via G-code translation.
        
        Args:
            command: OpenPNP command to execute
            
        Returns:
            OpenPNPResponse object
        """
        try:
            # Convert OpenPNP command to G-code
            gcode = self._convert_to_gcode(command)
            
            # Execute G-code
            handler = self._get_execution_handler()
            result = await handler.execute_single(gcode, timeout=self.default_timeout)
            
            # Build response
            if result.status == ExecutionStatus.COMPLETED:
                return OpenPNPResponse(
                    status=ResponseStatus.SUCCESS,
                    command=command.command_type.value,
                    command_id=command.id,
                    data={
                        'gcode': gcode,
                        'execution_time': result.execution_time,
                        'response': result.response
                    }
                )
            else:
                return OpenPNPResponse(
                    status=ResponseStatus.ERROR,
                    command=command.command_type.value,
                    command_id=command.id,
                    error_message=result.error_message or "G-code execution failed",
                    error_code="GCODE_EXECUTION_FAILED",
                    data={'gcode': gcode}
                )
        
        except Exception as e:
            return OpenPNPResponse(
                status=ResponseStatus.ERROR,
                command=command.command_type.value,
                command_id=command.id,
                error_message=str(e),
                error_code="GCODE_ERROR"
            )
    
    async def _execute_hybrid(self, command: OpenPNPCommand) -> OpenPNPResponse:
        """Execute command using hybrid approach (API + G-code).
        
        Args:
            command: OpenPNP command to execute
            
        Returns:
            OpenPNPResponse object
        """
        try:
            data = {}
            
            if command.command_type == OpenPNPCommandType.GET_STATUS:
                # Get comprehensive status
                async with self.gcode_translator.get_moonraker_client() as client:
                    printer_status = await client.get_printer_status()
                    klippy_state = await client.get_klippy_state()
                
                handler = self._get_execution_handler()
                stats = await handler.get_statistics()
                
                data = {
                    'printer_status': printer_status,
                    'klippy_state': klippy_state,
                    'execution_statistics': stats,
                    'internal_state': self._state
                }
            
            elif command.command_type == OpenPNPCommandType.GET_POSITION:
                # Get current position
                data = {
                    'position': self._state['current_position'],
                    'positioning_mode': self.gcode_translator.context.positioning_mode,
                    'units': self.gcode_translator.context.units
                }
            
            elif command.command_type == OpenPNPCommandType.GET_PRINTER_STATE:
                # Get printer state
                async with self.gcode_translator.get_moonraker_client() as client:
                    printer_status = await client.get_printer_status()
                    klippy_state = await client.get_klippy_state()
                
                data = {
                    'printer_status': printer_status,
                    'klippy_state': klippy_state,
                    'connected': klippy_state == 'ready'
                }
            
            else:
                return OpenPNPResponse(
                    status=ResponseStatus.ERROR,
                    command=command.command_type.value,
                    error_message=f"Hybrid execution not implemented for: {command.command_type.value}",
                    error_code="NOT_IMPLEMENTED"
                )
            
            return OpenPNPResponse(
                status=ResponseStatus.SUCCESS,
                command=command.command_type.value,
                command_id=command.id,
                data=data
            )
        
        except Exception as e:
            return OpenPNPResponse(
                status=ResponseStatus.ERROR,
                command=command.command_type.value,
                command_id=command.id,
                error_message=str(e),
                error_code="HYBRID_ERROR"
            )
    
    def _convert_to_gcode(self, command: OpenPNPCommand) -> str:
        """Convert OpenPNP command to G-code string.
        
        Args:
            command: OpenPNP command to convert
            
        Returns:
            G-code string
        """
        params = command.parameters
        cmd_type = command.command_type
        
        # Motion commands
        if cmd_type == OpenPNPCommandType.MOVE:
            x = params.get('x')
            y = params.get('y')
            z = params.get('z')
            f = params.get('feedrate', self.gcode_translator.context.feedrate)
            
            gcode_parts = ['G0']
            if x is not None:
                gcode_parts.append(f'X{x}')
            if y is not None:
                gcode_parts.append(f'Y{y}')
            if z is not None:
                gcode_parts.append(f'Z{z}')
            gcode_parts.append(f'F{f}')
            
            return ' '.join(gcode_parts)
        
        elif cmd_type == OpenPNPCommandType.MOVE_ABSOLUTE:
            return 'G90'
        
        elif cmd_type == OpenPNPCommandType.MOVE_RELATIVE:
            return 'G91'
        
        elif cmd_type == OpenPNPCommandType.HOME:
            axes = params.get('axes', 'all')
            if axes == 'all':
                return 'G28'
            else:
                return f'G28 {axes}'
        
        # Pick and place commands
        elif cmd_type == OpenPNPCommandType.PICK:
            z = params.get('z', params.get('pick_height', 0.0))
            f = params.get('feedrate', self.gcode_translator.context.feedrate)
            vacuum_power = params.get('vacuum_power', 255)
            travel_height = params.get('travel_height', 5.0)
            
            return f'G0 Z{z} F{f}\nM106 S{vacuum_power}\nG0 Z{travel_height}'
        
        elif cmd_type == OpenPNPCommandType.PLACE:
            z = params.get('z', params.get('place_height', 0.0))
            f = params.get('feedrate', self.gcode_translator.context.feedrate)
            travel_height = params.get('travel_height', 5.0)
            
            return f'G0 Z{z} F{f}\nM107\nG0 Z{travel_height}'
        
        elif cmd_type == OpenPNPCommandType.PICK_AND_PLACE:
            x = params.get('x', 0.0)
            y = params.get('y', 0.0)
            place_x = params.get('place_x', 0.0)
            place_y = params.get('place_y', 0.0)
            pick_height = params.get('pick_height', 0.0)
            place_height = params.get('place_height', 0.0)
            safe_height = params.get('safe_height', 10.0)
            f = params.get('feedrate', self.gcode_translator.context.feedrate)
            vacuum_power = params.get('vacuum_power', 255)
            
            return f'''G0 Z{safe_height} F{f}
G0 X{x} Y{y} F{f}
G0 Z{pick_height} F{f}
M106 S{vacuum_power}
G0 Z{safe_height} F{f}
G0 X{place_x} Y{place_y} F{f}
G0 Z{place_height} F{f}
M107
G0 Z{safe_height} F{f}'''
        
        # Actuator commands
        elif cmd_type == OpenPNPCommandType.ACTUATE:
            pin = params.get('pin')
            value = params.get('value', 1)
            return f'SET_PIN PIN={pin} VALUE={value}'
        
        elif cmd_type == OpenPNPCommandType.ACTUATE_ON:
            pin = params.get('pin')
            return f'SET_PIN PIN={pin} VALUE=1'
        
        elif cmd_type == OpenPNPCommandType.ACTUATE_OFF:
            pin = params.get('pin')
            return f'SET_PIN PIN={pin} VALUE=0'
        
        # Vacuum commands
        elif cmd_type == OpenPNPCommandType.VACUUM_ON:
            power = params.get('power', 255)
            return f'M106 S{power}'
        
        elif cmd_type == OpenPNPCommandType.VACUUM_OFF:
            return 'M107'
        
        elif cmd_type == OpenPNPCommandType.VACUUM_SET:
            power = params.get('power', 0)
            return f'M106 S{power}'
        
        # Fan commands
        elif cmd_type == OpenPNPCommandType.FAN_ON:
            speed = params.get('speed', 255)
            return f'M106 S{speed}'
        
        elif cmd_type == OpenPNPCommandType.FAN_OFF:
            return 'M107'
        
        elif cmd_type == OpenPNPCommandType.GPIO_WRITE:
            pin = params.get('pin')
            value = params.get('value', 1)
            return f'SET_PIN PIN={pin} VALUE={value}'
        
        # Feeder commands
        elif cmd_type == OpenPNPCommandType.FEEDER_ADVANCE:
            distance = params.get('distance', 10.0)
            f = params.get('feedrate', 100.0)
            return f'G0 E{distance} F{f}'
        
        elif cmd_type == OpenPNPCommandType.FEEDER_RETRACT:
            distance = params.get('distance', 10.0)
            f = params.get('feedrate', 100.0)
            return f'G0 E-{distance} F{f}'
        
        # Default: return empty string
        return ''
    
    # Direct API implementations
    
    async def _api_gpio_read(self, command: OpenPNPCommand, 
                            client: MoonrakerClient) -> OpenPNPResponse:
        """Read GPIO state via Moonraker API.
        
        Args:
            command: OpenPNP command
            client: Moonraker client
            
        Returns:
            OpenPNPResponse object
        """
        try:
            # Call Moonraker GPIO monitor endpoint
            pin_name = command.parameters.get('pin')
            
            if pin_name:
                # Read specific pin
                url = f"{client.base_url}/api/gpio_monitor/input/{pin_name}"
                async with client.session.get(url) as response:
                    data = await response.json()
            else:
                # Read all pins
                url = f"{client.base_url}/api/gpio_monitor/inputs"
                async with client.session.get(url) as response:
                    data = await response.json()
            
            if data.get('success'):
                return OpenPNPResponse(
                    status=ResponseStatus.SUCCESS,
                    command=command.command_type.value,
                    command_id=command.id,
                    data=data
                )
            else:
                return OpenPNPResponse(
                    status=ResponseStatus.ERROR,
                    command=command.command_type.value,
                    command_id=command.id,
                    error_message=data.get('error', 'GPIO read failed'),
                    error_code="GPIO_READ_FAILED"
                )
        
        except Exception as e:
            return OpenPNPResponse(
                status=ResponseStatus.ERROR,
                command=command.command_type.value,
                command_id=command.id,
                error_message=str(e),
                error_code="GPIO_API_ERROR"
            )
    
    async def _api_sensor_read(self, command: OpenPNPCommand,
                              client: MoonrakerClient) -> OpenPNPResponse:
        """Read sensor data via Moonraker API.
        
        Args:
            command: OpenPNP command
            client: Moonraker client
            
        Returns:
            OpenPNPResponse object
        """
        try:
            sensor_name = command.parameters.get('sensor')
            sensor_type = command.parameters.get('type')
            
            if sensor_name:
                # Read specific sensor
                url = f"{client.base_url}/api/sensor_query/{sensor_name}"
            elif sensor_type:
                # Read all sensors of a type
                url = f"{client.base_url}/api/sensor_query/type/{sensor_type}"
            else:
                # Read all sensors
                url = f"{client.base_url}/api/sensor_query/all"
            
            async with client.session.get(url) as response:
                data = await response.json()
            
            if data.get('success'):
                return OpenPNPResponse(
                    status=ResponseStatus.SUCCESS,
                    command=command.command_type.value,
                    command_id=command.id,
                    data=data
                )
            else:
                return OpenPNPResponse(
                    status=ResponseStatus.ERROR,
                    command=command.command_type.value,
                    command_id=command.id,
                    error_message=data.get('error', 'Sensor read failed'),
                    error_code="SENSOR_READ_FAILED"
                )
        
        except Exception as e:
            return OpenPNPResponse(
                status=ResponseStatus.ERROR,
                command=command.command_type.value,
                command_id=command.id,
                error_message=str(e),
                error_code="SENSOR_API_ERROR"
            )
    
    async def _api_sensor_read_all(self, command: OpenPNPCommand,
                                  client: MoonrakerClient) -> OpenPNPResponse:
        """Read all sensor data via Moonraker API.
        
        Args:
            command: OpenPNP command
            client: Moonraker client
            
        Returns:
            OpenPNPResponse object
        """
        try:
            url = f"{client.base_url}/api/sensor_query/all"
            async with client.session.get(url) as response:
                data = await response.json()
            
            if data.get('success'):
                return OpenPNPResponse(
                    status=ResponseStatus.SUCCESS,
                    command=command.command_type.value,
                    command_id=command.id,
                    data=data
                )
            else:
                return OpenPNPResponse(
                    status=ResponseStatus.ERROR,
                    command=command.command_type.value,
                    command_id=command.id,
                    error_message=data.get('error', 'Sensor read failed'),
                    error_code="SENSOR_READ_FAILED"
                )
        
        except Exception as e:
            return OpenPNPResponse(
                status=ResponseStatus.ERROR,
                command=command.command_type.value,
                command_id=command.id,
                error_message=str(e),
                error_code="SENSOR_API_ERROR"
            )
    
    async def _api_fan_set(self, command: OpenPNPCommand,
                            client: MoonrakerClient) -> OpenPNPResponse:
        """Set fan speed via Moonraker API.
        
        Args:
            command: OpenPNP command
            client: Moonraker client
            
        Returns:
            OpenPNPResponse object
        """
        try:
            speed = command.parameters.get('speed', 0.5)
            fan_name = command.parameters.get('fan', 'fan')
            
            url = f"{client.base_url}/api/fan_control/set"
            payload = {'speed': speed, 'fan_name': fan_name}
            
            async with client.session.post(url, json=payload) as response:
                data = await response.json()
            
            if data.get('success'):
                return OpenPNPResponse(
                    status=ResponseStatus.SUCCESS,
                    command=command.command_type.value,
                    command_id=command.id,
                    data=data
                )
            else:
                return OpenPNPResponse(
                    status=ResponseStatus.ERROR,
                    command=command.command_type.value,
                    command_id=command.id,
                    error_message=data.get('error', 'Fan control failed'),
                    error_code="FAN_CONTROL_FAILED"
                )
        
        except Exception as e:
            return OpenPNPResponse(
                status=ResponseStatus.ERROR,
                command=command.command_type.value,
                command_id=command.id,
                error_message=str(e),
                error_code="FAN_API_ERROR"
            )
    
    async def _api_pwm_set(self, command: OpenPNPCommand,
                          client: MoonrakerClient) -> OpenPNPResponse:
        """Set PWM value via Moonraker API.
        
        Args:
            command: OpenPNP command
            client: Moonraker client
            
        Returns:
            OpenPNPResponse object
        """
        try:
            value = command.parameters.get('value', 0.0)
            pin_name = command.parameters.get('pin')
            
            url = f"{client.base_url}/api/pwm_control/set"
            payload = {'value': value, 'pin_name': pin_name}
            
            async with client.session.post(url, json=payload) as response:
                data = await response.json()
            
            if data.get('success'):
                return OpenPNPResponse(
                    status=ResponseStatus.SUCCESS,
                    command=command.command_type.value,
                    command_id=command.id,
                    data=data
                )
            else:
                return OpenPNPResponse(
                    status=ResponseStatus.ERROR,
                    command=command.command_type.value,
                    command_id=command.id,
                    error_message=data.get('error', 'PWM control failed'),
                    error_code="PWM_CONTROL_FAILED"
                )
        
        except Exception as e:
            return OpenPNPResponse(
                status=ResponseStatus.ERROR,
                command=command.command_type.value,
                command_id=command.id,
                error_message=str(e),
                error_code="PWM_API_ERROR"
            )
    
    async def _api_pwm_ramp(self, command: OpenPNPCommand,
                           client: MoonrakerClient) -> OpenPNPResponse:
        """Ramp PWM value via Moonraker API.
        
        Args:
            command: OpenPNP command
            client: Moonraker client
            
        Returns:
            OpenPNPResponse object
        """
        try:
            start_value = command.parameters.get('start_value', 0.0)
            end_value = command.parameters.get('end_value', 1.0)
            pin_name = command.parameters.get('pin')
            duration = command.parameters.get('duration', 1.0)
            steps = command.parameters.get('steps', 10)
            
            url = f"{client.base_url}/api/pwm_control/ramp"
            payload = {
                'start_value': start_value,
                'end_value': end_value,
                'pin_name': pin_name,
                'duration': duration,
                'steps': steps
            }
            
            async with client.session.post(url, json=payload) as response:
                data = await response.json()
            
            if data.get('success'):
                return OpenPNPResponse(
                    status=ResponseStatus.SUCCESS,
                    command=command.command_type.value,
                    command_id=command.id,
                    data=data
                )
            else:
                return OpenPNPResponse(
                    status=ResponseStatus.ERROR,
                    command=command.command_type.value,
                    command_id=command.id,
                    error_message=data.get('error', 'PWM ramp failed'),
                    error_code="PWM_RAMP_FAILED"
                )
        
        except Exception as e:
            return OpenPNPResponse(
                status=ResponseStatus.ERROR,
                command=command.command_type.value,
                command_id=command.id,
                error_message=str(e),
                error_code="PWM_API_ERROR"
            )
    
    async def _api_queue_status(self, command: OpenPNPCommand) -> OpenPNPResponse:
        """Get queue status.
        
        Args:
            command: OpenPNP command
            
        Returns:
            OpenPNPResponse object
        """
        try:
            handler = self._get_execution_handler()
            status = await handler.get_queue_status()
            
            return OpenPNPResponse(
                status=ResponseStatus.SUCCESS,
                command=command.command_type.value,
                command_id=command.id,
                data=status
            )
        
        except Exception as e:
            return OpenPNPResponse(
                status=ResponseStatus.ERROR,
                command=command.command_type.value,
                command_id=command.id,
                error_message=str(e),
                error_code="QUEUE_STATUS_ERROR"
            )
    
    async def _api_queue_clear(self, command: OpenPNPCommand) -> OpenPNPResponse:
        """Clear command queue.
        
        Args:
            command: OpenPNP command
            
        Returns:
            OpenPNPResponse object
        """
        try:
            handler = self._get_execution_handler()
            await handler.clear_queue()
            
            return OpenPNPResponse(
                status=ResponseStatus.SUCCESS,
                command=command.command_type.value,
                command_id=command.id,
                data={'message': 'Queue cleared'}
            )
        
        except Exception as e:
            return OpenPNPResponse(
                status=ResponseStatus.ERROR,
                command=command.command_type.value,
                command_id=command.id,
                error_message=str(e),
                error_code="QUEUE_CLEAR_ERROR"
            )
    
    async def _api_cancel(self, command: OpenPNPCommand) -> OpenPNPResponse:
        """Cancel current execution.
        
        Args:
            command: OpenPNP command
            
        Returns:
            OpenPNPResponse object
        """
        try:
            handler = self._get_execution_handler()
            await handler.cancel_execution()
            
            return OpenPNPResponse(
                status=ResponseStatus.SUCCESS,
                command=command.command_type.value,
                command_id=command.id,
                data={'message': 'Execution cancelled'}
            )
        
        except Exception as e:
            return OpenPNPResponse(
                status=ResponseStatus.ERROR,
                command=command.command_type.value,
                command_id=command.id,
                error_message=str(e),
                error_code="CANCEL_ERROR"
            )
    
    async def _api_pause(self, command: OpenPNPCommand) -> OpenPNPResponse:
        """Pause execution.
        
        Args:
            command: OpenPNP command
            
        Returns:
            OpenPNPResponse object
        """
        try:
            handler = self._get_execution_handler()
            await handler.pause()
            
            return OpenPNPResponse(
                status=ResponseStatus.SUCCESS,
                command=command.command_type.value,
                command_id=command.id,
                data={'message': 'Execution paused'}
            )
        
        except Exception as e:
            return OpenPNPResponse(
                status=ResponseStatus.ERROR,
                command=command.command_type.value,
                command_id=command.id,
                error_message=str(e),
                error_code="PAUSE_ERROR"
            )
    
    async def _api_resume(self, command: OpenPNPCommand) -> OpenPNPResponse:
        """Resume execution.
        
        Args:
            command: OpenPNP command
            
        Returns:
            OpenPNPResponse object
        """
        try:
            handler = self._get_execution_handler()
            await handler.resume()
            
            return OpenPNPResponse(
                status=ResponseStatus.SUCCESS,
                command=command.command_type.value,
                command_id=command.id,
                data={'message': 'Execution resumed'}
            )
        
        except Exception as e:
            return OpenPNPResponse(
                status=ResponseStatus.ERROR,
                command=command.command_type.value,
                command_id=command.id,
                error_message=str(e),
                error_code="RESUME_ERROR"
            )
    
    async def _api_reset(self, command: OpenPNPCommand) -> OpenPNPResponse:
        """Reset execution handler.
        
        Args:
            command: OpenPNP command
            
        Returns:
            OpenPNPResponse object
        """
        try:
            handler = self._get_execution_handler()
            await handler.reset()
            self.gcode_translator.reset_context()
            
            return OpenPNPResponse(
                status=ResponseStatus.SUCCESS,
                command=command.command_type.value,
                command_id=command.id,
                data={'message': 'System reset'}
            )
        
        except Exception as e:
            return OpenPNPResponse(
                status=ResponseStatus.ERROR,
                command=command.command_type.value,
                command_id=command.id,
                error_message=str(e),
                error_code="RESET_ERROR"
            )
    
    # Batch and queue operations
    
    async def execute_batch(self, commands: List[Union[OpenPNPCommand, Dict[str, Any]]],
                          stop_on_error: bool = True) -> List[OpenPNPResponse]:
        """Execute multiple OpenPNP commands as a batch.
        
        Args:
            commands: List of OpenPNP commands
            stop_on_error: Stop on first error
            
        Returns:
            List of OpenPNPResponse objects
        """
        results = []
        
        logger.info(f"Executing batch of {len(commands)} commands")
        
        for cmd in commands:
            # Parse command if needed
            if isinstance(cmd, dict):
                cmd = self._parse_command_dict(cmd)
            
            # Execute command
            response = await self.translate_and_execute(cmd)
            results.append(response)
            
            # Stop on error if requested
            if response.status == ResponseStatus.ERROR and stop_on_error:
                logger.error(f"Batch execution stopped due to error at command: {cmd.command_type.value}")
                break
        
        return results
    
    async def enqueue_command(self, command: Union[OpenPNPCommand, Dict[str, Any]],
                            priority: int = 0) -> str:
        """Enqueue a command for later execution.
        
        Args:
            command: OpenPNP command to enqueue
            priority: Command priority
            
        Returns:
            Command ID
        """
        # Parse command if needed
        if isinstance(command, dict):
            command = self._parse_command_dict(command)
        
        # Convert to G-code
        gcode = self._convert_to_gcode(command)
        
        # Enqueue
        handler = self._get_execution_handler()
        command_id = await handler.enqueue_command(
            gcode,
            priority=priority,
            context=command.parameters,
            metadata=command.metadata
        )
        
        logger.info(f"Enqueued command {command.command_type.value} with ID: {command_id}")
        return command_id
    
    async def process_queue(self, stop_on_error: bool = True) -> List[OpenPNPResponse]:
        """Process all commands in the queue.
        
        Args:
            stop_on_error: Stop on first error
            
        Returns:
            List of OpenPNPResponse objects
        """
        try:
            handler = self._get_execution_handler()
            execution_results = await handler.process_queue(stop_on_error=stop_on_error)
            
            # Convert to OpenPNP responses
            responses = []
            for result in execution_results:
                if result.status == ExecutionStatus.COMPLETED:
                    response = OpenPNPResponse(
                        status=ResponseStatus.SUCCESS,
                        command='queued_command',
                        data={
                            'gcode': result.gcode,
                            'execution_time': result.execution_time
                        }
                    )
                else:
                    response = OpenPNPResponse(
                        status=ResponseStatus.ERROR,
                        command='queued_command',
                        error_message=result.error_message,
                        error_code="QUEUE_EXECUTION_FAILED"
                    )
                responses.append(response)
            
            return responses
        
        except Exception as e:
            logger.error(f"Error processing queue: {e}")
            return [OpenPNPResponse(
                status=ResponseStatus.ERROR,
                command='queue_process',
                error_message=str(e),
                error_code="QUEUE_PROCESS_ERROR"
            )]
    
    # State management
    
    def _update_state(self, command: OpenPNPCommand, response: OpenPNPResponse) -> None:
        """Update internal state based on command and response.
        
        Args:
            command: OpenPNP command that was executed
            response: Response from command execution
        """
        if response.status != ResponseStatus.SUCCESS:
            return
        
        cmd_type = command.command_type
        params = command.parameters
        
        # Update position
        if cmd_type in [OpenPNPCommandType.MOVE, OpenPNPCommandType.PICK, 
                        OpenPNPCommandType.PLACE, OpenPNPCommandType.PICK_AND_PLACE]:
            if 'x' in params:
                self._state['current_position']['x'] = params['x']
            if 'y' in params:
                self._state['current_position']['y'] = params['y']
            if 'z' in params:
                self._state['current_position']['z'] = params['z']
        
        # Update vacuum state
        if cmd_type == OpenPNPCommandType.VACUUM_ON:
            self._state['vacuum_enabled'] = True
        elif cmd_type == OpenPNPCommandType.VACUUM_OFF:
            self._state['vacuum_enabled'] = False
        
        # Update fan speed
        if cmd_type == OpenPNPCommandType.FAN_SET:
            self._state['fan_speed'] = params.get('speed', 0.0)
        elif cmd_type == OpenPNPCommandType.FAN_ON:
            self._state['fan_speed'] = 1.0
        elif cmd_type == OpenPNPCommandType.FAN_OFF:
            self._state['fan_speed'] = 0.0
        
        # Update actuator state
        if cmd_type in [OpenPNPCommandType.ACTUATE, OpenPNPCommandType.ACTUATE_ON,
                        OpenPNPCommandType.ACTUATE_OFF]:
            pin = params.get('pin')
            if pin:
                if cmd_type == OpenPNPCommandType.ACTUATE_OFF:
                    self._state['actuators'][pin] = 0
                else:
                    value = params.get('value', 1) if cmd_type == OpenPNPCommandType.ACTUATE else 1
                    self._state['actuators'][pin] = value
    
    def get_state(self) -> Dict[str, Any]:
        """Get current internal state.
        
        Returns:
            Dictionary containing current state
        """
        return self._state.copy()
    
    def reset_state(self) -> None:
        """Reset internal state to defaults."""
        self._state = {
            'current_position': {'x': 0.0, 'y': 0.0, 'z': 0.0},
            'vacuum_enabled': False,
            'fan_speed': 0.0,
            'actuators': {},
            'klippy_connected': False
        }
        logger.info("Internal state reset")
    
    # Convenience methods
    
    async def get_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get execution history.
        
        Args:
            limit: Maximum number of entries
            
        Returns:
            List of history entries
        """
        handler = self._get_execution_handler()
        return await handler.get_history(limit=limit)
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get execution statistics.
        
        Returns:
            Dictionary containing statistics
        """
        handler = self._get_execution_handler()
        return await handler.get_statistics()
    
    async def get_queue_info(self) -> Dict[str, Any]:
        """Get queue information.
        
        Returns:
            Dictionary containing queue information
        """
        handler = self._get_execution_handler()
        return await handler.get_queue_status()
    
    def add_custom_template(self, name: str, template: str) -> None:
        """Add a custom G-code template.
        
        Args:
            name: Template name
            template: G-code template string
        """
        self.gcode_translator.add_template(name, template)
        logger.info(f"Added custom template: {name}")
    
    def add_custom_validator(self, param_name: str, 
                          validator: Callable[[Any], bool]) -> None:
        """Add a custom parameter validator.
        
        Args:
            param_name: Parameter name
            validator: Validator function
        """
        self.gcode_translator.add_validator(param_name, validator)
        logger.info(f"Added custom validator for parameter: {param_name}")


# Convenience functions

async def execute_openpnp_command(command: Union[OpenPNPCommand, Dict[str, Any]],
                                  moonraker_host: str = 'localhost',
                                  moonraker_port: int = 7125,
                                  moonraker_api_key: Optional[str] = None) -> OpenPNPResponse:
    """Execute a single OpenPNP command with default configuration.
    
    Args:
        command: OpenPNP command or command dictionary
        moonraker_host: Moonraker host address
        moonraker_port: Moonraker port
        moonraker_api_key: Optional Moonraker API key
        
    Returns:
        OpenPNPResponse object
    """
    translator = OpenPNPTranslator(
        moonraker_host=moonraker_host,
        moonraker_port=moonraker_port,
        moonraker_api_key=moonraker_api_key
    )
    
    return await translator.translate_and_execute(command)


async def execute_openpnp_batch(commands: List[Union[OpenPNPCommand, Dict[str, Any]]],
                                moonraker_host: str = 'localhost',
                                moonraker_port: int = 7125,
                                moonraker_api_key: Optional[str] = None,
                                stop_on_error: bool = True) -> List[OpenPNPResponse]:
    """Execute a batch of OpenPNP commands with default configuration.
    
    Args:
        commands: List of OpenPNP commands or command dictionaries
        moonraker_host: Moonraker host address
        moonraker_port: Moonraker port
        moonraker_api_key: Optional Moonraker API key
        stop_on_error: Stop on first error
        
    Returns:
        List of OpenPNPResponse objects
    """
    translator = OpenPNPTranslator(
        moonraker_host=moonraker_host,
        moonraker_port=moonraker_port,
        moonraker_api_key=moonraker_api_key
    )
    
    return await translator.execute_batch(commands, stop_on_error)


def create_translator(moonraker_host: str = 'localhost',
                     moonraker_port: int = 7125,
                     moonraker_api_key: Optional[str] = None,
                     max_queue_size: int = 1000,
                     max_history_entries: int = 1000,
                     default_timeout: float = 30.0) -> OpenPNPTranslator:
    """Create an OpenPNPTranslator instance with configuration.
    
    Args:
        moonraker_host: Moonraker host address
        moonraker_port: Moonraker port
        moonraker_api_key: Optional Moonraker API key
        max_queue_size: Maximum queue size
        max_history_entries: Maximum history entries
        default_timeout: Default execution timeout
        
    Returns:
        OpenPNPTranslator instance
    """
    return OpenPNPTranslator(
        moonraker_host=moonraker_host,
        moonraker_port=moonraker_port,
        moonraker_api_key=moonraker_api_key,
        max_queue_size=max_queue_size,
        max_history_entries=max_history_entries,
        default_timeout=default_timeout
    )
