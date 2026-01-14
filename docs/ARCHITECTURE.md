# KlipperPlace Architecture Documentation

## Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Component Architecture](#component-architecture)
- [Integration Boundaries](#integration-boundaries)
- [Data Flows](#data-flows)
- [Design Decisions](#design-decisions)
- [Configuration Options](#configuration-options)
- [State Management](#state-management)
- [Error Handling](#error-handling)
- [Security Considerations](#security-considerations)
- [Performance Characteristics](#performance-characteristics)

---

## Overview

KlipperPlace is a middleware service that bridges Klipper firmware with OpenPNP 2.0 pick-and-place software. The system runs on the same Raspberry Pi host as Klipper and Moonraker, providing seamless integration through a REST API and WebSocket interface.

### Purpose

KlipperPlace enables Pick-and-Place (PnP) machines to leverage Klipper's real-time motion control architecture by:

- Translating OpenPNP operations to Klipper-compatible G-code
- Providing PnP-specific hardware control (GPIO, sensors, actuators, vacuum, fans)
- Offering real-time status updates via WebSocket
- Implementing safety mechanisms for hardware protection
- Caching hardware state for performance optimization

### Key Characteristics

- **Asynchronous Architecture**: Built on Python asyncio for concurrent operations
- **Event-Driven**: Uses WebSocket for real-time event notifications
- **Layered Design**: Clear separation between API, middleware, and hardware layers
- **Extensible**: Modular components allow easy addition of new features
- **Production-Ready**: Comprehensive error handling, logging, and monitoring

---

## System Architecture

### High-Level Architecture

```mermaid
graph TB
    subgraph "OpenPNP 2.0"
        OP[OpenPNP Application]
        KD[KlipperDriver]
    end
    
    subgraph "KlipperPlace Middleware"
        API[REST API Server]
        WS[WebSocket Server]
        MT[OpenPNP Translator]
        CM[State Cache Manager]
        SM[Safety Manager]
        EH[Execution Handler]
    end
    
    subgraph "Moonraker Extensions"
        MR[Moonraker Core]
        GPIO[GPIO Monitor]
        SENS[Sensor Query]
        FAN[Fan Control]
        PWM[PWM Control]
        WSN[WebSocket Notifier]
    end
    
    subgraph "Klipper Firmware"
        KF[Klipper Host]
        MCU1[MCU 1]
        MCU2[MCU N]
    end
    
    subgraph "Hardware"
        HW[Motors, Sensors, Actuators]
    end
    
    OP -->|HTTP/WebSocket| API
    API --> MT
    MT --> EH
    EH -->|G-code| MR
    MR --> KF
    KF --> MCU1
    KF --> MCU2
    MCU1 --> HW
    MCU2 --> HW
    
    CM -->|Cached State| MT
    SM -->|Safety Checks| MT
    SM -->|Monitoring| MR
    
    WS -->|Real-time Updates| OP
    WSN -->|Notifications| WS
    
    GPIO --> HW
    SENS --> HW
```

### Architecture Layers

#### 1. API Layer

**Responsibility**: Expose REST and WebSocket endpoints for OpenPNP integration

**Components**:
- [`src/api/server.py`](src/api/server.py) - Main API server using aiohttp
- [`src/api/routes/`](src/api/routes/) - Route handlers for all endpoints
- [`src/api/auth.py`](src/api/auth.py) - Authentication and authorization

**Key Features**:
- REST API for command execution
- WebSocket for real-time updates
- API key authentication (optional)
- CORS support
- Request/response logging
- Error handling middleware

#### 2. Middleware Layer

**Responsibility**: Translate OpenPNP commands, manage state, and ensure safety

**Components**:
- [`src/middleware/translator.py`](src/middleware/translator.py) - OpenPNP to Moonraker/G-code translation
- [`src/middleware/cache.py`](src/middleware/cache.py) - State caching with TTL support
- [`src/middleware/safety.py`](src/middleware/safety.py) - Safety mechanisms and monitoring

**Key Features**:
- Command translation strategies (direct API, G-code, hybrid)
- State caching with automatic invalidation
- Safety limits enforcement
- Background monitoring tasks
- Event history tracking

#### 3. G-code Driver Layer

**Responsibility**: Parse, translate, and execute G-code commands

**Components**:
- [`src/gcode_driver/parser.py`](src/gcode_driver/parser.py) - G-code parsing and translation
- [`src/gcode_driver/translator.py`](src/gcode_driver/translator.py) - Command translation to Klipper format
- [`src/gcode_driver/handlers.py`](src/gcode_driver/handlers.py) - Execution handlers and queue management

**Key Features**:
- G-code parsing with regex
- Command validation
- Translation context management
- Command queue with priority support
- Execution history tracking

#### 4. Moonraker Extensions Layer

**Responsibility**: Extend Moonraker API with PnP-specific endpoints

**Components**:
- [`src/moonraker_extensions/gpio_monitor.py`](src/moonraker_extensions/gpio_monitor.py) - GPIO state monitoring
- [`src/moonraker_extensions/fan_control.py`](src/moonraker_extensions/fan_control.py) - Fan port control
- [`src/moonraker_extensions/pwm_control.py`](src/moonraker_extensions/pwm_control.py) - PWM output control
- [`src/moonraker_extensions/sensor_query.py`](src/moonraker_extensions/sensor_query.py) - Sensor data queries
- [`src/moonraker_extensions/websocket_notifier.py`](src/moonraker_extensions/websocket_notifier.py) - WebSocket notification support

**Key Features**:
- REST endpoints for hardware control
- Real-time state monitoring
- Sensor data collection
- Hardware abstraction

---

## Component Architecture

### API Server

The API server ([`src/api/server.py`](src/api/server.py)) is built on aiohttp and provides:

#### Initialization

```python
APIServer(
    host='localhost',
    port=7125,
    moonraker_host='localhost',
    moonraker_port=7125,
    moonraker_api_key=None,
    api_key_enabled=False,
    api_key=None,
    enable_cors=True
)
```

#### Middleware Stack

1. **CORS Middleware** - Handles cross-origin requests
2. **Authentication Middleware** - Validates API keys
3. **Error Middleware** - Catches and formats errors
4. **Logging Middleware** - Logs requests and responses

#### Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Stopped
    Stopped --> Starting: start()
    Starting --> Running: Components initialized
    Running --> Stopping: stop()
    Stopping --> Stopped: Cleanup complete
```

### OpenPNP Translator

The translator ([`src/middleware/translator.py`](src/middleware/translator.py)) implements three translation strategies:

#### Translation Strategies

1. **Direct API** - Use Moonraker extension endpoints directly
   - Used for: GPIO read, sensor read, fan control, PWM control
   - Benefits: Lower latency, direct hardware access

2. **G-code** - Translate to G-code and execute via Moonraker
   - Used for: Motion commands, pick/place, actuators, vacuum
   - Benefits: Leverages Klipper's motion planning

3. **Hybrid** - Combine API and G-code approaches
   - Used for: Status queries, position queries
   - Benefits: Comprehensive state aggregation

#### Command Flow

```mermaid
sequenceDiagram
    participant API as API Server
    participant MT as Translator
    participant GC as G-code Driver
    participant MR as Moonraker
    participant KF as Klipper
    
    API->>MT: translate_and_execute(command)
    MT->>MT: Determine strategy
    alt Direct API
        MT->>MR: GET /api/gpio_monitor/inputs
        MR-->>MT: GPIO states
    else G-code
        MT->>GC: translate_to_gcode(command)
        GC-->>MT: G-code string
        MT->>MR: POST /api/printer/gcode/script
        MR->>KF: Execute G-code
        KF-->>MR: Result
        MR-->>MT: Execution result
    else Hybrid
        MT->>MR: GET /api/printer/query
        MT->>GC: get_context()
        GC-->>MT: Internal state
    MT-->>API: OpenPNPResponse
```

### State Cache Manager

The cache manager ([`src/middleware/cache.py`](src/middleware/cache.py)) provides:

#### Cache Categories

| Category | TTL (default) | Purpose |
|----------|---------------|---------|
| GPIO | 1.0s | GPIO pin states |
| Sensor | 0.5s | Sensor readings |
| Position | 0.1s | Toolhead position |
| Fan | 1.0s | Fan states |
| PWM | 1.0s | PWM output values |
| Printer State | 2.0s | Printer status |
| Actuator | 1.0s | Actuator states |

#### Cache Operations

```python
# Get cached value (fetches if expired)
value = await cache_manager.get('gpio:PB5', category=CacheCategory.GPIO)

# Set cached value with TTL
await cache_manager.set('gpio:PB5', 1, ttl=1.0, category=CacheCategory.GPIO)

# Invalidate specific entry
await cache_manager.invalidate('gpio:PB5')

# Invalidate by pattern
await cache_manager.invalidate_pattern('gpio:*')

# Invalidate by category
await cache_manager.invalidate_category(CacheCategory.SENSOR)
```

#### WebSocket Integration

The cache manager connects to Moonraker's WebSocket to receive real-time updates:

```mermaid
sequenceDiagram
    participant CM as Cache Manager
    participant WS as WebSocket
    participant MR as Moonraker
    
    CM->>WS: Connect
    WS->>MR: Subscribe to status updates
    MR-->>WS: Subscription confirmed
    loop Real-time updates
        MR-->>WS: notify_status_update
        WS-->>CM: Handle update
        CM->>CM: Invalidate affected cache
    end
```

### Safety Manager

The safety manager ([`src/middleware/safety.py`](src/middleware/safety.py)) implements:

#### Safety Levels

1. **Normal** - Routine operations
2. **Caution** - Minor issues requiring attention
3. **Warning** - Potential problems detected
4. **Critical** - Serious issues requiring immediate action
5. **Emergency** - System in emergency state

#### Safety Limits

Configurable limits for:

- **Temperature**: Extruder (250°C), Bed (120°C), Chamber (60°C)
- **Position**: X/Y (0-300mm), Z (0-400mm)
- **Velocity**: Max 500mm/s, Max acceleration 3000mm/s²
- **PWM**: 0.0-1.0 range
- **Fan**: 0.0-1.0 speed range
- **Feedrate**: 1-30000 mm/min

#### Monitoring Tasks

```python
# Temperature monitoring (1s interval)
async def temperature_monitor_loop():
    while running:
        await check_temperature_limits()
        await sleep(1.0)

# Position monitoring (0.5s interval)
async def position_monitor_loop():
    while running:
        await check_position_limits()
        await sleep(0.5)

# State monitoring (2s interval)
async def state_monitor_loop():
    while running:
        await check_emergency_stop_state()
        await sleep(2.0)
```

#### Emergency Stop

```mermaid
sequenceDiagram
    participant API as API Server
    participant SM as Safety Manager
    participant MR as Moonraker
    participant KF as Klipper
    
    API->>SM: emergency_stop(reason)
    SM->>SM: Mark emergency active
    SM->>MR: POST M112
    MR->>KF: Emergency stop command
    KF-->>MR: Stop confirmed
    MR-->>SM: Success
    SM->>SM: Invalidate cache
    SM-->>API: SafetyEvent
    SM->>API: Notify callbacks
```

### G-code Driver

The G-code driver ([`src/gcode_driver/parser.py`](src/gcode_driver/parser.py)) provides:

#### G-code Parsing

Regex-based parsing of G-code commands:

```python
GCODE_PATTERN = re.compile(
    r'^\s*'                           # Leading whitespace
    r'(?:(?P<ln>N\d+)\s+)?'          # Line number (optional)
    r'(?P<cmd>[GM]\d+|[A-Z_]+)'      # Command
    r'(?P<params>(?:\s*[A-Z][-+]?\d*\.?\d*(?:e[+-]?\d+)?)*)'  # Parameters
    r'(?:\s*;\s*(?P<comment>.*))?'     # Comment (optional)
    r'\s*$',                            # Trailing whitespace
    re.IGNORECASE
)
```

#### Command Types

Supported G-code commands:

- **Motion**: G0 (rapid), G1 (linear), G2/G3 (arcs), G4 (dwell)
- **Coordinate**: G17/G18/G19 (plane), G20/G21 (units), G28 (home), G90/G91 (positioning), G92 (set position)
- **Spindle/Fan**: M3/M4 (spindle), M5 (spindle off), M106 (fan on), M107 (fan off)
- **Misc**: M0/M1 (stop), M17/M18/M84 (motors), M104/M109 (extruder), M140/M190 (bed)
- **Klipper-specific**: SET_FAN_SPEED, SET_PIN, SET_HEATER_TEMPERATURE, QUERY_ENDSTOPS, STEPPER_ENABLE/DISABLE

#### Translation Context

Maintains state during translation:

```python
context = {
    'positioning_mode': 'absolute',  # 'absolute' or 'relative'
    'units': 'mm',                # 'mm' or 'inches'
    'feedrate': 1500,              # Default feedrate (mm/min)
    'current_position': {
        'x': 0.0,
        'y': 0.0,
        'z': 0.0,
        'e': 0.0
    }
}
```

---

## Integration Boundaries

### OpenPNP Integration

**Interface**: REST API + WebSocket

**Base URL**: `http://localhost:7125/api/v1`

**Authentication**: Optional API key via `X-API-Key` header

**Rate Limits**:
- Motion commands: 100 requests/second
- GPIO/Sensor reads: 200 requests/second
- Batch operations: 10 requests/second

### Moonraker Integration

**Interface**: HTTP REST API + WebSocket

**Base URL**: `http://localhost:7125`

**Authentication**: Optional API key via `X-Api-Key` header

**Extensions Used**:
- `/api/gpio_monitor/*` - GPIO monitoring
- `/api/sensor_query/*` - Sensor queries
- `/api/fan_control/*` - Fan control
- `/api/pwm_control/*` - PWM control
- `/websocket` - Real-time notifications

### Klipper Integration

**Interface**: Moonraker (indirect)

**G-code Commands**:
- Motion: G0, G1, G28
- I/O: M106, M107, SET_PIN
- Control: M112 (emergency stop)

**Status Queries**:
- Toolhead position
- Output pin states
- Fan states
- Temperature sensors

---

## Data Flows

### Command Execution Flow

```mermaid
sequenceDiagram
    participant OP as OpenPNP
    participant API as API Server
    participant MT as Translator
    participant CM as Cache Manager
    participant SM as Safety Manager
    participant MR as Moonraker
    participant KF as Klipper
    
    OP->>API: POST /motion/move
    API->>SM: validate_move_command()
    SM-->>API: (valid, errors)
    alt Valid
        API->>MT: translate_and_execute()
        MT->>CM: get_cached_state()
        CM-->>MT: cached position
        MT->>MT: convert_to_gcode()
        MT->>MR: POST /api/printer/gcode/script
        MR->>KF: Send G-code
        KF-->>MR: Execution result
        MR-->>MT: Response
        MT->>CM: update_cache()
        MT-->>API: OpenPNPResponse
        API-->>OP: 200 OK + response
    else Invalid
        API-->>OP: 400 Bad Request + errors
    end
```

### Pick and Place Flow

```mermaid
sequenceDiagram
    participant OP as OpenPNP
    participant API as API Server
    participant MT as Translator
    participant MR as Moonraker
    participant KF as Klipper
    participant HW as Hardware
    
    OP->>API: POST /pnp/pick_and_place
    API->>MT: translate_and_execute(pick_and_place)
    
    Note over MT: Generate G-code sequence
    MT->>MT: G0 Z{safe_height}
    MT->>MT: G0 X{x} Y{y}
    MT->>MT: G0 Z{pick_height}
    MT->>MT: M106 S{vacuum_power}
    MT->>MT: G0 Z{safe_height}
    MT->>MT: G0 X{place_x} Y{place_y}
    MT->>MT: G0 Z{place_height}
    MT->>MT: M107
    MT->>MT: G0 Z{safe_height}
    
    MT->>MR: POST G-code script
    MR->>KF: Execute sequence
    KF->>HW: Move to safe height
    KF->>HW: Move to pick position
    KF->>HW: Lower to pick height
    KF->>HW: Enable vacuum
    KF->>HW: Raise to safe height
    KF->>HW: Move to place position
    KF->>HW: Lower to place height
    KF->>HW: Disable vacuum
    KF->>HW: Raise to safe height
    
    KF-->>MR: Complete
    MR-->>MT: Success
    MT-->>API: OpenPNPResponse
    API-->>OP: 200 OK
```

### Real-time Status Updates

```mermaid
sequenceDiagram
    participant OP as OpenPNP
    participant WS as WebSocket Server
    participant CM as Cache Manager
    participant MR as Moonraker
    
    OP->>WS: Connect WebSocket
    WS->>OP: Connected
    
    OP->>WS: Subscribe to events
    Note over WS,OP: Subscribe to: position, sensors, gpio, status
    
    WS->>MR: Subscribe to printer.objects
    MR-->>WS: Subscription confirmed
    
    loop Status changes
        HW->>MR: Hardware state change
        MR->>WS: notify_status_update
        WS->>CM: Invalidate cache
        WS->>OP: WebSocket notification
    end
```

### Emergency Stop Flow

```mermaid
sequenceDiagram
    participant OP as OpenPNP
    participant API as API Server
    participant SM as Safety Manager
    participant CM as Cache Manager
    participant MR as Moonraker
    participant KF as Klipper
    participant HW as Hardware
    
    OP->>API: POST /system/emergency_stop
    API->>SM: emergency_stop(reason)
    
    SM->>SM: Set emergency flag
    SM->>MR: POST M112
    MR->>KF: Emergency stop
    KF->>HW: Stop all motion
    KF->>HW: Disable motors
    KF-->>MR: Stopped
    MR-->>SM: Success
    
    SM->>CM: Invalidate all cache
    SM->>SM: Log safety event
    SM->>OP: Notify callbacks
    
    SM-->>API: SafetyEvent
    API-->>OP: 200 OK
```

---

## Design Decisions

### 1. Async/Await Architecture

**Decision**: Use Python asyncio throughout the system

**Rationale**:
- Enables concurrent operations without threading complexity
- Efficient I/O handling for network operations
- Natural fit for aiohttp web framework
- Better resource utilization on single-core systems

**Trade-offs**:
- Requires async/await syntax throughout
- Debugging can be more complex
- Some libraries don't support async

### 2. Three-Tier Translation Strategy

**Decision**: Implement Direct API, G-code, and Hybrid translation strategies

**Rationale**:
- **Direct API**: Lowest latency for simple read operations
- **G-code**: Leverages Klipper's motion planning for complex operations
- **Hybrid**: Best of both worlds for status queries

**Trade-offs**:
- Increased complexity in translator
- Requires knowledge of optimal strategy for each command
- Potential inconsistency if strategies diverge

### 3. State Caching with TTL

**Decision**: Implement TTL-based caching with automatic invalidation

**Rationale**:
- Reduces load on Moonraker/Klipper
- Improves response times for frequent queries
- Automatic invalidation prevents stale data
- WebSocket integration ensures cache freshness

**Trade-offs**:
- Cache complexity and memory usage
- Potential for stale data during network issues
- Requires careful TTL tuning

### 4. Safety-First Design

**Decision**: Implement comprehensive safety mechanisms

**Rationale**:
- Protects hardware from damage
- Prevents unsafe operations
- Provides audit trail via event history
- Enables graceful error recovery

**Trade-offs**:
- Additional code complexity
- Performance overhead from safety checks
- Requires configuration tuning

### 5. REST + WebSocket APIs

**Decision**: Provide both REST and WebSocket interfaces

**Rationale**:
- REST for simple request/response operations
- WebSocket for real-time updates
- Industry-standard patterns
- Flexibility for different client needs

**Trade-offs**:
- Two different client implementations needed
- WebSocket connection management complexity
- Potential for inconsistent state across protocols

### 6. Modular Component Design

**Decision**: Separate components with clear interfaces

**Rationale**:
- Easy to test individual components
- Can replace components without affecting others
- Clear separation of concerns
- Facilitates future enhancements

**Trade-offs**:
- More files and packages
- Indirection can make debugging harder
- Interface design overhead

### 7. Configuration-Driven Behavior

**Decision**: Extensive configuration options

**Rationale**:
- Adaptable to different hardware setups
- No code changes needed for customization
- Easy to tune performance
- Supports deployment variations

**Trade-offs**:
- Configuration complexity
- More code paths to test
- Potential for misconfiguration

---

## Configuration Options

### API Server Configuration

```ini
[api]
# Server binding
host: localhost
port: 7125

# Moonraker connection
moonraker_host: localhost
moonraker_port: 7125
moonraker_api_key: 

# Authentication
api_key_enabled: false
api_key: 

# CORS
enable_cors: true
```

### Cache Configuration

```ini
[cache]
# Cache settings
default_ttl: 1.0
max_cache_size: 10000
cleanup_interval: 10.0
enable_auto_refresh: true

# Category-specific TTLs (optional)
gpio_ttl: 1.0
sensor_ttl: 0.5
position_ttl: 0.1
fan_ttl: 1.0
pwm_ttl: 1.0
printer_state_ttl: 2.0
```

### Safety Configuration

```ini
[safety]
# Temperature limits (Celsius)
max_extruder_temp: 250.0
max_bed_temp: 120.0
max_chamber_temp: 60.0
min_temp_delta: 5.0

# Position limits (mm)
max_x_position: 300.0
max_y_position: 300.0
max_z_position: 400.0
min_x_position: 0.0
min_y_position: 0.0
min_z_position: 0.0

# Velocity limits (mm/s)
max_velocity: 500.0
max_acceleration: 3000.0

# PWM limits (0.0-1.0)
max_pwm_value: 1.0
min_pwm_value: 0.0

# Fan limits (0.0-1.0)
max_fan_speed: 1.0
min_fan_speed: 0.0

# Feedrate limits (mm/min)
max_feedrate: 30000.0
min_feedrate: 1.0

# Emergency stop
emergency_stop_timeout: 5.0

# Monitoring intervals (seconds)
temperature_check_interval: 1.0
position_check_interval: 0.5
state_check_interval: 2.0
```

### G-code Driver Configuration

```ini
[gcode_driver]
# Command mappings (optional)
command_mappings:
  OPENPNP_VACUUM_ON: ['M106 S255']
  OPENPNP_VACUUM_OFF: ['M107']
  OPENPNP_ACTUATE_ON: ['SET_PIN PIN={pin} VALUE=1']
  OPENPNP_ACTUATE_OFF: ['SET_PIN PIN={pin} VALUE=0']

# Queue settings
max_queue_size: 1000
max_history_entries: 1000
default_timeout: 30.0
```

### Environment Variables

```bash
# API server
KLIPPERPLACE_HOST=localhost
KLIPPERPLACE_PORT=7125

# Moonraker connection
MOONRAKER_HOST=localhost
MOONRAKER_PORT=7125
MOONRAKER_API_KEY=

# Authentication
API_KEY_ENABLED=false
API_KEY=

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

---

## State Management

### State Categories

#### 1. Connection State

Tracks connection status to Moonraker and Klipper:

```python
connection_state = {
    'moonraker_connected': bool,
    'klippy_connected': bool,
    'websocket_connected': bool,
    'last_heartbeat': float
}
```

#### 2. Position State

Tracks toolhead position and motion state:

```python
position_state = {
    'current_position': {'x': float, 'y': float, 'z': float},
    'positioning_mode': 'absolute' | 'relative',
    'units': 'mm' | 'inches',
    'feedrate': float,
    'homed_axes': ['x', 'y', 'z']
}
```

#### 3. GPIO State

Tracks GPIO pin states:

```python
gpio_state = {
    'inputs': {
        'PB5': 0 | 1,
        'PB6': 0 | 1,
        # ...
    },
    'outputs': {
        'PA0': 0 | 1,
        'PA1': 0 | 1,
        # ...
    }
}
```

#### 4. Sensor State

Tracks sensor readings:

```python
sensor_state = {
    'pressure_sensors': {
        'pressure_sensor_1': {
            'value': float,
            'unit': 'kPa',
            'last_updated': float
        },
        # ...
    },
    'vacuum_sensors': {
        'vacuum_sensor_1': {
            'value': float,
            'unit': 'bar',
            'last_updated': float
        },
        # ...
    },
    'temperature_sensors': {
        # ...
    }
}
```

#### 5. Actuator State

Tracks actuator states:

```python
actuator_state = {
    'vacuum_enabled': bool,
    'vacuum_power': int,  # 0-255
    'fan_speed': float,  # 0.0-1.0
    'fan_states': {
        'fan': {
            'speed': float,
            'power': float
        }
    },
    'pwm_outputs': {
        'PA2': float,  # 0.0-1.0
        # ...
    }
}
```

### State Synchronization

**Single Source of Truth**: Klipper firmware

**Synchronization Strategy**: Eventual consistency

**Update Mechanisms**:
1. **Direct Updates**: When commands execute successfully
2. **WebSocket Updates**: When Moonraker publishes state changes
3. **Periodic Refresh**: Cache TTL expiration
4. **Manual Refresh**: Explicit cache invalidation

**Conflict Resolution**: Last-write-wins with timestamp ordering

### State Persistence

**Current Implementation**: In-memory state only

**Future Enhancements**:
- State persistence to disk
- State recovery after restart
- State backup/restore
- State versioning for rollback

---

## Error Handling

### Error Categories

#### 1. Validation Errors

**Source**: Input validation before execution

**Examples**:
- Invalid parameter values
- Missing required parameters
- Out-of-bounds values

**Handling**: Return 400 Bad Request with error details

#### 2. Execution Errors

**Source**: Command execution failures

**Examples**:
- Moonraker API errors
- Klipper communication failures
- Hardware faults

**Handling**: Return 500 Internal Server Error with error details

#### 3. Safety Errors

**Source**: Safety limit violations

**Examples**:
- Position out of bounds
- Temperature exceeded
- Emergency stop triggered

**Handling**: Log safety event, return error, potentially trigger emergency stop

#### 4. Timeout Errors

**Source**: Command execution timeout

**Examples**:
- No response from Moonraker
- Klipper not responding
- Hardware hang

**Handling**: Cancel operation, return 504 Gateway Timeout

### Error Response Format

```json
{
  "status": "error",
  "command": "move",
  "command_id": "550e8400-e29b-41d4-a716-4466554400000",
  "error_code": "POSITION_OUT_OF_BOUNDS",
  "error_message": "X position 350.0 mm exceeds maximum of 300.0 mm",
  "details": {
    "axis": "x",
    "position": 350.0,
    "max_limit": 300.0
  },
  "warnings": [],
  "timestamp": 1640000000.000
}
```

### Error Recovery Strategies

#### 1. Retry with Exponential Backoff

**Applicable**: Network errors, temporary failures

**Strategy**:
- Initial retry: 1 second
- Subsequent retries: 2s, 4s, 8s, 16s
- Max retries: 5
- Jitter: Add random delay to prevent thundering herd

#### 2. Circuit Breaker Pattern

**Applicable**: Repeated failures to same endpoint

**States**:
- **Closed**: Normal operation
- **Open**: Reject requests after failure threshold
- **Half-Open**: Allow test requests after timeout

**Configuration**:
- Failure threshold: 5 consecutive failures
- Timeout: 60 seconds before half-open
- Success threshold: 3 consecutive successes to close

#### 3. Fallback to Cached Data

**Applicable**: Sensor reads, GPIO reads

**Strategy**:
- Return cached data if available
- Flag data as stale in response
- Continue background refresh

#### 4. Graceful Degradation

**Applicable**: Partial system failures

**Strategy**:
- Disable non-critical features
- Return limited functionality
- Log degradation events

### Error Logging

**Levels**:
- **DEBUG**: Detailed diagnostic information
- **INFO**: Normal operation events
- **WARNING**: Unexpected but recoverable events
- **ERROR**: Error conditions
- **CRITICAL**: System failure events

**Format**:
```json
{
  "timestamp": "2024-01-13T19:00:00Z",
  "level": "ERROR",
  "component": "api_server",
  "message": "Request failed",
  "request_id": "abc123",
  "details": {
    "error": "Connection timeout",
    "endpoint": "/motion/move"
  }
}
```

---

## Security Considerations

### Authentication

**Current Implementation**: Optional API key authentication

**Configuration**:
```ini
[api]
api_key_enabled: true
api_key: your-secure-api-key-here
```

**Usage**:
```bash
curl -H "X-API-Key: your-secure-api-key-here" \
     http://localhost:7125/api/v1/motion/move
```

**Future Enhancements**:
- JWT token authentication
- OAuth 2.0 integration
- Role-based access control
- API key rotation

### Input Validation

**Validation Layers**:
1. **Type Validation**: Ensure correct data types
2. **Range Validation**: Check parameter bounds
3. **Format Validation**: Verify data format
4. **Business Logic Validation**: Enforce safety rules

**Examples**:
```python
# Position validation
if x < 0 or x > 300:
    raise ValueError("X position out of bounds")

# PWM validation
if pwm < 0.0 or pwm > 1.0:
    raise ValueError("PWM value out of range")

# Pin name validation
if not re.match(r'^[PA-Z]\d+$', pin_name):
    raise ValueError("Invalid pin name format")
```

### Rate Limiting

**Implementation**: Token bucket algorithm

**Limits**:
- Motion commands: 100 requests/second
- GPIO/Sensor reads: 200 requests/second
- Batch operations: 10 requests/second
- WebSocket connections: 100 concurrent

**Response Headers**:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640000000
X-RateLimit-Retry-After: 60
```

### Network Security

**Recommendations**:
1. **Bind to localhost only** for local deployments
2. **Use firewall rules** to restrict access
3. **Enable HTTPS** for external access
4. **Implement IP whitelisting** for remote access
5. **Monitor for suspicious activity**

### Data Protection

**Sensitive Data**:
- API keys
- Configuration files
- Log files with credentials

**Protection Measures**:
- Never log API keys
- Use environment variables for secrets
- Restrict file permissions
- Encrypt sensitive data at rest

---

## Performance Characteristics

### Latency

| Operation | Typical Latency | P95 Latency | P99 Latency |
|-----------|------------------|---------------|---------------|
| Move command | 50-100ms | 150ms | 250ms |
| GPIO read | 10-30ms | 50ms | 100ms |
| Sensor read | 20-50ms | 80ms | 150ms |
| Pick and place | 200-500ms | 800ms | 1.5s |
| Status query | 30-80ms | 120ms | 200ms |

### Throughput

| Operation | Max Throughput | Sustained Throughput |
|-----------|----------------|---------------------|
| Motion commands | 100/sec | 50/sec |
| GPIO reads | 200/sec | 150/sec |
| Sensor reads | 200/sec | 150/sec |
| Batch operations | 10/sec | 5/sec |

### Resource Usage

**Memory**:
- Base usage: ~100MB
- Per connection: ~1MB
- Cache: ~10MB (configurable)

**CPU**:
- Idle: <5%
- Normal load: 10-20%
- Peak load: 30-50%

**Network**:
- REST API: ~1KB per request
- WebSocket: ~100 bytes per update
- Moonraker API: ~500 bytes per request

### Optimization Strategies

#### 1. Caching

**Benefits**:
- Reduces Moonraker API calls by 60-80%
- Improves response times by 70-90%
- Lowers CPU usage

**Trade-offs**:
- Memory usage increases
- Potential for stale data
- Cache invalidation complexity

#### 2. Connection Pooling

**Benefits**:
- Reduces connection overhead
- Improves throughput
- Better resource utilization

**Implementation**: aiohttp automatic connection pooling

#### 3. Async Operations

**Benefits**:
- Handles concurrent requests efficiently
- No thread overhead
- Better I/O utilization

**Trade-offs**:
- Requires async/await syntax
- Debugging complexity

#### 4. WebSocket Updates

**Benefits**:
- Real-time updates without polling
- Reduced network traffic
- Lower latency

**Trade-offs**:
- Connection management complexity
- Requires fallback to polling

### Scaling Considerations

**Vertical Scaling**:
- More CPU cores: Better concurrency
- More RAM: Larger cache, more connections
- Faster network: Lower latency

**Horizontal Scaling**:
- Multiple API instances: Load balancing
- Separate Moonraker instances: Reduced load
- Distributed caching: Shared state

**Bottlenecks**:
1. Moonraker API capacity
2. Klipper MCU processing
3. Network bandwidth
4. Single-threaded Python GIL

---

## Appendix

### Component Reference

| Component | File | Purpose |
|-----------|-------|---------|
| API Server | [`src/api/server.py`](src/api/server.py) | REST API implementation |
| Translator | [`src/middleware/translator.py`](src/middleware/translator.py) | OpenPNP to Moonraker translation |
| Cache Manager | [`src/middleware/cache.py`](src/middleware/cache.py) | State caching with TTL |
| Safety Manager | [`src/middleware/safety.py`](src/middleware/safety.py) | Safety mechanisms |
| G-code Parser | [`src/gcode_driver/parser.py`](src/gcode_driver/parser.py) | G-code parsing |
| G-code Translator | [`src/gcode_driver/translator.py`](src/gcode_driver/translator.py) | G-code translation |
| Execution Handler | [`src/gcode_driver/handlers.py`](src/gcode_driver/handlers.py) | Command execution |
| GPIO Monitor | [`src/moonraker_extensions/gpio_monitor.py`](src/moonraker_extensions/gpio_monitor.py) | GPIO monitoring |
| Fan Control | [`src/moonraker_extensions/fan_control.py`](src/moonraker_extensions/fan_control.py) | Fan control |
| PWM Control | [`src/moonraker_extensions/pwm_control.py`](src/moonraker_extensions/pwm_control.py) | PWM control |
| Sensor Query | [`src/moonraker_extensions/sensor_query.py`](src/moonraker_extensions/sensor_query.py) | Sensor queries |
| WebSocket Notifier | [`src/moonraker_extensions/websocket_notifier.py`](src/moonraker_extensions/websocket_notifier.py) | WebSocket notifications |

### API Endpoint Reference

See [`src/api/schema.md`](src/api/schema.md) for complete API documentation.

### Testing Documentation

See [`docs/TESTING.md`](docs/TESTING.md) for testing strategies and procedures.

### Architecture Design Document

See [`plans/architecture-design.md`](plans/architecture-design.md) for the original architecture design.

---

**Document Version**: 1.0.0  
**Last Updated**: 2024-01-13  
**Maintained By**: KlipperPlace Development Team
