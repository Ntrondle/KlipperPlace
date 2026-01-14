# Configuration Guide

This guide provides comprehensive configuration instructions for KlipperPlace, covering all components including the API server, cache, safety mechanisms, G-code driver, and Moonraker integration.

## Table of Contents

- [Quick Start](#quick-start)
- [API Server Configuration](#api-server-configuration)
- [Cache Configuration](#cache-configuration)
- [Safety Configuration](#safety-configuration)
- [G-code Driver Configuration](#g-code-driver-configuration)
- [Moonraker Integration Configuration](#moonraker-integration-configuration)
- [Authentication Configuration](#authentication-configuration)
- [Environment Variables](#environment-variables)
- [Example Configuration Files](#example-configuration-files)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

For a basic setup, create a minimal configuration file:

```python
# config/klipperplace_config.py
config = {
    # API Server
    'host': '0.0.0.0',
    'port': 7125,
    
    # Moonraker Connection
    'moonraker_host': 'localhost',
    'moonraker_port': 7125,
    
    # Authentication
    'api_key_enabled': True,
    'rate_limit': 100,
    
    # Cache
    'cache_default_ttl': 1.0,
    'cache_max_size': 10000,
    
    # Safety
    'safety_max_extruder_temp': 250.0,
    'safety_max_bed_temp': 120.0,
}
```

Start the server:

```bash
python -m src.api.server
```

---

## API Server Configuration

The API server is the main entry point for KlipperPlace, handling all REST API requests.

### Basic Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `host` | string | `'localhost'` | API server host address |
| `port` | integer | `7125` | API server port |
| `enable_cors` | boolean | `True` | Enable CORS support |

### Moonraker Connection

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `moonraker_host` | string | `'localhost'` | Moonraker host address |
| `moonraker_port` | integer | `7125` | Moonraker port |
| `moonraker_api_key` | string | `None` | Optional Moonraker API key |

### Example Configuration

```python
from src.api.server import APIServer

server = APIServer(
    host='0.0.0.0',
    port=7125,
    moonraker_host='localhost',
    moonraker_port=7125,
    moonraker_api_key='your-moonraker-api-key',
    enable_cors=True
)

await server.start()
```

### Configuration File

Create `config/server_config.json`:

```json
{
    "host": "0.0.0.0",
    "port": 7125,
    "moonraker_host": "localhost",
    "moonraker_port": 7125,
    "moonraker_api_key": null,
    "enable_cors": true
}
```

Load configuration:

```python
import json
from src.api.server import run_server

with open('config/server_config.json', 'r') as f:
    config = json.load(f)

await run_server(config)
```

---

## Cache Configuration

The cache manager improves performance by storing hardware state with automatic expiration.

### Cache Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `default_ttl` | float | `1.0` | Default time-to-live in seconds |
| `max_cache_size` | integer | `10000` | Maximum number of cache entries |
| `cleanup_interval` | float | `10.0` | Cleanup interval in seconds |
| `enable_auto_refresh` | boolean | `True` | Enable automatic cache refresh |

### Category-Specific TTL Values

Different cache categories have different default TTL values:

| Category | Default TTL | Description |
|----------|-------------|-------------|
| `GPIO` | 1.0s | GPIO pin states |
| `SENSOR` | 0.5s | Sensor readings |
| `POSITION` | 0.1s | Toolhead position |
| `FAN` | 1.0s | Fan speeds |
| `PWM` | 1.0s | PWM output values |
| `PRINTER_STATE` | 2.0s | Printer state information |
| `ACTUATOR` | 1.0s | Actuator states |
| `CUSTOM` | 5.0s | Custom cached data |

### Example Configuration

```python
from src.middleware.cache import StateCacheManager, CacheCategory

cache_manager = StateCacheManager(
    moonraker_host='localhost',
    moonraker_port=7125,
    default_ttl=1.0,
    max_cache_size=10000,
    cleanup_interval=10.0,
    enable_auto_refresh=True
)

# Override TTL for specific category
await cache_manager.set('gpio:pin1', value, ttl=0.5, category=CacheCategory.GPIO)
```

### Cache Performance Tuning

For high-performance systems:

```python
cache_manager = StateCacheManager(
    default_ttl=0.5,           # Shorter TTL for fresher data
    max_cache_size=50000,       # Larger cache for more data
    cleanup_interval=5.0,       # More frequent cleanup
    enable_auto_refresh=True
)
```

For memory-constrained systems:

```python
cache_manager = StateCacheManager(
    default_ttl=2.0,           # Longer TTL to reduce fetches
    max_cache_size=1000,        # Smaller cache
    cleanup_interval=30.0,       # Less frequent cleanup
    enable_auto_refresh=False      # Disable auto-refresh
)
```

---

## Safety Configuration

The safety manager enforces hardware protection limits and monitors system state.

### Temperature Limits

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_extruder_temp` | float | `250.0` | Maximum extruder temperature (°C) |
| `max_bed_temp` | float | `120.0` | Maximum bed temperature (°C) |
| `max_chamber_temp` | float | `60.0` | Maximum chamber temperature (°C) |
| `min_temp_delta` | float | `5.0` | Minimum delta between target and current (°C) |

### Position Limits

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_x_position` | float | `300.0` | Maximum X position (mm) |
| `max_y_position` | float | `300.0` | Maximum Y position (mm) |
| `max_z_position` | float | `400.0` | Maximum Z position (mm) |
| `min_x_position` | float | `0.0` | Minimum X position (mm) |
| `min_y_position` | float | `0.0` | Minimum Y position (mm) |
| `min_z_position` | float | `0.0` | Minimum Z position (mm) |

### Velocity and Feedrate Limits

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_velocity` | float | `500.0` | Maximum velocity (mm/s) |
| `max_acceleration` | float | `3000.0` | Maximum acceleration (mm/s²) |
| `max_feedrate` | float | `30000.0` | Maximum feedrate (mm/min) |
| `min_feedrate` | float | `1.0` | Minimum feedrate (mm/min) |

### PWM and Fan Limits

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_pwm_value` | float | `1.0` | Maximum PWM value (0.0-1.0) |
| `min_pwm_value` | float | `0.0` | Minimum PWM value (0.0-1.0) |
| `max_fan_speed` | float | `1.0` | Maximum fan speed (0.0-1.0) |
| `min_fan_speed` | float | `0.0` | Minimum fan speed (0.0-1.0) |

### Monitoring Intervals

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `temperature_check_interval` | float | `1.0` | Temperature check interval (s) |
| `position_check_interval` | float | `0.5` | Position check interval (s) |
| `state_check_interval` | float | `2.0` | State check interval (s) |
| `emergency_stop_timeout` | float | `5.0` | Emergency stop timeout (s) |

### Example Configuration

```python
from src.middleware.safety import SafetyManager, SafetyLimits

# Create custom safety limits
safety_limits = SafetyLimits(
    max_extruder_temp=260.0,
    max_bed_temp=130.0,
    max_chamber_temp=70.0,
    max_x_position=350.0,
    max_y_position=350.0,
    max_z_position=500.0,
    max_velocity=600.0,
    max_acceleration=5000.0,
    max_feedrate=40000.0
)

safety_manager = SafetyManager(
    moonraker_host='localhost',
    moonraker_port=7125,
    cache_manager=cache_manager,
    safety_limits=safety_limits
)

await safety_manager.start()
```

### Updating Limits at Runtime

```python
# Update specific limits
safety_manager.update_limits({
    'max_extruder_temp': 280.0,
    'max_feedrate': 50000.0
})
```

### Safety Event Callbacks

```python
def on_safety_event(event):
    print(f"Safety Event: {event.message}")
    if event.level == SafetyLevel.EMERGENCY:
        # Handle emergency
        pass

safety_manager.add_event_callback(on_safety_event)
```

---

## G-code Driver Configuration

The G-code driver translates OpenPNP commands to Klipper-compatible G-code.

### Basic Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `moonraker_host` | string | `'localhost'` | Moonraker host address |
| `moonraker_port` | integer | `7125` | Moonraker port |
| `moonraker_api_key` | string | `None` | Optional Moonraker API key |
| `timeout` | float | `30.0` | Request timeout in seconds |

### Translation Context Defaults

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `feedrate` | float | `1500.0` | Default feedrate (mm/min) |
| `positioning_mode` | string | `'absolute'` | Positioning mode ('absolute' or 'relative') |
| `units` | string | `'mm'` | Units ('mm' or 'inches') |
| `tool_number` | integer | `0` | Default tool number |
| `spindle_speed` | integer | `0` | Default spindle speed (RPM) |

### Command Templates

Customize G-code templates for specific operations:

```python
from src.gcode_driver.translator import CommandTranslator

translator = CommandTranslator(
    moonraker_host='localhost',
    moonraker_port=7125
)

# Add custom template
translator.add_template('custom_pick', '''
    G0 Z{safe_height} F{feedrate}
    G0 X{x} Y{y} F{feedrate}
    G0 Z{pick_height} F{feedrate}
    M106 S{vacuum_power}
    G4 P{dwell_time}
    G0 Z{safe_height} F{feedrate}
''')

# Add custom validator
translator.add_validator('dwell_time', lambda v: v >= 0 and v <= 10)
```

### Example Configuration File

Create `config/gcode_config.json`:

```json
{
    "context_defaults": {
        "feedrate": 2000.0,
        "positioning_mode": "absolute",
        "units": "mm",
        "tool_number": 0,
        "spindle_speed": 0
    },
    "templates": {
        "pick": "G0 Z{safe_height} F{feedrate}\nG0 X{x} Y{y} F{feedrate}\nG0 Z{pick_height} F{feedrate}\nM106 S{vacuum_power}\nG0 Z{safe_height} F{feedrate}",
        "place": "G0 Z{safe_height} F{feedrate}\nG0 X{x} Y{y} F{feedrate}\nG0 Z{place_height} F{feedrate}\nM107\nG0 Z{safe_height} F{feedrate}"
    },
    "validators": {
        "x": "lambda v: isinstance(v, (int, float)) and -1000 <= v <= 1000",
        "y": "lambda v: isinstance(v, (int, float)) and -1000 <= v <= 1000",
        "z": "lambda v: isinstance(v, (int, float)) and -500 <= v <= 500",
        "feedrate": "lambda v: isinstance(v, (int, float)) and v > 0"
    }
}
```

Load configuration:

```python
import json
from src.gcode_driver.translator import CommandTranslator

with open('config/gcode_config.json', 'r') as f:
    config = json.load(f)

translator = CommandTranslator(
    config=config,
    moonraker_host='localhost',
    moonraker_port=7125
)
```

### Using the Translator

```python
# Parse and translate G-code
results = translator.parse_and_translate("""
    OPENPNP_MOVE X=100 Y=100 Z=10 F=2000
    OPENPNP_PICK pick_height=0 vacuum_power=255
    OPENPNP_PLACE X=200 Y=200 place_height=0
""")

for result in results:
    if result.success:
        print(f"Translated: {result.translated_commands}")
    else:
        print(f"Error: {result.error_message}")
```

---

## Moonraker Integration Configuration

KlipperPlace integrates with Moonraker through custom extensions. These must be configured in Moonraker's configuration file.

### GPIO Monitor Configuration

Add to `moonraker.conf`:

```ini
[gpio_monitor]
# Comma-separated list of enabled GPIO pins (empty = all pins)
enabled_pins: 
# Poll interval in milliseconds (10-5000)
poll_interval: 100
```

### Fan Control Configuration

Add to `moonraker.conf`:

```ini
[fan_control]
# Default fan name
default_fan: fan
# Default fan speed (0.0-1.0)
default_speed: 0.5
# Maximum fan speed (0.0-1.0)
max_speed: 1.0
```

### PWM Control Configuration

Add to `moonraker.conf`:

```ini
[pwm_control]
# Default PWM pin name
default_pin: my_pwm_pin
# Default PWM value (0.0-1.0)
default_value: 0.0
# Default ramp duration in seconds (0.1-60.0)
ramp_duration: 1.0
# Default ramp steps (2-100)
ramp_steps: 10
```

### Sensor Query Configuration

Add to `moonraker.conf`:

```ini
[sensor_query]
# Comma-separated list of enabled sensors (empty = all sensors)
enabled_sensors: 
# Include timestamp in responses
include_timestamp: true
# Flatten response structure
flatten_response: false
```

### Supported Sensor Types

The sensor query component supports the following sensor types:

**Temperature Sensors:**
- `temperature_sensor`
- `heater`
- `temperature_fan`
- `bme280`
- `htu21d`
- `lm75`
- `rpi_temperature`
- `temperature_host`

**Force/Load Sensors:**
- `load_cell`
- `load_cell_probe`

**Motion Sensors:**
- `adxl345`
- `angle`
- `motion_report`

**Filament Sensors:**
- `hall_filament_width_sensor`
- `filament_switch_sensor`
- `filament_motion_sensor`

**Other Sensors:**
- `tmc2209`, `tmc2660`, `tmc5160`, `tmc2240`
- `resonance_tester`
- `probe`
- `bed_mesh`
- `endstop`
- `gcode_macro`
- `gcode_button`
- `temperature_mcu`
- `adc_scaled`
- `angle_sensor`

### Example Moonraker Configuration

Complete `moonraker.conf` example:

```ini
[server]
host: 0.0.0.0
port: 7125
enable_debug_logging: False

[database]
database_path: ~/.moonraker_database

[gpio_monitor]
enabled_pins: pin1, pin2, pin3
poll_interval: 50

[fan_control]
default_fan: fan
default_speed: 0.5
max_speed: 1.0

[pwm_control]
default_pin: vacuum_pwm
default_value: 0.0
ramp_duration: 0.5
ramp_steps: 20

[sensor_query]
enabled_sensors: extruder, heater_bed, temperature_sensor_chamber
include_timestamp: true
flatten_response: false
```

---

## Authentication Configuration

KlipperPlace provides comprehensive API key management and authentication.

### Authentication Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key_enabled` | boolean | `True` | Enable API key authentication |
| `api_key` | string | `None` | Default API key (for backward compatibility) |
| `api_key_storage_path` | string | `'config/api_keys.json'` | Path to API key storage file |
| `rate_limit` | integer | `100` | Default rate limit (requests/second) |
| `public_endpoints` | list | `['/api/v1/version', '/health']` | Public endpoints (no auth required) |

### API Key Permissions

API keys can have the following permissions:

| Permission | Description |
|------------|-------------|
| `read` | Read-only access to printer state |
| `write` | Write access to printer controls |
| `admin` | Full administrative access |

### Example Configuration

```python
from src.api.auth import create_auth_manager

auth_config = {
    'api_key_enabled': True,
    'api_key_storage_path': 'config/api_keys.json',
    'rate_limit': 100,
    'public_endpoints': [
        '/api/v1/version',
        '/health',
        '/api/v1/status'
    ]
}

key_manager, auth_middleware, auth_logger = create_auth_manager(auth_config)
```

### Creating API Keys

```python
# Create a new API key
key_id, api_key = key_manager.create_key(
    name='OpenPNP Client',
    permissions=['read', 'write'],
    rate_limit=50,
    description='API key for OpenPNP integration'
)

print(f"Key ID: {key_id}")
print(f"API Key: {api_key}")  # Store this securely!
```

### Managing API Keys

```python
# List all keys
keys = key_manager.list_keys()
for key in keys:
    print(f"{key['key_id']}: {key['name']}")

# Update a key
key_manager.update_key(
    key_id='abc123',
    rate_limit=100,
    is_active=True
)

# Delete a key
key_manager.delete_key(key_id='abc123')
```

### API Key Storage Format

The `api_keys.json` file stores API keys in the following format:

```json
{
    "api_keys": [
        {
            "key_id": "abc123def456",
            "key_hash": "5f4dcc3b5aa765d61d8327deb882cf99",
            "name": "Default Key",
            "permissions": ["read", "write", "admin"],
            "rate_limit": 100,
            "created_at": 1234567890.0,
            "last_used": 1234567895.0,
            "is_active": true,
            "description": "Default API key"
        }
    ]
}
```

### Using API Keys in Requests

Include the API key in the `X-API-Key` header:

```bash
curl -H "X-API-Key: kp_your_api_key_here" \
     http://localhost:7125/api/v1/status
```

---

## Environment Variables

KlipperPlace supports configuration through environment variables.

### Server Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `KLIPPERPLACE_HOST` | API server host | `localhost` |
| `KLIPPERPLACE_PORT` | API server port | `7125` |
| `KLIPPERPLACE_MOONRAKER_HOST` | Moonraker host | `localhost` |
| `KLIPPERPLACE_MOONRAKER_PORT` | Moonraker port | `7125` |
| `KLIPPERPLACE_MOONRAKER_API_KEY` | Moonraker API key | `None` |
| `KLIPPERPLACE_API_KEY_ENABLED` | Enable API key auth | `True` |
| `KLIPPERPLACE_API_KEY` | Default API key | `None` |
| `KLIPPERPLACE_CORS_ENABLED` | Enable CORS | `True` |

### Cache Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `KLIPPERPLACE_CACHE_TTL` | Default cache TTL | `1.0` |
| `KLIPPERPLACE_CACHE_MAX_SIZE` | Maximum cache size | `10000` |
| `KLIPPERPLACE_CACHE_CLEANUP_INTERVAL` | Cleanup interval | `10.0` |

### Safety Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `KLIPPERPLACE_MAX_EXTRUDER_TEMP` | Max extruder temp | `250.0` |
| `KLIPPERPLACE_MAX_BED_TEMP` | Max bed temp | `120.0` |
| `KLIPPERPLACE_MAX_VELOCITY` | Max velocity | `500.0` |
| `KLIPPERPLACE_MAX_ACCELERATION` | Max acceleration | `3000.0` |

### Example Environment File

Create `.env` file:

```bash
# Server
KLIPPERPLACE_HOST=0.0.0.0
KLIPPERPLACE_PORT=7125
KLIPPERPLACE_MOONRAKER_HOST=localhost
KLIPPERPLACE_MOONRAKER_PORT=7125

# Authentication
KLIPPERPLACE_API_KEY_ENABLED=true
KLIPPERPLACE_RATE_LIMIT=100

# Cache
KLIPPERPLACE_CACHE_TTL=1.0
KLIPPERPLACE_CACHE_MAX_SIZE=10000

# Safety
KLIPPERPLACE_MAX_EXTRUDER_TEMP=260.0
KLIPPERPLACE_MAX_BED_TEMP=130.0
```

Load environment variables in Python:

```python
import os
from dotenv import load_dotenv

load_dotenv()

config = {
    'host': os.getenv('KLIPPERPLACE_HOST', 'localhost'),
    'port': int(os.getenv('KLIPPERPLACE_PORT', 7125)),
    'moonraker_host': os.getenv('KLIPPERPLACE_MOONRAKER_HOST', 'localhost'),
    'moonraker_port': int(os.getenv('KLIPPERPLACE_MOONRAKER_PORT', 7125))
}
```

---

## Example Configuration Files

### Complete KlipperPlace Configuration

Create `config/klipperplace.json`:

```json
{
    "host": "0.0.0.0",
    "port": 7125,
    "moonraker_host": "localhost",
    "moonraker_port": 7125,
    "moonraker_api_key": null,
    "enable_cors": true,
    
    "api_key_enabled": true,
    "rate_limit": 100,
    "api_key_storage_path": "config/api_keys.json",
    "public_endpoints": [
        "/api/v1/version",
        "/health",
        "/api/v1/status"
    ],
    
    "cache_default_ttl": 1.0,
    "cache_max_size": 10000,
    "cache_cleanup_interval": 10.0,
    "cache_enable_auto_refresh": true,
    
    "safety_max_extruder_temp": 260.0,
    "safety_max_bed_temp": 130.0,
    "safety_max_chamber_temp": 70.0,
    "safety_max_x_position": 350.0,
    "safety_max_y_position": 350.0,
    "safety_max_z_position": 500.0,
    "safety_min_x_position": 0.0,
    "safety_min_y_position": 0.0,
    "safety_min_z_position": 0.0,
    "safety_max_velocity": 600.0,
    "safety_max_acceleration": 5000.0,
    "safety_max_feedrate": 40000.0,
    "safety_min_feedrate": 1.0,
    "safety_max_pwm_value": 1.0,
    "safety_min_pwm_value": 0.0,
    "safety_max_fan_speed": 1.0,
    "safety_min_fan_speed": 0.0,
    "safety_emergency_stop_timeout": 5.0,
    "safety_temperature_check_interval": 1.0,
    "safety_position_check_interval": 0.5,
    "safety_state_check_interval": 2.0,
    
    "gcode_context_defaults": {
        "feedrate": 2000.0,
        "positioning_mode": "absolute",
        "units": "mm",
        "tool_number": 0,
        "spindle_speed": 0
    }
}
```

### Loading Complete Configuration

```python
import json
from src.api.server import run_server

with open('config/klipperplace.json', 'r') as f:
    config = json.load(f)

await run_server(config)
```

### Production Configuration

For production deployments:

```json
{
    "host": "0.0.0.0",
    "port": 7125,
    "moonraker_host": "localhost",
    "moonraker_port": 7125,
    "moonraker_api_key": "secure-moonraker-key",
    "enable_cors": false,
    
    "api_key_enabled": true,
    "rate_limit": 50,
    "api_key_storage_path": "/var/lib/klipperplace/api_keys.json",
    "public_endpoints": ["/health"],
    
    "cache_default_ttl": 0.5,
    "cache_max_size": 50000,
    "cache_cleanup_interval": 5.0,
    "cache_enable_auto_refresh": true,
    
    "safety_max_extruder_temp": 250.0,
    "safety_max_bed_temp": 120.0,
    "safety_max_velocity": 500.0,
    "safety_max_acceleration": 3000.0,
    "safety_emergency_stop_timeout": 3.0,
    "safety_temperature_check_interval": 0.5,
    "safety_position_check_interval": 0.25
}
```

---

## Troubleshooting

### Common Configuration Issues

#### Issue: API Server Won't Start

**Symptoms:** Server fails to start or exits immediately.

**Possible Causes:**
- Port already in use
- Invalid host address
- Missing dependencies

**Solutions:**
```bash
# Check if port is in use
netstat -tuln | grep 7125

# Use a different port
"port": 7126

# Check host binding
"host": "127.0.0.1"  # Local only
"host": "0.0.0.0"    # All interfaces
```

#### Issue: Moonraker Connection Failed

**Symptoms:** "Connection refused" or "Timeout" errors.

**Possible Causes:**
- Moonraker not running
- Wrong host/port
- Firewall blocking connection
- API key mismatch

**Solutions:**
```bash
# Check Moonraker status
sudo systemctl status moonraker

# Check Moonraker logs
sudo journalctl -u moonraker -f

# Test connection
curl http://localhost:7125/server/info

# Verify API key
curl -H "X-Api-Key: your-key" http://localhost:7125/server/info
```

#### Issue: Cache Performance Problems

**Symptoms:** Slow responses, high memory usage.

**Possible Causes:**
- Cache too large
- TTL too long
- Too many cache misses

**Solutions:**
```python
# Reduce cache size
"cache_max_size": 5000

# Shorten TTL
"cache_default_ttl": 0.5

# Check cache statistics
stats = await cache_manager.get_statistics()
print(f"Hit rate: {stats['hit_rate']}%")
print(f"Miss rate: {stats['miss_rate']}%")
```

#### Issue: Safety Limits Triggering

**Symptoms:** Commands rejected with "bounds violation" errors.

**Possible Causes:**
- Limits too restrictive
- Wrong units (mm vs inches)
- Position not homed

**Solutions:**
```python
# Check current limits
limits = await safety_manager.get_current_limits()
print(json.dumps(limits, indent=2))

# Update limits if needed
safety_manager.update_limits({
    'max_x_position': 400.0,
    'max_feedrate': 50000.0
})

# Check homing status
homed_axes = safety_manager.get_homed_axes()
print(f"Homed axes: {homed_axes}")

# Home axes if needed
# G28 X Y Z
```

#### Issue: G-code Translation Failures

**Symptoms:** "No mapping found" or "Parameter validation failed" errors.

**Possible Causes:**
- Missing command template
- Invalid parameter values
- Wrong command syntax

**Solutions:**
```python
# Check available templates
templates = translator.get_templates()
print(json.dumps(templates, indent=2))

# Add missing template
translator.add_template('my_command', 'G0 X{x} Y{y} F{feedrate}')

# Validate parameters
result = translator.translate_command(command)
if not result.success:
    print(f"Error: {result.error_message}")
```

#### Issue: Authentication Failures

**Symptoms:** 401 Unauthorized responses.

**Possible Causes:**
- Invalid API key
- API key inactive
- Rate limit exceeded
- IP blocked

**Solutions:**
```python
# List API keys
keys = key_manager.list_keys()
for key in keys:
    print(f"{key['key_id']}: {key['is_active']}")

# Reactivate key
key_manager.update_key(key_id, is_active=True)

# Check rate limit
rate_info = key_manager.get_rate_limit_info(api_key)
print(f"Remaining: {rate_info['remaining']}/{rate_info['limit']}")

# Check blocked IPs
blocked_ips = [ip for ip, attempts in auth_logger.failed_attempts.items() 
               if attempts >= 10]
print(f"Blocked IPs: {blocked_ips}")
```

### Debug Mode

Enable debug logging for troubleshooting:

```python
import logging

# Set debug level
logging.basicConfig(level=logging.DEBUG)

# Or set specific module level
logging.getLogger('src.api').setLevel(logging.DEBUG)
logging.getLogger('src.middleware').setLevel(logging.DEBUG)
logging.getLogger('src.gcode_driver').setLevel(logging.DEBUG)
```

### Configuration Validation

Validate your configuration before starting:

```python
import json
from jsonschema import validate, ValidationError

# Define schema
schema = {
    "type": "object",
    "properties": {
        "host": {"type": "string"},
        "port": {"type": "integer", "minimum": 1, "maximum": 65535},
        "moonraker_host": {"type": "string"},
        "moonraker_port": {"type": "integer", "minimum": 1, "maximum": 65535}
    },
    "required": ["host", "port", "moonraker_host", "moonraker_port"]
}

# Load and validate configuration
with open('config/klipperplace.json', 'r') as f:
    config = json.load(f)

try:
    validate(instance=config, schema=schema)
    print("Configuration is valid")
except ValidationError as e:
    print(f"Configuration error: {e.message}")
```

### Getting Help

If you encounter issues not covered here:

1. Check the [Architecture Documentation](ARCHITECTURE.md) for system overview
2. Review the [API Reference](API_REFERENCE.md) for endpoint details
3. Check logs in `/var/log/klipperplace/` or console output
4. Open an issue on GitHub with:
   - Configuration file (with sensitive data removed)
   - Error messages
   - System information (OS, Python version)
   - Steps to reproduce

---

## Additional Resources

- [Architecture Documentation](ARCHITECTURE.md) - System architecture overview
- [API Reference](API_REFERENCE.md) - Complete API documentation
- [Testing Guide](TESTING.md) - Testing procedures and examples
- [Klipper Documentation](https://www.klipper3d.org/) - Klipper firmware docs
- [Moonraker Documentation](https://moonraker.readthedocs.io/) - Moonraker API docs
- [OpenPNP Documentation](https://openpnp.org/) - OpenPNP software docs
