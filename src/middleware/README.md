# KlipperPlace Middleware - Translation Layer

## Overview

The translation layer (`translator.py`) provides the core interface between OpenPNP and Moonraker/Klipper. It translates OpenPNP commands into appropriate Moonraker API calls or G-code commands, manages command queuing and batching, and provides a unified response format.

## Architecture

```
OpenPNP Commands
       ↓
OpenPNP Translator
       ↓
   ┌─────┴─────┐
   │             │
Direct API    G-code Translation
   │             │
   ↓             ↓
Moonraker Extensions  →  G-code Driver
   │             │
   └─────┬─────┘
         ↓
   Klipper Firmware
```

## Components

### 1. OpenPNPCommandType

Enumeration of all supported OpenPNP command types:

- **Motion Commands**: `MOVE`, `MOVE_ABSOLUTE`, `MOVE_RELATIVE`, `HOME`
- **Pick and Place**: `PICK`, `PLACE`, `PICK_AND_PLACE`
- **Actuator Commands**: `ACTUATE`, `ACTUATE_ON`, `ACTUATE_OFF`
- **Vacuum Commands**: `VACUUM_ON`, `VACUUM_OFF`, `VACUUM_SET`
- **Fan Commands**: `FAN_ON`, `FAN_OFF`, `FAN_SET`
- **PWM Commands**: `PWM_SET`, `PWM_RAMP`
- **GPIO Commands**: `GPIO_READ`, `GPIO_WRITE`
- **Sensor Commands**: `SENSOR_READ`, `SENSOR_READ_ALL`
- **Feeder Commands**: `FEEDER_ADVANCE`, `FEEDER_RETRACT`
- **Status Commands**: `GET_STATUS`, `GET_POSITION`, `GET_PRINTER_STATE`
- **Queue Commands**: `QUEUE_COMMAND`, `QUEUE_BATCH`, `QUEUE_STATUS`, `QUEUE_CLEAR`
- **System Commands**: `CANCEL`, `PAUSE`, `RESUME`, `RESET`

### 2. TranslationStrategy

Defines how commands are executed:

- **DIRECT_API**: Uses Moonraker extension APIs directly (GPIO, sensors, fans, PWM)
- **GCODE**: Translates to G-code and executes via G-code driver
- **HYBRID**: Combines API calls and G-code for complex operations

### 3. OpenPNPResponse

Unified response format for all commands:

```python
@dataclass
class OpenPNPResponse:
    status: ResponseStatus           # SUCCESS, ERROR, PARTIAL, TIMEOUT, CANCELLED
    command: str                    # Command type that was executed
    command_id: str                  # Unique command identifier
    data: Optional[Dict[str, Any]]  # Response data
    error_message: Optional[str]      # Error description if failed
    error_code: Optional[str]         # Error code for programmatic handling
    warnings: List[str]               # Warning messages
    execution_time: float              # Execution time in seconds
    timestamp: float                  # Unix timestamp
```

### 4. OpenPNPTranslator

Main translator class that coordinates all operations:

```python
class OpenPNPTranslator:
    def __init__(self,
                 moonraker_host: str = 'localhost',
                 moonraker_port: int = 7125,
                 moonraker_api_key: Optional[str] = None,
                 max_queue_size: int = 1000,
                 max_history_entries: int = 1000,
                 default_timeout: float = 30.0)
```

## Usage Examples

### Basic Command Execution

```python
import asyncio
from middleware.translator import (
    OpenPNPCommand,
    OpenPNPCommandType,
    create_translator
)

async def main():
    # Create translator instance
    translator = create_translator(
        moonraker_host='localhost',
        moonraker_port=7125
    )
    
    # Execute a move command
    command = OpenPNPCommand(
        command_type=OpenPNPCommandType.MOVE,
        parameters={
            'x': 100.0,
            'y': 50.0,
            'z': 10.0,
            'feedrate': 1500.0
        }
    )
    
    response = await translator.translate_and_execute(command)
    
    if response.status == ResponseStatus.SUCCESS:
        print(f"Command executed successfully: {response.data}")
    else:
        print(f"Command failed: {response.error_message}")

asyncio.run(main())
```

### Pick and Place Operation

```python
# Pick operation
pick_command = OpenPNPCommand(
    command_type=OpenPNPCommandType.PICK,
    parameters={
        'pick_height': 0.0,
        'vacuum_power': 255,
        'travel_height': 5.0,
        'feedrate': 1000.0
    }
)

response = await translator.translate_and_execute(pick_command)

# Place operation
place_command = OpenPNPCommand(
    command_type=OpenPNPCommandType.PLACE,
    parameters={
        'place_height': 0.0,
        'travel_height': 5.0,
        'feedrate': 1000.0
    }
)

response = await translator.translate_and_execute(place_command)
```

### Complete Pick and Place Sequence

```python
# Single command for complete pick and place
pnp_command = OpenPNPCommand(
    command_type=OpenPNPCommandType.PICK_AND_PLACE,
    parameters={
        'x': 100.0,
        'y': 50.0,
        'place_x': 200.0,
        'place_y': 100.0,
        'pick_height': 0.0,
        'place_height': 0.0,
        'safe_height': 10.0,
        'feedrate': 1500.0,
        'vacuum_power': 255
    }
)

response = await translator.translate_and_execute(pnp_command)
```

### Batch Command Execution

```python
# Execute multiple commands as a batch
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
        command_type=OpenPNPCommandType.PICK,
        parameters={'pick_height': 0.0, 'vacuum_power': 255}
    )
]

responses = await translator.execute_batch(commands, stop_on_error=True)

for response in responses:
    print(f"Command: {response.command}, Status: {response.status.value}")
```

### Command Queuing

```python
# Enqueue commands for later execution
command_id = await translator.enqueue_command(
    OpenPNPCommand(
        command_type=OpenPNPCommandType.MOVE,
        parameters={'x': 100.0, 'y': 50.0},
        priority=10  # Higher priority = executed first
    )
)

print(f"Command enqueued with ID: {command_id}")

# Process the queue
responses = await translator.process_queue(stop_on_error=True)
```

### Direct API Calls

```python
# Read GPIO state
gpio_command = OpenPNPCommand(
    command_type=OpenPNPCommandType.GPIO_READ,
    parameters={'pin': 'vacuum_sensor'}
)

response = await translator.translate_and_execute(gpio_command)
print(f"GPIO state: {response.data}")

# Read sensor data
sensor_command = OpenPNPCommand(
    command_type=OpenPNPCommandType.SENSOR_READ,
    parameters={'sensor': 'pressure_sensor'}
)

response = await translator.translate_and_execute(sensor_command)
print(f"Sensor data: {response.data}")

# Set fan speed
fan_command = OpenPNPCommand(
    command_type=OpenPNPCommandType.FAN_SET,
    parameters={'speed': 0.5, 'fan': 'fan'}
)

response = await translator.translate_and_execute(fan_command)
```

### Status Queries

```python
# Get comprehensive status
status_command = OpenPNPCommand(
    command_type=OpenPNPCommandType.GET_STATUS
)

response = await translator.translate_and_execute(status_command)
print(f"System status: {response.data}")

# Get current position
position_command = OpenPNPCommand(
    command_type=OpenPNPCommandType.GET_POSITION
)

response = await translator.translate_and_execute(position_command)
print(f"Current position: {response.data}")

# Get printer state
printer_command = OpenPNPCommand(
    command_type=OpenPNPCommandType.GET_PRINTER_STATE
)

response = await translator.translate_and_execute(printer_command)
print(f"Printer state: {response.data}")
```

### System Control

```python
# Cancel current execution
cancel_command = OpenPNPCommand(
    command_type=OpenPNPCommandType.CANCEL
)
response = await translator.translate_and_execute(cancel_command)

# Pause execution
pause_command = OpenPNPCommand(
    command_type=OpenPNPCommandType.PAUSE
)
response = await translator.translate_and_execute(pause_command)

# Resume execution
resume_command = OpenPNPCommand(
    command_type=OpenPNPCommandType.RESUME
)
response = await translator.translate_and_execute(resume_command)

# Reset system
reset_command = OpenPNPCommand(
    command_type=OpenPNPCommandType.RESET
)
response = await translator.translate_and_execute(reset_command)
```

### Custom Templates and Validators

```python
# Add custom G-code template
translator.add_custom_template(
    'custom_sequence',
    '''G0 Z{safe_height} F{feedrate}
G0 X{x} Y{y} F{feedrate}
M106 S{vacuum_power}
G0 Z{pick_height} F{feedrate}'''
)

# Add custom parameter validator
def validate_coordinate(value):
    return isinstance(value, (int, float)) and -1000 <= value <= 1000

translator.add_custom_validator('x', validate_coordinate)
translator.add_custom_validator('y', validate_coordinate)
translator.add_custom_validator('z', validate_coordinate)
```

## Command Translation Mapping

### Motion Commands

| OpenPNP Command | Translation Strategy | Generated G-code |
|------------------|---------------------|------------------|
| MOVE | G-code | `G0 X{x} Y{y} Z{z} F{feedrate}` |
| MOVE_ABSOLUTE | G-code | `G90` |
| MOVE_RELATIVE | G-code | `G91` |
| HOME | G-code | `G28` or `G28 X Y` |

### Pick and Place Commands

| OpenPNP Command | Translation Strategy | Generated G-code |
|------------------|---------------------|------------------|
| PICK | G-code | `G0 Z{pick_height}`, `M106 S{vacuum_power}`, `G0 Z{travel_height}` |
| PLACE | G-code | `G0 Z{place_height}`, `M107`, `G0 Z{travel_height}` |
| PICK_AND_PLACE | G-code | Multi-move sequence with vacuum control |

### Actuator Commands

| OpenPNP Command | Translation Strategy | Generated G-code |
|------------------|---------------------|------------------|
| ACTUATE | G-code | `SET_PIN PIN={pin} VALUE={value}` |
| ACTUATE_ON | G-code | `SET_PIN PIN={pin} VALUE=1` |
| ACTUATE_OFF | G-code | `SET_PIN PIN={pin} VALUE=0` |

### Vacuum Commands

| OpenPNP Command | Translation Strategy | Generated G-code |
|------------------|---------------------|------------------|
| VACUUM_ON | G-code | `M106 S{power}` |
| VACUUM_OFF | G-code | `M107` |
| VACUUM_SET | G-code | `M106 S{power}` |

### Fan Commands

| OpenPNP Command | Translation Strategy | Generated G-code |
|------------------|---------------------|------------------|
| FAN_ON | G-code | `M106 S{speed}` |
| FAN_OFF | G-code | `M107` |
| FAN_SET | Direct API | Moonraker fan control endpoint |

### PWM Commands

| OpenPNP Command | Translation Strategy | Moonraker Endpoint |
|------------------|---------------------|---------------------|
| PWM_SET | Direct API | `/api/pwm_control/set` |
| PWM_RAMP | Direct API | `/api/pwm_control/ramp` |

### GPIO Commands

| OpenPNP Command | Translation Strategy | Moonraker Endpoint |
|------------------|---------------------|---------------------|
| GPIO_READ | Direct API | `/api/gpio_monitor/inputs` |
| GPIO_WRITE | G-code | `SET_PIN PIN={pin} VALUE={value}` |

### Sensor Commands

| OpenPNP Command | Translation Strategy | Moonraker Endpoint |
|------------------|---------------------|---------------------|
| SENSOR_READ | Direct API | `/api/sensor_query/{sensor_name}` |
| SENSOR_READ_ALL | Direct API | `/api/sensor_query/all` |

## State Management

The translator maintains internal state for:

- **Current Position**: X, Y, Z coordinates
- **Vacuum State**: Enabled/disabled status
- **Fan Speed**: Current fan speed (0.0-1.0)
- **Actuator States**: Dictionary of actuator pin values
- **Klippy Connection**: Connection status to Klipper

Access state:
```python
state = translator.get_state()
print(f"Position: {state['current_position']}")
print(f"Vacuum enabled: {state['vacuum_enabled']}")

# Reset state
translator.reset_state()
```

## Error Handling

The translator provides comprehensive error handling:

### Error Codes

| Error Code | Description |
|-------------|-------------|
| UNKNOWN_STRATEGY | Translation strategy not found |
| NOT_IMPLEMENTED | Command not implemented |
| API_ERROR | Moonraker API call failed |
| GPIO_READ_FAILED | GPIO read operation failed |
| SENSOR_READ_FAILED | Sensor read operation failed |
| FAN_CONTROL_FAILED | Fan control operation failed |
| PWM_CONTROL_FAILED | PWM control operation failed |
| PWM_RAMP_FAILED | PWM ramp operation failed |
| GCODE_EXECUTION_FAILED | G-code execution failed |
| QUEUE_STATUS_ERROR | Queue status query failed |
| QUEUE_CLEAR_ERROR | Queue clear operation failed |
| CANCEL_ERROR | Cancel operation failed |
| PAUSE_ERROR | Pause operation failed |
| RESUME_ERROR | Resume operation failed |
| RESET_ERROR | Reset operation failed |
| EXECUTION_ERROR | General execution error |

### Error Response Format

```python
OpenPNPResponse(
    status=ResponseStatus.ERROR,
    command='move',
    command_id='uuid-here',
    error_message='Invalid parameter: x must be numeric',
    error_code='INVALID_PARAM',
    execution_time=0.001
)
```

## Queue and History

### Queue Operations

```python
# Get queue status
queue_info = await translator.get_queue_info()
print(f"Queue size: {queue_info['size']}")
print(f"Queue snapshot: {queue_info['snapshot']}")

# Clear queue
await translator._api_queue_clear(OpenPNPCommand(command_type=OpenPNPCommandType.QUEUE_CLEAR))
```

### History Operations

```python
# Get execution history
history = await translator.get_history(limit=100)
for entry in history:
    print(f"{entry['gcode']} - {entry['status']}")

# Get statistics
stats = await translator.get_statistics()
print(f"Total commands: {stats['total']}")
print(f"Success rate: {stats['success_rate']}%")
print(f"Average execution time: {stats['avg_execution_time']}s")
```

## Integration with Moonraker Extensions

The translator integrates with the following Moonraker extensions:

### GPIO Monitor Extension
- **Endpoint**: `/api/gpio_monitor/inputs`
- **Endpoint**: `/api/gpio_monitor/input/{pin_name}`
- **Used for**: Reading GPIO pin states

### Fan Control Extension
- **Endpoint**: `/api/fan_control/set`
- **Endpoint**: `/api/fan_control/off`
- **Endpoint**: `/api/fan_control/status`
- **Used for**: Fan speed control

### PWM Control Extension
- **Endpoint**: `/api/pwm_control/set`
- **Endpoint**: `/api/pwm_control/ramp`
- **Endpoint**: `/api/pwm_control/status`
- **Used for**: PWM output control and ramping

### Sensor Query Extension
- **Endpoint**: `/api/sensor_query/all`
- **Endpoint**: `/api/sensor_query/type/{sensor_type}`
- **Endpoint**: `/api/sensor_query/{sensor_name}`
- **Used for**: Reading sensor data

### WebSocket Notifier Extension
- **Events**: GPIO state changes, fan speed changes, PWM value changes, sensor alerts
- **Used for**: Real-time status updates

## Configuration

### Moonraker Connection

```python
translator = create_translator(
    moonraker_host='localhost',      # Moonraker host
    moonraker_port=7125,            # Moonraker port
    moonraker_api_key=None,            # Optional API key
    default_timeout=30.0               # Default timeout in seconds
)
```

### Queue and History

```python
translator = create_translator(
    max_queue_size=1000,               # Maximum commands in queue
    max_history_entries=1000            # Maximum history entries to retain
)
```

## Testing

Run the test suite:

```bash
python src/middleware/test_translator.py
```

Test suites include:
- Command Parsing
- G-code Translation
- Strategy Mapping
- Response Format
- State Management
- Command Types
- Batch Operations
- Custom Templates

## API Reference

### OpenPNPTranslator

#### Methods

```python
async def translate_and_execute(
    command: Union[OpenPNPCommand, Dict[str, Any]]
) -> OpenPNPResponse
```
Translate and execute a single OpenPNP command.

```python
async def execute_batch(
    commands: List[Union[OpenPNPCommand, Dict[str, Any]]],
    stop_on_error: bool = True
) -> List[OpenPNPResponse]
```
Execute multiple OpenPNP commands as a batch.

```python
async def enqueue_command(
    command: Union[OpenPNPCommand, Dict[str, Any]],
    priority: int = 0
) -> str
```
Enqueue a command for later execution.

```python
async def process_queue(
    stop_on_error: bool = True
) -> List[OpenPNPResponse]
```
Process all commands in the queue.

```python
def get_state() -> Dict[str, Any]
```
Get current internal state.

```python
def reset_state() -> None
```
Reset internal state to defaults.

```python
async def get_history(
    limit: Optional[int] = None
) -> List[Dict[str, Any]]
```
Get execution history.

```python
async def get_statistics() -> Dict[str, Any]
```
Get execution statistics.

```python
async def get_queue_info() -> Dict[str, Any]
```
Get queue information.

```python
def add_custom_template(name: str, template: str) -> None
```
Add a custom G-code template.

```python
def add_custom_validator(
    param_name: str,
    validator: Callable[[Any], bool]
) -> None
```
Add a custom parameter validator.

## Best Practices

1. **Use Command Queuing for Batch Operations**: Enqueue multiple commands instead of executing them individually for better performance.

2. **Set Appropriate Timeouts**: Adjust `default_timeout` based on your specific operations.

3. **Handle Errors Gracefully**: Always check `response.status` and handle errors appropriately.

4. **Use Priority for Critical Commands**: Set higher priority for commands that need to execute first.

5. **Monitor Queue Status**: Check queue size to prevent overflow.

6. **Review History for Debugging**: Use execution history to diagnose issues.

7. **Customize Templates**: Add custom templates for complex sequences specific to your use case.

8. **Validate Parameters**: Use custom validators to ensure parameter correctness.

## Troubleshooting

### Common Issues

**Issue**: Commands timing out
- **Solution**: Increase `default_timeout` parameter

**Issue**: Queue overflow
- **Solution**: Increase `max_queue_size` or process queue more frequently

**Issue**: G-code translation errors
- **Solution**: Check parameter names and values match expected format

**Issue**: Moonraker API errors
- **Solution**: Verify Moonraker is running and extensions are loaded

**Issue**: State inconsistency
- **Solution**: Call `reset_state()` to reset internal state

## License

This module is part of KlipperPlace and follows the project's licensing terms.

## Support

For issues, questions, or contributions, please refer to the main KlipperPlace project documentation.
