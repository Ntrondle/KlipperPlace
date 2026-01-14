# Hardware Testing Guide

This document provides comprehensive procedures for testing KlipperPlace with real hardware, including Klipper firmware, Moonraker API server, and OpenPNP pick-and-place software integration.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Hardware Test Environment Setup](#hardware-test-environment-setup)
- [Testing REST Endpoints](#testing-rest-endpoints)
- [Testing WebSocket Communication](#testing-websocket-communication)
- [Testing Safety Mechanisms](#testing-safety-mechanisms)
- [Testing OpenPNP Integration](#testing-openpnp-integration)
- [Performance Testing](#performance-testing)
- [Issue Documentation](#issue-documentation)
- [Test Results Reporting](#test-results-reporting)
- [Troubleshooting](#troubleshooting)
- [Safety Guidelines](#safety-guidelines)

---

## Overview

Hardware testing validates that KlipperPlace functions correctly with real physical hardware, ensuring that all software components integrate properly and that the system performs as expected in production environments.

### Testing Objectives

- Verify all 32 REST endpoints work with real hardware
- Validate WebSocket real-time communication
- Test safety mechanisms under real conditions
- Confirm OpenPNP integration functionality
- Measure and verify performance characteristics
- Identify and document any hardware-specific issues

### Testing Scope

**Hardware Components:**
- Klipper motherboard (e.g., BigTreeTech, Fysetc, Creality)
- Stepper motors and drivers
- Endstops and limit switches
- GPIO pins for actuators
- Vacuum pump and sensors
- Fan controls
- Temperature sensors

**Software Components:**
- Klipper firmware
- Moonraker API server
- KlipperPlace middleware
- OpenPNP 2.0 application

---

## Prerequisites

### Hardware Requirements

#### Required Hardware

| Component | Minimum Specification | Recommended |
|-----------|----------------------|-------------|
| Raspberry Pi | Pi 3B+ | Pi 4 or Pi 5 (4GB+ RAM) |
| Motherboard | Klipper-compatible MCU | BigTreeTech SKR, Fysetc Spider, etc. |
| Stepper Motors | NEMA 17 | NEMA 17 with proper drivers |
| Power Supply | 12V/24V 10A+ | 12V/24V 15A+ |
| MicroSD Card | 16GB Class 10 | 32GB+ Class 10 |
| Network | Wired Ethernet | Gigabit Ethernet |

#### Optional Hardware for Testing

- Vacuum pump with pressure sensor
- Component feeders
- Pick-and-place nozzle with vacuum
- Limit switches on all axes
- Temperature sensors (thermistors, thermocouples)
- Camera for visual verification (optional)

### Software Prerequisites

#### 1. Klipper Installation

**Version:** Klipper with Moonraker support (v0.10.0 or later)

**Verify Installation:**
```bash
# Check Klipper service status
sudo systemctl status klipper

# Check Klipper version
~/klipper-env/bin/python ~/klipper/klippy/klippy.py --version

# Verify MCU connection
ls /dev/serial/by-id/
```

**Expected Output:**
```
● klipper.service - Klipper 3D Printer Firmware
   Loaded: loaded (/etc/systemd/system/klipper.service; enabled)
   Active: active (running) since ...
```

#### 2. Moonraker Installation

**Version:** Moonraker 0.8.0 or later

**Verify Installation:**
```bash
# Check Moonraker service status
sudo systemctl status moonraker

# Check Moonraker API
curl http://localhost:7125/server/info

# Verify Moonraker extensions
curl http://localhost:7125/server/info | jq .components
```

**Expected Output:**
```json
{
  "klipper_version": "v0.12.0-123-g1234567",
  "moonraker_version": "v0.9.0-456-gabcdef",
  "api_version": 1,
  "api_server_version": "v0.9.0-456-gabcdef",
  "components": ["gpio_monitor", "fan_control", "pwm_control", "sensor_query"]
}
```

#### 3. KlipperPlace Installation

**Version:** KlipperPlace 1.0.0 or later

**Verify Installation:**
```bash
# Check KlipperPlace service status
sudo systemctl status klipperplace

# Test API endpoint
curl http://localhost:7125/api/v1/version

# Check health endpoint
curl http://localhost:7125/health
```

**Expected Output:**
```json
{
  "api_version": "1.0.0",
  "server_version": "1.0.0",
  "supported_versions": ["v1"],
  "latest_version": "v1"
}
```

#### 4. OpenPNP Installation

**Version:** OpenPNP 2.0 or later

**Verify Installation:**
```bash
# Launch OpenPNP
java -jar OpenPnP.jar

# Check version in Help → About
# Expected: OpenPnP 2.0 or later
```

### Network Configuration

#### Required Network Setup

1. **Local Network:** All components on same network
2. **Static IP:** Assign static IP to Raspberry Pi
3. **Firewall:** Allow port 7125 (or configured port)
4. **Latency:** <10ms latency between components

**Test Network Connectivity:**
```bash
# Test Moonraker connectivity
ping -c 5 localhost

# Test API accessibility
curl -v http://localhost:7125/server/info

# Test WebSocket connectivity
wscat -c ws://localhost:7125/websocket
```

---

## Hardware Test Environment Setup

### Step 1: Prepare Test Machine

#### 1.1 Physical Setup

1. **Mount motherboard securely** to test frame
2. **Connect stepper motors** to appropriate drivers
3. **Install endstops** on all axes
4. **Connect power supply** (ensure proper voltage)
5. **Connect vacuum pump** to designated pin
6. **Connect fan** to fan header
7. **Connect any sensors** (pressure, temperature)
8. **Verify all connections** are secure

#### 1.2 Electrical Safety Check

⚠️ **IMPORTANT:** Perform these checks before powering on:

```bash
# Visual inspection checklist
- [ ] No loose wires
- [ ] No exposed conductors
- [ ] Proper wire gauges for current
- [ ] Polarity correct on all connections
- [ ] No shorts between adjacent pins
- [ ] Proper grounding

# Multimeter checks
- [ ] No continuity between VCC and GND
- [ ] Proper voltage levels on power rails
- [ ] No unexpected resistance on outputs
```

#### 1.3 Power-On Sequence

1. **Connect USB** from Raspberry Pi to motherboard
2. **Power on Raspberry Pi** first
3. **Wait for services** to start (30-60 seconds)
4. **Power on motherboard** (12V/24V supply)
5. **Listen for** any unusual sounds (clicks, whines)
6. **Check for** any smoke or burning smell
7. **Verify LEDs** on motherboard indicate normal operation

### Step 2: Configure Klipper for PnP Operations

#### 2.1 Create PnP-Specific Configuration

Create or modify `/home/pi/printer_data/config/printer.cfg`:

```ini
# PnP Machine Configuration
[stepper_x]
step_pin: PB0
dir_pin: !PB1
enable_pin: !PA4
microsteps: 16
rotation_distance: 40
endstop_pin: ^PB2
position_min: 0
position_endstop: 300
homing_speed: 50
homing_retract_dist: 5

[stepper_y]
step_pin: PB3
dir_pin: !PB4
enable_pin: !PA7
microsteps: 16
rotation_distance: 40
endstop_pin: ^PB5
position_min: 0
position_endstop: 300
homing_speed: 50
homing_retract_dist: 5

[stepper_z]
step_pin: PA8
dir_pin: PA7
enable_pin: !PA6
microsteps: 16
rotation_distance: 8
endstop_pin: ^PA5
position_min: 0
position_endstop: 400
homing_speed: 20
homing_retract_dist: 2

# PnP Vacuum Control
[output_pin vacuum_pin]
pin: !PA2
pwm: True
cycle_time: 0.01
value: 0
shutdown_value: 0
maximum_mcu_duration: 5.000000

# PnP Actuator Control
[output_pin actuator_pin]
pin: !PA3
pwm: False
value: 0
shutdown_value: 0

# PnP Fan Control
[fan]
pin: PB6
kick_start_time: 0.5
off_below: 0.10
cycle_time: 0.010

# Virtual Fan for Vacuum
[fan_generic vacuum_fan]
pin: PA2
max_power: 1.0
kick_start_time: 0.1
off_below: 0.05
cycle_time: 0.010
```

#### 2.2 Restart Klipper

```bash
# Restart Klipper to apply configuration
sudo systemctl restart klipper

# Verify Klipper started successfully
sudo systemctl status klipper

# Check for errors in logs
sudo journalctl -u klipper -n 50
```

### Step 3: Configure Moonraker Extensions

#### 3.1 Add KlipperPlace Extensions to Moonraker

Edit `/etc/moonraker.conf`:

```ini
# KlipperPlace Extensions
[gpio_monitor]
enabled_pins:
poll_interval: 50

[fan_control]
default_fan: fan
default_speed: 0.5
max_speed: 1.0

[pwm_control]
default_pin: vacuum_pin
default_value: 0.0
ramp_duration: 0.5
ramp_steps: 20

[sensor_query]
enabled_sensors:
include_timestamp: true
flatten_response: false
```

#### 3.2 Restart Moonraker

```bash
# Restart Moonraker to apply configuration
sudo systemctl restart moonraker

# Verify Moonraker started successfully
sudo systemctl status moonraker

# Check for errors in logs
sudo journalctl -u moonraker -n 50
```

### Step 4: Configure KlipperPlace

#### 4.1 Create KlipperPlace Configuration

Create `config/klipperplace.json`:

```json
{
    "host": "0.0.0.0",
    "port": 7125,
    "moonraker_host": "localhost",
    "moonraker_port": 7125,
    "moonraker_api_key": null,
    "enable_cors": true,
    
    "api_key_enabled": false,
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
    "safety_max_x_position": 300.0,
    "safety_max_y_position": 300.0,
    "safety_max_z_position": 400.0,
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

#### 4.2 Start KlipperPlace

```bash
# Start KlipperPlace service
sudo systemctl start klipperplace

# Enable service to start on boot
sudo systemctl enable klipperplace

# Verify KlipperPlace started successfully
sudo systemctl status klipperplace

# Check logs for errors
tail -f logs/klipperplace.log
```

### Step 5: Verify All Services

#### 5.1 Service Status Check

```bash
# Check all services
echo "=== Klipper ==="
sudo systemctl status klipper --no-pager

echo "=== Moonraker ==="
sudo systemctl status moonraker --no-pager

echo "=== KlipperPlace ==="
sudo systemctl status klipperplace --no-pager
```

#### 5.2 API Health Check

```bash
# Test KlipperPlace API
curl http://localhost:7125/health

# Test Moonraker API
curl http://localhost:7125/server/info

# Test KlipperPlace version
curl http://localhost:7125/api/v1/version
```

**Expected Output:**
```json
{
  "status": "healthy",
  "server": "KlipperPlace",
  "version": "1.0.0",
  "uptime": 123.456,
  "connections": {
    "moonraker": true,
    "klipper": true
  }
}
```

---

## Testing REST Endpoints

This section provides detailed procedures for testing all 32 REST endpoints with real hardware.

### Test Preparation

#### Create Test Script

Create `scripts/test_rest_endpoints.sh`:

```bash
#!/bin/bash

# Configuration
API_BASE="http://localhost:7125/api/v1"
API_KEY=""  # Set if authentication enabled

# Headers
if [ -n "$API_KEY" ]; then
    HEADERS="-H 'Content-Type: application/json' -H 'X-API-Key: $API_KEY'"
else
    HEADERS="-H 'Content-Type: application/json'"
fi

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test function
test_endpoint() {
    local name=$1
    local method=$2
    local endpoint=$3
    local data=$4
    
    echo -e "${YELLOW}Testing: $name${NC}"
    echo "Method: $method"
    echo "Endpoint: $endpoint"
    
    if [ -n "$data" ]; then
        echo "Data: $data"
        response=$(curl -s -w "\n%{http_code}" -X $method "$API_BASE$endpoint" $HEADERS -d "$data")
    else
        response=$(curl -s -w "\n%{http_code}" -X $method "$API_BASE$endpoint" $HEADERS)
    fi
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "204" ]; then
        echo -e "${GREEN}✓ PASS${NC} (HTTP $http_code)"
    else
        echo -e "${RED}✗ FAIL${NC} (HTTP $http_code)"
        echo "Response: $body"
    fi
    echo ""
}

# Home axes before motion tests
echo "=== Homing Axes ==="
test_endpoint "Home All Axes" "POST" "/motion/home" '{"axes": ["x", "y", "z"]}'
sleep 2
```

Make it executable:
```bash
chmod +x scripts/test_rest_endpoints.sh
```

---

### Motion Commands Testing

#### Test 1: POST /motion/move

**Purpose:** Test toolhead movement to specified coordinates

**Test Procedure:**

```bash
# Test 1: Move to center position
curl -X POST http://localhost:7125/api/v1/motion/move \
  -H "Content-Type: application/json" \
  -d '{
    "x": 150.0,
    "y": 150.0,
    "z": 10.0,
    "feedrate": 3000
  }'

# Expected Response:
{
  "status": "success",
  "command": "move",
  "command_id": "...",
  "data": {
    "position": {"x": 150.0, "y": 150.0, "z": 10.0},
    "execution_time": 0.125
  },
  "timestamp": ...
}

# Verify physical movement
echo "Check that toolhead moved to center position"
```

**Verification Steps:**
1. [ ] Toolhead moves to X=150, Y=150, Z=10
2. [ ] Movement is smooth, no jerking
3. [ ] No error messages in logs
4. [ ] Response time < 500ms
5. [ ] Position reported correctly in API

**Test Variations:**

```bash
# Test 2: Move with relative positioning
curl -X POST http://localhost:7125/api/v1/motion/move \
  -H "Content-Type: application/json" \
  -d '{
    "x": 10.0,
    "y": 10.0,
    "z": 5.0,
    "relative": true,
    "feedrate": 2000
  }'

# Test 3: Move with high feedrate
curl -X POST http://localhost:7125/api/v1/motion/move \
  -H "Content-Type: application/json" \
  -d '{
    "x": 200.0,
    "y": 200.0,
    "z": 20.0,
    "feedrate": 5000
  }'

# Test 4: Move to edge positions
curl -X POST http://localhost:7125/api/v1/motion/move \
  -H "Content-Type: application/json" \
  -d '{
    "x": 290.0,
    "y": 290.0,
    "z": 390.0,
    "feedrate": 3000
  }'
```

**Expected Results:**
- All movements execute successfully
- Toolhead reaches target positions
- No position errors reported
- Movement is smooth and accurate

**Document Issues:**
- [ ] Any axis fails to move
- [ ] Position inaccuracy > 1mm
- [ ] Unusual sounds during movement
- [ ] Timeout errors
- [ ] Position out of bounds errors

---

#### Test 2: POST /motion/home

**Purpose:** Test homing of all axes

**Test Procedure:**

```bash
# Test 1: Home all axes
curl -X POST http://localhost:7125/api/v1/motion/home \
  -H "Content-Type: application/json" \
  -d '{"axes": ["x", "y", "z"]}'

# Expected Response:
{
  "status": "success",
  "command": "home",
  "command_id": "...",
  "data": {
    "homed_axes": ["x", "y", "z"],
    "execution_time": 2.5
  },
  "timestamp": ...
}

# Verify physical homing
echo "Check that all axes homed to endstops"
```

**Verification Steps:**
1. [ ] All axes move toward endstops
2. [ ] Endstops trigger correctly
3. [ ] Axes stop at endstop positions
4. [ ] No error messages in logs
5. [ ] Homed status reported correctly

**Test Variations:**

```bash
# Test 2: Home only X and Y
curl -X POST http://localhost:7125/api/v1/motion/home \
  -H "Content-Type: application/json" \
  -d '{"axes": ["x", "y"]}'

# Test 3: Home only Z
curl -X POST http://localhost:7125/api/v1/motion/home \
  -H "Content-Type: application/json" \
  -d '{"axes": ["z"]}'

# Test 4: Home with no parameters (default all)
curl -X POST http://localhost:7125/api/v1/motion/home \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Expected Results:**
- All specified axes home correctly
- Endstops trigger at expected positions
- Homing completes in reasonable time (< 10 seconds)
- No false triggers or missed triggers

**Document Issues:**
- [ ] Axis fails to home
- [ ] Endstop not triggered
- [ ] Homing takes too long
- [ ] Homing position inaccurate

---

### Pick and Place Commands Testing

#### Test 3: POST /pnp/pick

**Purpose:** Test pick operation at current position

**Test Procedure:**

```bash
# First, move to a pick position
curl -X POST http://localhost:7125/api/v1/motion/move \
  -H "Content-Type: application/json" \
  -d '{"x": 100.0, "y": 100.0, "z": 10.0}'

# Test pick operation
curl -X POST http://localhost:7125/api/v1/pnp/pick \
  -H "Content-Type: application/json" \
  -d '{
    "z": 0.5,
    "feedrate": 500,
    "vacuum_power": 255,
    "travel_height": 5.0
  }'

# Expected Response:
{
  "status": "success",
  "command": "pick",
  "command_id": "...",
  "data": {
    "position": {"x": 100.0, "y": 100.0, "z": 0.5},
    "vacuum_enabled": true,
    "gcode": "G0 Z0.5 F500\nM106 S255\nG0 Z5.0",
    "execution_time": 0.75
  },
  "timestamp": ...
}

# Verify physical pick operation
echo "Check that nozzle lowered, vacuum enabled, then raised"
```

**Verification Steps:**
1. [ ] Nozzle lowers to pick height (Z=0.5)
2. [ ] Vacuum pump activates
3. [ ] Nozzle raises to travel height (Z=5.0)
4. [ ] Component picked up (if test component present)
5. [ ] No error messages in logs

**Test Variations:**

```bash
# Test 2: Pick with different vacuum power
curl -X POST http://localhost:7125/api/v1/pnp/pick \
  -H "Content-Type: application/json" \
  -d '{"z": 0.5, "vacuum_power": 128, "travel_height": 5.0}'

# Test 3: Pick with custom feedrate
curl -X POST http://localhost:7125/api/v1/pnp/pick \
  -H "Content-Type: application/json" \
  -d '{"z": 0.3, "feedrate": 300, "vacuum_power": 255}'
```

**Document Issues:**
- [ ] Vacuum doesn't activate
- [ ] Nozzle doesn't lower correctly
- [ ] Component not picked up
- [ ] Vacuum power incorrect

---

#### Test 4: POST /pnp/place

**Purpose:** Test place operation at current position

**Test Procedure:**

```bash
# Move to a place position (after pick)
curl -X POST http://localhost:7125/api/v1/motion/move \
  -H "Content-Type: application/json" \
  -d '{"x": 200.0, "y": 200.0, "z": 10.0}'

# Test place operation
curl -X POST http://localhost:7125/api/v1/pnp/place \
  -H "Content-Type: application/json" \
  -d '{
    "z": 0.2,
    "feedrate": 500,
    "travel_height": 5.0
  }'

# Expected Response:
{
  "status": "success",
  "command": "place",
  "command_id": "...",
  "data": {
    "position": {"x": 200.0, "y": 200.0, "z": 0.2},
    "vacuum_enabled": false,
    "gcode": "G0 Z0.2 F500\nM107\nG0 Z5.0",
    "execution_time": 0.75
  },
  "timestamp": ...
}

# Verify physical place operation
echo "Check that nozzle lowered, vacuum disabled, then raised"
```

**Verification Steps:**
1. [ ] Nozzle lowers to place height (Z=0.2)
2. [ ] Vacuum pump deactivates
3. [ ] Nozzle raises to travel height (Z=5.0)
4. [ ] Component placed (if test component present)
5. [ ] No error messages in logs

**Document Issues:**
- [ ] Vacuum doesn't deactivate
- [ ] Component not released
- [ ] Nozzle doesn't raise correctly

---

#### Test 5: POST /pnp/pick_and_place

**Purpose:** Test complete pick and place operation

**Test Procedure:**

```bash
# Test complete pick and place
curl -X POST http://localhost:7125/api/v1/pnp/pick_and_place \
  -H "Content-Type: application/json" \
  -d '{
    "x": 100.0,
    "y": 100.0,
    "place_x": 200.0,
    "place_y": 200.0,
    "pick_height": 0.5,
    "place_height": 0.2,
    "safe_height": 10.0,
    "feedrate": 3000,
    "vacuum_power": 255
  }'

# Expected Response:
{
  "status": "success",
  "command": "pick_and_place",
  "command_id": "...",
  "data": {
    "pick_position": {"x": 100.0, "y": 100.0, "z": 0.5},
    "place_position": {"x": 200.0, "y": 200.0, "z": 0.2},
    "vacuum_enabled": false,
    "gcode": "G0 Z10.0 F3000\nG0 X100.0 Y100.0 F3000\nG0 Z0.5 F3000\nM106 S255\nG0 Z10.0 F3000\nG0 X200.0 Y200.0 F3000\nG0 Z0.2 F3000\nM107\nG0 Z10.0 F3000",
    "execution_time": 2.5
  },
  "timestamp": ...
}

# Verify physical pick and place
echo "Observe complete pick and place sequence"
```

**Verification Steps:**
1. [ ] Nozzle moves to safe height
2. [ ] Nozzle moves to pick position
3. [ ] Nozzle lowers to pick height
4. [ ] Vacuum activates
5. [ ] Nozzle raises to safe height
6. [ ] Nozzle moves to place position
7. [ ] Nozzle lowers to place height
8. [ ] Vacuum deactivates
9. [ ] Nozzle raises to safe height
10. [ ] Component successfully transferred

**Document Issues:**
- [ ] Sequence doesn't execute correctly
- [ ] Component dropped during transfer
- [ ] Vacuum timing incorrect
- [ ] Movement sequence wrong

---

### Actuator Commands Testing

#### Test 6: POST /actuators/actuate

**Purpose:** Test GPIO pin control

**Test Procedure:**

```bash
# Test actuating a GPIO pin
curl -X POST http://localhost:7125/api/v1/actuators/actuate \
  -H "Content-Type: application/json" \
  -d '{
    "pin": "PA0",
    "value": 1
  }'

# Expected Response:
{
  "status": "success",
  "command": "actuate",
  "command_id": "...",
  "data": {
    "pin": "PA0",
    "value": 1,
    "gcode": "SET_PIN PIN=PA0 VALUE=1",
    "execution_time": 0.01
  },
  "timestamp": ...
}

# Verify with multimeter
echo "Check PA0 pin voltage (should be 3.3V or 5V)"
```

**Verification Steps:**
1. [ ] Pin voltage changes to high (3.3V/5V)
2. [ ] Connected device activates
3. [ ] No error messages in logs
4. [ ] Response time < 50ms

**Test Variations:**

```bash
# Test 2: Turn pin off
curl -X POST http://localhost:7125/api/v1/actuators/actuate \
  -H "Content-Type: application/json" \
  -d '{"pin": "PA0", "value": 0}'

# Test 3: Actuate different pin
curl -X POST http://localhost:7125/api/v1/actuators/actuate \
  -H "Content-Type: application/json" \
  -d '{"pin": "PA3", "value": 1}'
```

**Document Issues:**
- [ ] Pin doesn't change state
- [ ] Wrong voltage level
- [ ] Pin not accessible

---

#### Test 7: POST /actuators/on

**Purpose:** Test turning on an actuator

**Test Procedure:**

```bash
# Test turning on actuator
curl -X POST http://localhost:7125/api/v1/actuators/on \
  -H "Content-Type: application/json" \
  -d '{"pin": "PA1"}'

# Expected Response:
{
  "status": "success",
  "command": "actuator_on",
  "command_id": "...",
  "data": {
    "pin": "PA1",
    "value": 1,
    "gcode": "SET_PIN PIN=PA1 VALUE=1",
    "execution_time": 0.01
  },
  "timestamp": ...
}

# Verify actuator is on
echo "Check that PA1 is HIGH"
```

**Verification Steps:**
1. [ ] Pin goes HIGH
2. [ ] Connected device turns on
3. [ ] State persists

---

#### Test 8: POST /actuators/off

**Purpose:** Test turning off an actuator

**Test Procedure:**

```bash
# Test turning off actuator
curl -X POST http://localhost:7125/api/v1/actuators/off \
  -H "Content-Type: application/json" \
  -d '{"pin": "PA1"}'

# Expected Response:
{
  "status": "success",
  "command": "actuator_off",
  "command_id": "...",
  "data": {
    "pin": "PA1",
    "value": 0,
    "gcode": "SET_PIN PIN=PA1 VALUE=0",
    "execution_time": 0.01
  },
  "timestamp": ...
}

# Verify actuator is off
echo "Check that PA1 is LOW"
```

**Verification Steps:**
1. [ ] Pin goes LOW
2. [ ] Connected device turns off
3. [ ] State persists

---

### Vacuum Commands Testing

#### Test 9: POST /vacuum/on

**Purpose:** Test enabling vacuum pump

**Test Procedure:**

```bash
# Test turning on vacuum
curl -X POST http://localhost:7125/api/v1/vacuum/on \
  -H "Content-Type: application/json" \
  -d '{"power": 255}'

# Expected Response:
{
  "status": "success",
  "command": "vacuum_on",
  "command_id": "...",
  "data": {
    "power": 255,
    "gcode": "M106 S255",
    "execution_time": 0.01
  },
  "timestamp": ...
}

# Verify vacuum pump is running
echo "Check that vacuum pump is operating"
echo "Check vacuum sensor reading (if available)"
```

**Verification Steps:**
1. [ ] Vacuum pump activates
2. [ ] Vacuum pressure increases
3. [ ] Fan/PWM output correct
4. [ ] No error messages in logs

**Test Variations:**

```bash
# Test 2: Vacuum at half power
curl -X POST http://localhost:7125/api/v1/vacuum/on \
  -H "Content-Type: application/json" \
  -d '{"power": 128}'

# Test 3: Vacuum at low power
curl -X POST http://localhost:7125/api/v1/vacuum/on \
  -H "Content-Type: application/json" \
  -d '{"power": 50}'
```

**Document Issues:**
- [ ] Vacuum doesn't activate
- [ ] Pressure too low
- [ ] PWM output incorrect
- [ ] Vacuum power doesn't match request

---

#### Test 10: POST /vacuum/off

**Purpose:** Test disabling vacuum pump

**Test Procedure:**

```bash
# Test turning off vacuum
curl -X POST http://localhost:7125/api/v1/vacuum/off \
  -H "Content-Type: application/json"

# Expected Response:
{
  "status": "success",
  "command": "vacuum_off",
  "command_id": "...",
  "data": {
    "gcode": "M107",
    "execution_time": 0.01
  },
  "timestamp": ...
}

# Verify vacuum pump is off
echo "Check that vacuum pump stopped"
echo "Check vacuum pressure drops to zero"
```

**Verification Steps:**
1. [ ] Vacuum pump deactivates
2. [ ] Vacuum pressure drops
3. [ ] Fan/PWM output stops

---

#### Test 11: POST /vacuum/set

**Purpose:** Test setting vacuum power level

**Test Procedure:**

```bash
# Test setting vacuum power
curl -X POST http://localhost:7125/api/v1/vacuum/set \
  -H "Content-Type: application/json" \
  -d '{"power": 200}'

# Expected Response:
{
  "status": "success",
  "command": "vacuum_set",
  "command_id": "...",
  "data": {
    "power": 200,
    "gcode": "M106 S200",
    "execution_time": 0.01
  },
  "timestamp": ...
}

# Verify vacuum power level
echo "Check vacuum power is at 200/255"
```

**Verification Steps:**
1. [ ] Vacuum power changes to specified level
2. [ ] PWM output matches request
3. [ ] Vacuum pressure changes accordingly

**Test Variations:**

```bash
# Test 2: Set to minimum power
curl -X POST http://localhost:7125/api/v1/vacuum/set \
  -H "Content-Type: application/json" \
  -d '{"power": 0}'

# Test 3: Set to maximum power
curl -X POST http://localhost:7125/api/v1/vacuum/set \
  -H "Content-Type: application/json" \
  -d '{"power": 255}'
```

---

### Fan Commands Testing

#### Test 12: POST /fan/on

**Purpose:** Test enabling fan

**Test Procedure:**

```bash
# Test turning on fan
curl -X POST http://localhost:7125/api/v1/fan/on \
  -H "Content-Type: application/json" \
  -d '{"fan": "fan", "speed": 0.5}'

# Expected Response:
{
  "status": "success",
  "command": "fan_on",
  "command_id": "...",
  "data": {
    "fan": "fan",
    "speed": 0.5,
    "gcode": "M106 S127",
    "execution_time": 0.01
  },
  "timestamp": ...
}

# Verify fan is running
echo "Check that fan is spinning at 50% speed"
```

**Verification Steps:**
1. [ ] Fan activates
2. [ ] Fan speed matches request
3. [ ] No error messages in logs

---

#### Test 13: POST /fan/off

**Purpose:** Test disabling fan

**Test Procedure:**

```bash
# Test turning off fan
curl -X POST http://localhost:7125/api/v1/fan/off \
  -H "Content-Type: application/json" \
  -d '{"fan": "fan"}'

# Expected Response:
{
  "status": "success",
  "command": "fan_off",
  "command_id": "...",
  "data": {
    "fan": "fan",
    "gcode": "M107",
    "execution_time": 0.01
  },
  "timestamp": ...
}

# Verify fan is off
echo "Check that fan stopped spinning"
```

**Verification Steps:**
1. [ ] Fan deactivates
2. [ ] Fan stops spinning

---

#### Test 14: POST /fan/set

**Purpose:** Test setting fan speed

**Test Procedure:**

```bash
# Test setting fan speed
curl -X POST http://localhost:7125/api/v1/fan/set \
  -H "Content-Type: application/json" \
  -d '{"fan": "fan", "speed": 0.75}'

# Expected Response:
{
  "status": "success",
  "command": "fan_set",
  "command_id": "...",
  "data": {
    "fan": "fan",
    "speed": 0.75,
    "gcode": "M106 S191",
    "execution_time": 0.01
  },
  "timestamp": ...
}

# Verify fan speed
echo "Check that fan is at 75% speed"
```

**Verification Steps:**
1. [ ] Fan speed changes to specified level
2. [ ] PWM output matches request

---

### PWM Commands Testing

#### Test 15: POST /pwm/set

**Purpose:** Test setting PWM output

**Test Procedure:**

```bash
# Test setting PWM value
curl -X POST http://localhost:7125/api/v1/pwm/set \
  -H "Content-Type: application/json" \
  -d '{
    "pin": "PA2",
    "value": 0.5,
    "cycle_time": 0.01
  }'

# Expected Response:
{
  "status": "success",
  "command": "pwm_set",
  "command_id": "...",
  "data": {
    "pin": "PA2",
    "value": 0.5,
    "cycle_time": 0.01,
    "execution_time": 0.01
  },
  "timestamp": ...
}

# Verify PWM output with oscilloscope or multimeter
echo "Check PWM output is 50% duty cycle"
```

**Verification Steps:**
1. [ ] PWM output matches requested value
2. [ ] Duty cycle is correct
3. [ ] Cycle time is correct

---

#### Test 16: POST /pwm/ramp

**Purpose:** Test ramping PWM value over time

**Test Procedure:**

```bash
# Test PWM ramp
curl -X POST http://localhost:7125/api/v1/pwm/ramp \
  -H "Content-Type: application/json" \
  -d '{
    "pin": "PA2",
    "start_value": 0.0,
    "end_value": 1.0,
    "duration": 2.0,
    "steps": 20
  }'

# Expected Response:
{
  "status": "success",
  "command": "pwm_ramp",
  "command_id": "...",
  "data": {
    "pin": "PA2",
    "start_value": 0.0,
    "end_value": 1.0,
    "duration": 2.0,
    "steps": 20,
    "execution_time": 2.0
  },
  "timestamp": ...
}

# Verify PWM ramp with oscilloscope
echo "Observe PWM ramp from 0% to 100% over 2 seconds"
```

**Verification Steps:**
1. [ ] PWM ramps smoothly from start to end value
2. [ ] Ramp duration matches request
3. [ ] Number of steps is correct

---

### GPIO Commands Testing

#### Test 17: GET /gpio/read

**Purpose:** Test reading GPIO pin state

**Test Procedure:**

```bash
# Test reading GPIO pin
curl -X GET "http://localhost:7125/api/v1/gpio/read?pin=PB5"

# Expected Response:
{
  "status": "success",
  "command": "gpio_read",
  "command_id": "...",
  "data": {
    "pin": "PB5",
    "state": 1,
    "timestamp": ...
  },
  "timestamp": ...
}

# Verify with multimeter
echo "Check PB5 pin state matches reading"
```

**Verification Steps:**
1. [ ] Pin state matches actual hardware state
2. [ ] Response time < 50ms
3. [ ] No error messages in logs

**Test Variations:**

```bash
# Test 2: Read different pin
curl -X GET "http://localhost:7125/api/v1/gpio/read?pin=PB6"

# Test 3: Read multiple pins in sequence
for pin in PB5 PB6 PB7; do
    curl -X GET "http://localhost:7125/api/v1/gpio/read?pin=$pin"
done
```

**Document Issues:**
- [ ] Pin state doesn't match actual state
- [ ] Pin not accessible
- [ ] Read timeout

---

#### Test 18: POST /gpio/write

**Purpose:** Test writing GPIO pin state

**Test Procedure:**

```bash
# Test writing GPIO pin
curl -X POST http://localhost:7125/api/v1/gpio/write \
  -H "Content-Type: application/json" \
  -d '{"pin": "PB6", "value": 1}'

# Expected Response:
{
  "status": "success",
  "command": "gpio_write",
  "command_id": "...",
  "data": {
    "pin": "PB6",
    "value": 1,
    "gcode": "SET_PIN PIN=PB6 VALUE=1",
    "execution_time": 0.01
  },
  "timestamp": ...
}

# Verify with multimeter
echo "Check PB6 pin is HIGH"
```

**Verification Steps:**
1. [ ] Pin state changes to requested value
2. [ ] Voltage level is correct
3. [ ] State persists

---

#### Test 19: GET /gpio/read_all

**Purpose:** Test reading all configured GPIO pins

**Test Procedure:**

```bash
# Test reading all GPIO pins
curl -X GET http://localhost:7125/api/v1/gpio/read_all

# Expected Response:
{
  "status": "success",
  "command": "gpio_read_all",
  "command_id": "...",
  "data": {
    "pins": {
      "PB5": 1,
      "PB6": 0,
      "PB7": 1,
      "PA0": 0,
      "PA1": 1
    },
    "count": 5
  },
  "timestamp": ...
}

# Verify all pin states
echo "Check all pin states match hardware"
```

**Verification Steps:**
1. [ ] All configured pins are read
2. [ ] Pin states match actual hardware
3. [ ] Response time < 100ms

---

### Sensor Commands Testing

#### Test 20: GET /sensor/read

**Purpose:** Test reading sensor value

**Test Procedure:**

```bash
# Test reading sensor
curl -X GET "http://localhost:7125/api/v1/sensor/read?sensor=pressure_sensor"

# Expected Response:
{
  "status": "success",
  "command": "sensor_read",
  "command_id": "...",
  "data": {
    "sensor": "pressure_sensor",
    "value": 85.5,
    "unit": "kPa",
    "last_updated": ...
  },
  "timestamp": ...
}

# Verify sensor reading
echo "Check sensor reading matches actual value"
```

**Verification Steps:**
1. [ ] Sensor value matches actual hardware reading
2. [ ] Unit is correct
3. [ ] Response time < 100ms

**Test Variations:**

```bash
# Test 2: Read vacuum sensor
curl -X GET "http://localhost:7125/api/v1/sensor/read?sensor=vacuum_sensor"

# Test 3: Read temperature sensor
curl -X GET "http://localhost:7125/api/v1/sensor/read?sensor=temperature_sensor"
```

---

#### Test 21: GET /sensor/read_all

**Purpose:** Test reading all configured sensors

**Test Procedure:**

```bash
# Test reading all sensors
curl -X GET http://localhost:7125/api/v1/sensor/read_all

# Expected Response:
{
  "status": "success",
  "command": "sensor_read_all",
  "command_id": "...",
  "data": {
    "sensors": {
      "pressure_sensor": {
        "value": 85.5,
        "unit": "kPa",
        "last_updated": ...
      },
      "vacuum_sensor": {
        "value": 0.92,
        "unit": "bar",
        "last_updated": ...
      },
      "temperature_sensor": {
        "value": 25.3,
        "unit": "°C",
        "last_updated": ...
      }
    },
    "count": 3
  },
  "timestamp": ...
}

# Verify all sensor readings
echo "Check all sensor readings match hardware"
```

**Verification Steps:**
1. [ ] All configured sensors are read
2. [ ] Sensor values match actual hardware
3. [ ] Response time < 200ms

---

#### Test 22: GET /sensor/read_by_type

**Purpose:** Test reading sensors by type

**Test Procedure:**

```bash
# Test reading pressure sensors
curl -X GET "http://localhost:7125/api/v1/sensor/read_by_type?type=pressure"

# Expected Response:
{
  "status": "success",
  "command": "sensor_read_by_type",
  "command_id": "...",
  "data": {
    "type": "pressure",
    "sensors": {
      "pressure_sensor_1": {
        "value": 85.5,
        "unit": "kPa",
        "last_updated": ...
      },
      "pressure_sensor_2": {
        "value": 87.2,
        "unit": "kPa",
        "last_updated": ...
      }
    },
    "count": 2
  },
  "timestamp": ...
}

# Verify all sensors of type
echo "Check all pressure sensors are read"
```

**Verification Steps:**
1. [ ] All sensors of specified type are read
2. [ ] Sensor values match actual hardware

---

### Feeder Commands Testing

#### Test 23: POST /feeder/advance

**Purpose:** Test advancing feeder

**Test Procedure:**

```bash
# Test advancing feeder
curl -X POST http://localhost:7125/api/v1/feeder/advance \
  -H "Content-Type: application/json" \
  -d '{"feeder": "feeder_1", "distance": 10.0, "feedrate": 100.0}'

# Expected Response:
{
  "status": "success",
  "command": "feeder_advance",
  "command_id": "...",
  "data": {
    "feeder": "feeder_1",
    "distance": 10.0,
    "gcode": "G0 E10.0 F100.0",
    "execution_time": 0.5
  },
  "timestamp": ...
}

# Verify feeder advancement
echo "Check that feeder advanced 10mm"
```

**Verification Steps:**
1. [ ] Feeder advances correct distance
2. [ ] Feedrate is correct
3. [ ] No error messages in logs

---

#### Test 24: POST /feeder/retract

**Purpose:** Test retracting feeder

**Test Procedure:**

```bash
# Test retracting feeder
curl -X POST http://localhost:7125/api/v1/feeder/retract \
  -H "Content-Type: application/json" \
  -d '{"feeder": "feeder_1", "distance": 10.0, "feedrate": 100.0}'

# Expected Response:
{
  "status": "success",
  "command": "feeder_retract",
  "command_id": "...",
  "data": {
    "feeder": "feeder_1",
    "distance": 10.0,
    "gcode": "G0 E-10.0 F100.0",
    "execution_time": 0.5
  },
  "timestamp": ...
}

# Verify feeder retraction
echo "Check that feeder retracted 10mm"
```

**Verification Steps:**
1. [ ] Feeder retracts correct distance
2. [ ] Feedrate is correct
3. [ ] No error messages in logs

---

### Status Commands Testing

#### Test 25: GET /status

**Purpose:** Test getting comprehensive system status

**Test Procedure:**

```bash
# Test getting system status
curl -X GET http://localhost:7125/api/v1/status

# Expected Response:
{
  "status": "success",
  "command": "get_status",
  "command_id": "...",
  "data": {
    "printer_status": {
      "state": "ready",
      "klippy_connected": true,
      "moonraker_connected": true
    },
    "position": {
      "x": 150.0,
      "y": 150.0,
      "z": 10.0
    },
    "homed_axes": ["x", "y", "z"],
    "vacuum_enabled": false,
    "fan_speed": 0.5,
    "actuators": {
      "PA0": 1,
      "PA1": 0
    },
    "queue": {
      "size": 5,
      "executing": false
    }
  },
  "timestamp": ...
}

# Verify status accuracy
echo "Check all status values match actual state"
```

**Verification Steps:**
1. [ ] All status fields are present
2. [ ] Values match actual hardware state
3. [ ] Response time < 200ms

---

#### Test 26: GET /position

**Purpose:** Test getting current toolhead position

**Test Procedure:**

```bash
# Test getting position
curl -X GET http://localhost:7125/api/v1/position

# Expected Response:
{
  "status": "success",
  "command": "get_position",
  "command_id": "...",
  "data": {
    "position": {
      "x": 150.0,
      "y": 150.0,
      "z": 10.0
    },
    "positioning_mode": "absolute",
    "units": "mm"
  },
  "timestamp": ...
}

# Verify position accuracy
echo "Check position matches actual toolhead location"
```

**Verification Steps:**
1. [ ] Position values are accurate
2. [ ] Positioning mode is correct
3. [ ] Units are correct

---

#### Test 27: GET /printer/state

**Purpose:** Test getting printer state information

**Test Procedure:**

```bash
# Test getting printer state
curl -X GET http://localhost:7125/api/v1/printer/state

# Expected Response:
{
  "status": "success",
  "command": "get_printer_state",
  "command_id": "...",
  "data": {
    "klippy_state": "ready",
    "klippy_connected": true,
    "moonraker_connected": true,
    "print_stats": {
      "state": "idle",
      "print_duration": 0.0
    }
  },
  "timestamp": ...
}

# Verify printer state
echo "Check printer state matches actual status"
```

**Verification Steps:**
1. [ ] Klippy state is correct
2. [ ] Connection status is accurate
3. [ ] Print stats are correct

---

### Queue Commands Testing

#### Test 28: POST /queue/add

**Purpose:** Test adding command to execution queue

**Test Procedure:**

```bash
# Test adding command to queue
curl -X POST http://localhost:7125/api/v1/queue/add \
  -H "Content-Type: application/json" \
  -d '{
    "command": "move",
    "parameters": {
      "x": 100.0,
      "y": 50.0,
      "z": 10.0
    },
    "priority": 0
  }'

# Expected Response:
{
  "status": "success",
  "command": "queue_add",
  "command_id": "...",
  "data": {
    "queue_id": "q-...",
    "queue_position": 5,
    "queue_size": 6
  },
  "timestamp": ...
}

# Verify queue status
curl -X GET http://localhost:7125/api/v1/queue/status
```

**Verification Steps:**
1. [ ] Command is added to queue
2. [ ] Queue ID is generated
3. [ ] Queue position is correct

---

#### Test 29: POST /queue/batch

**Purpose:** Test adding multiple commands to queue

**Test Procedure:**

```bash
# Test adding batch of commands
curl -X POST http://localhost:7125/api/v1/queue/batch \
  -H "Content-Type: application/json" \
  -d '{
    "commands": [
      {
        "command": "move",
        "parameters": {"x": 100.0, "y": 50.0}
      },
      {
        "command": "pick",
        "parameters": {"z": 0.5}
      },
      {
        "command": "move",
        "parameters": {"x": 150.0, "y": 75.0}
      },
      {
        "command": "place",
        "parameters": {"z": 0.2}
      }
    ],
    "stop_on_error": true
  }'

# Expected Response:
{
  "status": "success",
  "command": "queue_batch",
  "command_id": "...",
  "data": {
    "queue_ids": [
      "q-...-0001",
      "q-...-0002",
      "q-...-0003",
      "q-...-0004"
    ],
    "queue_size": 9
  },
  "timestamp": ...
}

# Verify batch queue status
curl -X GET http://localhost:7125/api/v1/queue/status
```

**Verification Steps:**
1. [ ] All commands are added to queue
2. [ ] Queue IDs are generated for all commands
3. [ ] Commands execute in correct order

---

#### Test 30: GET /queue/status

**Purpose:** Test getting queue status

**Test Procedure:**

```bash
# Test getting queue status
curl -X GET http://localhost:7125/api/v1/queue/status

# Expected Response:
{
  "status": "success",
  "command": "queue_status",
  "command_id": "...",
  "data": {
    "queue_size": 5,
    "executing": true,
    "current_command": {
      "id": "q-...-0003",
      "command": "pick",
      "status": "executing"
    },
    "queued_commands": [
      {
        "id": "q-...-0004",
        "command": "move",
        "status": "pending"
      },
      {
        "id": "q-...-0005",
        "command": "place",
        "status": "pending"
      }
    ]
  },
  "timestamp": ...
}

# Verify queue status accuracy
echo "Check queue status matches actual state"
```

**Verification Steps:**
1. [ ] Queue size is correct
2. [ ] Current command is accurate
3. [ ] Queued commands are listed

---

#### Test 31: DELETE /queue/clear

**Purpose:** Test clearing all commands from queue

**Test Procedure:**

```bash
# First, add some commands to queue
curl -X POST http://localhost:7125/api/v1/queue/add \
  -H "Content-Type: application/json" \
  -d '{"command": "move", "parameters": {"x": 100.0}}'

# Test clearing queue
curl -X DELETE http://localhost:7125/api/v1/queue/clear

# Expected Response:
{
  "status": "success",
  "command": "queue_clear",
  "command_id": "...",
  "data": {
    "cleared_count": 5,
    "message": "Queue cleared successfully"
  },
  "timestamp": ...
}

# Verify queue is empty
curl -X GET http://localhost:7125/api/v1/queue/status
```

**Verification Steps:**
1. [ ] All commands are removed from queue
2. [ ] Queue size is 0
3. [ ] No commands are executing

---

#### Test 32: DELETE /queue/cancel

**Purpose:** Test cancelling specific queued command

**Test Procedure:**

```bash
# First, add a command to queue and get queue_id
response=$(curl -X POST http://localhost:7125/api/v1/queue/add \
  -H "Content-Type: application/json" \
  -d '{"command": "move", "parameters": {"x": 100.0}}')

queue_id=$(echo $response | jq -r '.data.queue_id')

# Test cancelling command
curl -X DELETE http://localhost:7125/api/v1/queue/cancel \
  -H "Content-Type: application/json" \
  -d "{\"queue_id\": \"$queue_id\"}"

# Expected Response:
{
  "status": "success",
  "command": "queue_cancel",
  "command_id": "...",
  "data": {
    "cancelled_id": "q-...",
    "message": "Command cancelled successfully"
  },
  "timestamp": ...
}

# Verify command is cancelled
curl -X GET http://localhost:7125/api/v1/queue/status
```

**Verification Steps:**
1. [ ] Specified command is removed from queue
2. [ ] Other commands remain in queue
3. [ ] Cancelled command doesn't execute

---

### System Commands Testing

#### Test 33: POST /system/emergency_stop

**Purpose:** Test emergency stop functionality

**Test Procedure:**

```bash
# Start a movement
curl -X POST http://localhost:7125/api/v1/motion/move \
  -H "Content-Type: application/json" \
  -d '{"x": 200.0, "y": 200.0, "z": 50.0}'

# Immediately trigger emergency stop
curl -X POST http://localhost:7125/api/v1/system/emergency_stop \
  -H "Content-Type: application/json" \
  -d '{"reason": "Test emergency stop"}'

# Expected Response:
{
  "status": "success",
  "command": "emergency_stop",
  "command_id": "...",
  "data": {
    "emergency_stop_active": true,
    "reason": "Test emergency stop",
    "gcode_sent": "M112"
  },
  "timestamp": ...
}

# Verify emergency stop
echo "Check that all motion stopped immediately"
echo "Check that motors are disabled"
```

**Verification Steps:**
1. [ ] All motion stops immediately
2. [ ] Motors are disabled
3. [ ] Emergency stop flag is set
4. [ ] No error messages in logs

⚠️ **IMPORTANT:** This test will stop all motion. Be prepared for sudden stop.

---

#### Test 34: POST /system/pause

**Purpose:** Test pausing current execution

**Test Procedure:**

```bash
# Start a movement
curl -X POST http://localhost:7125/api/v1/motion/move \
  -H "Content-Type: application/json" \
  -d '{"x": 200.0, "y": 200.0, "z": 50.0}'

# Pause execution
curl -X POST http://localhost:7125/api/v1/system/pause

# Expected Response:
{
  "status": "success",
  "command": "pause",
  "command_id": "...",
  "data": {
    "paused": true,
    "message": "Execution paused"
  },
  "timestamp": ...
}

# Verify pause
echo "Check that motion paused at current position"
```

**Verification Steps:**
1. [ ] Motion pauses at current position
2. [ ] Pause flag is set
3. [ ] Toolhead holds position

---

#### Test 35: POST /system/resume

**Purpose:** Test resuming paused execution

**Test Procedure:**

```bash
# Resume execution
curl -X POST http://localhost:7125/api/v1/system/resume

# Expected Response:
{
  "status": "success",
  "command": "resume",
  "command_id": "...",
  "data": {
    "resumed": true,
    "message": "Execution resumed"
  },
  "timestamp": ...
}

# Verify resume
echo "Check that motion resumes from paused position"
```

**Verification Steps:**
1. [ ] Motion resumes from paused position
2. [ ] Pause flag is cleared
3. [ ] Movement continues to target

---

#### Test 36: POST /system/reset

**Purpose:** Test resetting system state

**Test Procedure:**

```bash
# Reset system
curl -X POST http://localhost:7125/api/v1/system/reset

# Expected Response:
{
  "status": "success",
  "command": "reset",
  "command_id": "...",
  "data": {
    "reset_complete": true,
    "message": "System reset successfully"
  },
  "timestamp": ...
}

# Verify reset
curl -X GET http://localhost:7125/api/v1/status
echo "Check that system state is reset"
```

**Verification Steps:**
1. [ ] System state is reset
2. [ ] Queue is cleared
3. [ ] Flags are cleared
4. [ ] System returns to ready state

---

### Batch Operations Testing

#### Test 37: POST /batch/execute

**Purpose:** Test executing multiple commands in single request

**Test Procedure:**

```bash
# Test batch execution
curl -X POST http://localhost:7125/api/v1/batch/execute \
  -H "Content-Type: application/json" \
  -d '{
    "commands": [
      {
        "command": "move",
        "parameters": {"x": 100.0, "y": 50.0}
      },
      {
        "command": "pick",
        "parameters": {"z": 0.5}
      },
      {
        "command": "move",
        "parameters": {"x": 150.0, "y": 75.0}
      },
      {
        "command": "place",
        "parameters": {"z": 0.2}
      }
    ],
    "stop_on_error": true,
    "parallel": false
  }'

# Expected Response:
{
  "status": "success",
  "command": "batch_execute",
  "command_id": "...",
  "data": {
    "results": [
      {
        "command": "move",
        "status": "success",
        "execution_time": 0.125
      },
      {
        "command": "pick",
        "status": "success",
        "execution_time": 0.75
      },
      {
        "command": "move",
        "status": "success",
        "execution_time": 0.125
      },
      {
        "command": "place",
        "status": "success",
        "execution_time": 0.75
      }
    ],
    "total_execution_time": 1.75,
    "success_count": 4,
    "error_count": 0
  },
  "timestamp": ...
}

# Verify batch execution
echo "Check that all commands executed in sequence"
```

**Verification Steps:**
1. [ ] All commands execute successfully
2. [ ] Commands execute in correct order
3. [ ] Execution times are reasonable
4. [ ] No partial execution

---

### Version Information Testing

#### Test 38: GET /version

**Purpose:** Test getting API version information

**Test Procedure:**

```bash
# Test getting version
curl -X GET http://localhost:7125/api/v1/version

# Expected Response:
{
  "api_version": "1.0.0",
  "server_version": "1.0.0",
  "supported_versions": ["v1"],
  "latest_version": "v1",
  "deprecation_notices": []
}
```

**Verification Steps:**
1. [ ] API version is correct
2. [ ] Server version is correct
3. [ ] Supported versions are listed
4. [ ] No deprecation notices (expected)

---

## Testing WebSocket Communication

### WebSocket Connection Testing

#### Test 1: Basic WebSocket Connection

**Purpose:** Test establishing WebSocket connection

**Test Procedure:**

```python
# Create test_websocket.py
import asyncio
import websockets
import json

async def test_websocket_connection():
    uri = "ws://localhost:7125/ws/v1"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✓ WebSocket connected successfully")
            
            # Send subscription request
            subscribe_msg = {
                "jsonrpc": "2.0",
                "method": "subscribe",
                "params": {
                    "events": ["position", "sensors", "status"]
                },
                "id": 1
            }
            await websocket.send(json.dumps(subscribe_msg))
            print("✓ Subscription request sent")
            
            # Receive response
            response = await websocket.recv()
            data = json.loads(response)
            print(f"✓ Subscription response: {data}")
            
            # Wait for a few updates
            for i in range(3):
                update = await websocket.recv()
                data = json.loads(update)
                print(f"✓ Update {i+1}: {data.get('method', 'unknown')}")
            
            print("✓ WebSocket test completed successfully")
            
    except Exception as e:
        print(f"✗ WebSocket test failed: {e}")
        return False
    
    return True

# Run test
success = asyncio.run(test_websocket_connection())
exit(0 if success else 1)
```

**Run Test:**
```bash
python test_websocket.py
```

**Expected Output:**
```
✓ WebSocket connected successfully
✓ Subscription request sent
✓ Subscription response: {'jsonrpc': '2.0', 'result': {'subscribed': True, 'events': ['position', 'sensors', 'status']}, 'id': 1}
✓ Update 1: notify_position_update
✓ Update 2: notify_sensor_update
✓ Update 3: notify_status_update
✓ WebSocket test completed successfully
```

**Verification Steps:**
1. [ ] WebSocket connection establishes
2. [ ] Subscription request succeeds
3. [ ] Real-time updates are received
4. [ ] Connection remains stable

---

#### Test 2: WebSocket Event Subscription

**Purpose:** Test subscribing to different event types

**Test Procedure:**

```python
# Create test_websocket_subscriptions.py
import asyncio
import websockets
import json

async def test_event_subscriptions():
    uri = "ws://localhost:7125/ws/v1"
    
    events_to_test = [
        ["position"],
        ["sensors"],
        ["queue"],
        ["status"],
        ["gpio"],
        ["actuators"],
        ["safety"],
        ["position", "sensors", "queue", "status", "gpio", "actuators", "safety"]
    ]
    
    async with websockets.connect(uri) as websocket:
        for events in events_to_test:
            # Subscribe to events
            subscribe_msg = {
                "jsonrpc": "2.0",
                "method": "subscribe",
                "params": {"events": events},
                "id": len(events_to_test)
            }
            await websocket.send(json.dumps(subscribe_msg))
            
            # Receive response
            response = await websocket.recv()
            data = json.loads(response)
            
            if data.get('result', {}).get('subscribed'):
                print(f"✓ Subscribed to: {events}")
            else:
                print(f"✗ Failed to subscribe to: {events}")
            
            # Unsubscribe
            unsubscribe_msg = {
                "jsonrpc": "2.0",
                "method": "unsubscribe",
                "params": {"events": events},
                "id": len(events_to_test) + 1
            }
            await websocket.send(json.dumps(unsubscribe_msg))
            
            # Receive response
            response = await websocket.recv()
            data = json.loads(response)
            
            if data.get('result', {}).get('unsubscribed'):
                print(f"✓ Unsubscribed from: {events}")
            else:
                print(f"✗ Failed to unsubscribe from: {events}")

asyncio.run(test_event_subscriptions())
```

**Verification Steps:**
1. [ ] All event types can be subscribed to
2. [ ] Subscription responses are correct
3. [ ] Unsubscription works
4. [ ] No errors in logs

---

#### Test 3: WebSocket Real-Time Updates

**Purpose:** Test receiving real-time updates

**Test Procedure:**

```python
# Create test_websocket_updates.py
import asyncio
import websockets
import json
import time

async def test_realtime_updates():
    uri = "ws://localhost:7125/ws/v1"
    
    async with websockets.connect(uri) as websocket:
        # Subscribe to all events
        subscribe_msg = {
            "jsonrpc": "2.0",
            "method": "subscribe",
            "params": {
                "events": ["position", "sensors", "queue", "status", "gpio", "actuators", "safety"]
            },
            "id": 1
        }
        await websocket.send(json.dumps(subscribe_msg))
        
        # Receive subscription confirmation
        response = await websocket.recv()
        print("Subscribed to all events")
        
        # Trigger some changes
        print("Triggering position change...")
        import subprocess
        subprocess.run([
            "curl", "-X", "POST",
            "http://localhost:7125/api/v1/motion/move",
            "-H", "Content-Type: application/json",
            "-d", '{"x": 100.0, "y": 100.0, "z": 10.0}'
        ])
        
        # Collect updates for 10 seconds
        updates_received = []
        start_time = time.time()
        
        while time.time() - start_time < 10:
            try:
                update = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                data = json.loads(update)
                event_type = data.get('method', 'unknown')
                updates_received.append(event_type)
                print(f"✓ Received: {event_type}")
            except asyncio.TimeoutError:
                pass
        
        print(f"\nTotal updates received: {len(updates_received)}")
        print(f"Event types: {set(updates_received)}")
        
        # Verify expected updates
        expected_events = {"notify_position_update"}
        if expected_events.issubset(set(updates_received)):
            print("✓ All expected events received")
        else:
            print("✗ Some expected events missing")

asyncio.run(test_realtime_updates())
```

**Verification Steps:**
1. [ ] Position updates are received
2. [ ] Updates are timely (< 1 second after change)
3. [ ] Update data is accurate
4. [ ] No duplicate updates

---

#### Test 4: WebSocket Command Execution

**Purpose:** Test executing commands via WebSocket

**Test Procedure:**

```python
# Create test_websocket_commands.py
import asyncio
import websockets
import json

async def test_websocket_commands():
    uri = "ws://localhost:7125/ws/v1"
    
    async with websockets.connect(uri) as websocket:
        # Subscribe to events
        subscribe_msg = {
            "jsonrpc": "2.0",
            "method": "subscribe",
            "params": {"events": ["position"]},
            "id": 1
        }
        await websocket.send(json.dumps(subscribe_msg))
        
        # Execute move command via WebSocket
        execute_msg = {
            "jsonrpc": "2.0",
            "method": "execute",
            "params": {
                "command": "move",
                "parameters": {
                    "x": 150.0,
                    "y": 150.0,
                    "z": 10.0
                }
            },
            "id": 2
        }
        await websocket.send(json.dumps(execute_msg))
        print("✓ Move command sent via WebSocket")
        
        # Receive response
        response = await websocket.recv()
        data = json.loads(response)
        
        if data.get('result', {}).get('status') == 'success':
            print("✓ Command executed successfully via WebSocket")
            print(f"Position: {data['result']['data']['position']}")
        else:
            print("✗ Command execution failed")
            print(f"Error: {data}")

asyncio.run(test_websocket_commands())
```

**Verification Steps:**
1. [ ] Commands can be executed via WebSocket
2. [ ] Responses are correct
3. [ ] Hardware responds to commands

---

#### Test 5: WebSocket Connection Stability

**Purpose:** Test WebSocket connection stability over time

**Test Procedure:**

```python
# Create test_websocket_stability.py
import asyncio
import websockets
import json
import time

async def test_websocket_stability():
    uri = "ws://localhost:7125/ws/v1"
    
    async with websockets.connect(uri) as websocket:
        # Subscribe to events
        subscribe_msg = {
            "jsonrpc": "2.0",
            "method": "subscribe",
            "params": {"events": ["position", "sensors", "status"]},
            "id": 1
        }
        await websocket.send(json.dumps(subscribe_msg))
        
        # Monitor connection for 5 minutes
        print("Monitoring WebSocket connection for 5 minutes...")
        start_time = time.time()
        update_count = 0
        last_update_time = time.time()
        
        while time.time() - start_time < 300:  # 5 minutes
            try:
                update = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(update)
                update_count += 1
                last_update_time = time.time()
                print(f"Update {update_count}: {data.get('method', 'unknown')}")
            except asyncio.TimeoutError:
                # No update, check connection
                elapsed = time.time() - last_update_time
                if elapsed > 30:
                    print(f"⚠ No updates for {elapsed:.0f} seconds")
        
        print(f"\n✓ Connection stable for 5 minutes")
        print(f"Total updates: {update_count}")
        print(f"Average updates/minute: {update_count / 5:.1f}")

asyncio.run(test_websocket_stability())
```

**Verification Steps:**
1. [ ] Connection remains stable for 5 minutes
2. [ ] Regular updates are received
3. [ ] No unexpected disconnections
4. [ ] No connection errors

---

#### Test 6: WebSocket Reconnection

**Purpose:** Test WebSocket reconnection after disconnect

**Test Procedure:**

```python
# Create test_websocket_reconnection.py
import asyncio
import websockets
import json

async def test_websocket_reconnection():
    uri = "ws://localhost:7125/ws/v1"
    
    # First connection
    print("Connecting to WebSocket...")
    async with websockets.connect(uri) as websocket:
        subscribe_msg = {
            "jsonrpc": "2.0",
            "method": "subscribe",
            "params": {"events": ["position"]},
            "id": 1
        }
        await websocket.send(json.dumps(subscribe_msg))
        response = await websocket.recv()
        print("✓ First connection established")
        
        # Simulate disconnect by closing
        await asyncio.sleep(2)
        print("Simulating disconnect...")
    
    # Reconnection
    print("Reconnecting to WebSocket...")
    reconnect_attempts = 0
    max_attempts = 5
    
    while reconnect_attempts < max_attempts:
        try:
            async with websockets.connect(uri) as websocket:
                subscribe_msg = {
                    "jsonrpc": "2.0",
                    "method": "subscribe",
                    "params": {"events": ["position"]},
                    "id": 1
                }
                await websocket.send(json.dumps(subscribe_msg))
                response = await websocket.recv()
                print(f"✓ Reconnection successful on attempt {reconnect_attempts + 1}")
                return True
        except Exception as e:
            reconnect_attempts += 1
            print(f"✗ Reconnection attempt {reconnect_attempts} failed: {e}")
            await asyncio.sleep(2)
    
    print("✗ Failed to reconnect after maximum attempts")
    return False

success = asyncio.run(test_websocket_reconnection())
exit(0 if success else 1)
```

**Verification Steps:**
1. [ ] Reconnection succeeds
2. [ ] Subscription works after reconnection
3. [ ] No data loss during reconnection

---

## Testing Safety Mechanisms

### Safety Limits Testing

#### Test 1: Position Limit Enforcement

**Purpose:** Test that position limits are enforced

**Test Procedure:**

```bash
# Test 1: Attempt to move beyond X limit
curl -X POST http://localhost:7125/api/v1/motion/move \
  -H "Content-Type: application/json" \
  -d '{"x": 350.0, "y": 150.0, "z": 10.0}'

# Expected Response (Error):
{
  "status": "error",
  "command": "move",
  "command_id": "...",
  "error_code": "POSITION_OUT_OF_BOUNDS",
  "error_message": "X position 350.0 mm exceeds maximum of 300.0 mm",
  "details": {
    "axis": "x",
    "position": 350.0,
    "max_limit": 300.0
  },
  "timestamp": ...
}

# Verify no movement
echo "Check that toolhead did not move beyond limit"
```

**Verification Steps:**
1. [ ] Position out of bounds error is returned
2. [ ] Toolhead does not move beyond limit
3. [ ] No physical damage occurs
4. [ ] Error message is clear

**Test Variations:**

```bash
# Test 2: Attempt to move beyond Y limit
curl -X POST http://localhost:7125/api/v1/motion/move \
  -H "Content-Type: application/json" \
  -d '{"x": 150.0, "y": 350.0, "z": 10.0}'

# Test 3: Attempt to move beyond Z limit
curl -X POST http://localhost:7125/api/v1/motion/move \
  -H "Content-Type: application/json" \
  -d '{"x": 150.0, "y": 150.0, "z": 450.0}'

# Test 4: Attempt to move to negative position
curl -X POST http://localhost:7125/api/v1/motion/move \
  -H "Content-Type: application/json" \
  -d '{"x": -10.0, "y": 150.0, "z": 10.0}'
```

---

#### Test 2: Feedrate Limit Enforcement

**Purpose:** Test that feedrate limits are enforced

**Test Procedure:**

```bash
# Test 1: Attempt to move with excessive feedrate
curl -X POST http://localhost:7125/api/v1/motion/move \
  -H "Content-Type: application/json" \
  -d '{"x": 150.0, "y": 150.0, "z": 10.0, "feedrate": 50000}'

# Expected Response (Error):
{
  "status": "error",
  "command": "move",
  "command_id": "...",
  "error_code": "FEEDRATE_OUT_OF_BOUNDS",
  "error_message": "Feedrate 50000 mm/min exceeds maximum of 40000 mm/min",
  "details": {
    "feedrate": 50000.0,
    "max_feedrate": 40000.0
  },
  "timestamp": ...
}

# Verify movement uses safe feedrate
echo "Check that movement uses safe feedrate"
```

**Verification Steps:**
1. [ ] Feedrate out of bounds error is returned
2. [ ] Movement is limited to safe feedrate
3. [ ] No physical damage occurs

---

#### Test 3: PWM Value Limit Enforcement

**Purpose:** Test that PWM value limits are enforced

**Test Procedure:**

```bash
# Test 1: Attempt to set PWM beyond maximum
curl -X POST http://localhost:7125/api/v1/pwm/set \
  -H "Content-Type: application/json" \
  -d '{"pin": "PA2", "value": 1.5}'

# Expected Response (Error):
{
  "status": "error",
  "command": "pwm_set",
  "command_id": "...",
  "error_code": "PWM_OUT_OF_BOUNDS",
  "error_message": "PWM value 1.5 exceeds maximum of 1.0",
  "details": {
    "value": 1.5,
    "max_value": 1.0,
    "min_value": 0.0
  },
  "timestamp": ...
}

# Verify PWM is not set beyond limit
echo "Check that PWM is not set beyond limit"
```

**Verification Steps:**
1. [ ] PWM out of bounds error is returned
2. [ ] PWM is not set beyond limit
3. [ ] No hardware damage occurs

---

#### Test 4: Fan Speed Limit Enforcement

**Purpose:** Test that fan speed limits are enforced

**Test Procedure:**

```bash
# Test 1: Attempt to set fan speed beyond maximum
curl -X POST http://localhost:7125/api/v1/fan/set \
  -H "Content-Type: application/json" \
  -d '{"fan": "fan", "speed": 1.5}'

# Expected Response (Error):
{
  "status": "error",
  "command": "fan_set",
  "command_id": "...",
  "error_code": "FAN_SPEED_OUT_OF_BOUNDS",
  "error_message": "Fan speed 1.5 exceeds maximum of 1.0",
  "details": {
    "speed": 1.5,
    "max_speed": 1.0,
    "min_speed": 0.0
  },
  "timestamp": ...
}

# Verify fan speed is not set beyond limit
echo "Check that fan speed is not set beyond limit"
```

**Verification Steps:**
1. [ ] Fan speed out of bounds error is returned
2. [ ] Fan speed is not set beyond limit
3. [ ] No hardware damage occurs

---

### Emergency Stop Testing

#### Test 5: Emergency Stop During Motion

**Purpose:** Test emergency stop functionality during motion

**Test Procedure:**

```bash
# Start a long movement
curl -X POST http://localhost:7125/api/v1/motion/move \
  -H "Content-Type: application/json" \
  -d '{"x": 250.0, "y": 250.0, "z": 50.0, "feedrate": 1000}' &

# Wait 1 second for movement to start
sleep 1

# Trigger emergency stop
curl -X POST http://localhost:7125/api/v1/system/emergency_stop \
  -H "Content-Type: application/json" \
  -d '{"reason": "Test emergency stop during motion"}'

# Expected Response:
{
  "status": "success",
  "command": "emergency_stop",
  "command_id": "...",
  "data": {
    "emergency_stop_active": true,
    "reason": "Test emergency stop during motion",
    "gcode_sent": "M112"
  },
  "timestamp": ...
}

# Verify immediate stop
echo "Check that motion stopped immediately"
echo "Check that motors are disabled"
```

**Verification Steps:**
1. [ ] Motion stops immediately
2. [ ] Motors are disabled
3. [ ] Emergency stop flag is set
4. [ ] No coasting or overshoot

⚠️ **IMPORTANT:** Keep hand near emergency stop button during this test.

---

#### Test 6: Emergency Stop Recovery

**Purpose:** Test system recovery after emergency stop

**Test Procedure:**

```bash
# Trigger emergency stop
curl -X POST http://localhost:7125/api/v1/system/emergency_stop \
  -H "Content-Type: application/json" \
  -d '{"reason": "Test emergency stop recovery"}'

# Wait 2 seconds
sleep 2

# Check system status
curl -X GET http://localhost:7125/api/v1/status

# Expected Response:
{
  "status": "success",
  "command": "get_status",
  "command_id": "...",
  "data": {
    "printer_status": {
      "state": "emergency_stop",
      "klippy_connected": true,
      "moonraker_connected": true
    },
    "emergency_stop_active": true,
    ...
  },
  "timestamp": ...
}

# Attempt to reset system
curl -X POST http://localhost:7125/api/v1/system/reset

# Home axes after reset
curl -X POST http://localhost:7125/api/v1/motion/home \
  -H "Content-Type: application/json" \
  -d '{"axes": ["x", "y", "z"]}'

# Verify recovery
echo "Check that system recovers after reset"
```

**Verification Steps:**
1. [ ] Emergency stop state is reported
2. [ ] System can be reset
3. [ ] Axes can be homed after reset
4. [ ] System returns to ready state

---

### Safety Monitoring Testing

#### Test 7: Temperature Monitoring

**Purpose:** Test temperature safety monitoring

**Test Procedure:**

```bash
# If you have temperature sensors, check monitoring
curl -X GET http://localhost:7125/api/v1/sensor/read?sensor=temperature_sensor

# Monitor temperature over time
for i in {1..10}; do
    curl -X GET http://localhost:7125/api/v1/sensor/read?sensor=temperature_sensor
    sleep 5
done

# Check logs for temperature warnings
tail -100 logs/klipperplace.log | grep -i temperature
```

**Verification Steps:**
1. [ ] Temperature readings are accurate
2. [ ] Temperature warnings are logged if limits exceeded
3. [ ] Temperature monitoring interval is correct

---

#### Test 8: Position Monitoring

**Purpose:** Test position safety monitoring

**Test Procedure:**

```bash
# Move to various positions and verify monitoring
for pos in "50,50,10" "150,150,10" "250,250,10"; do
    IFS=',' read x y z <<< "$pos"
    curl -X POST http://localhost:7125/api/v1/motion/move \
      -H "Content-Type: application/json" \
      -d "{\"x\": $x, \"y\": $y, \"z\": $z}"
    
    # Check position after move
    curl -X GET http://localhost:7125/api/v1/position
    sleep 2
done

# Check logs for position warnings
tail -100 logs/klipperplace.log | grep -i position
```

**Verification Steps:**
1. [ ] Position is monitored continuously
2. [ ] Position warnings are logged if limits exceeded
3. [ ] Position monitoring interval is correct

---

#### Test 9: State Monitoring

**Purpose:** Test system state monitoring

**Test Procedure:**

```bash
# Monitor system state over time
for i in {1..10}; do
    curl -X GET http://localhost:7125/api/v1/status
    sleep 10
done

# Check logs for state changes
tail -100 logs/klipperplace.log | grep -i "state"
```

**Verification Steps:**
1. [ ] System state is monitored continuously
2. [ ] State changes are logged
3. [ ] State monitoring interval is correct

---

## Testing OpenPNP Integration

### OpenPNP Driver Configuration

#### Step 1: Configure Klipper Driver in OpenPNP

1. **Open OpenPNP**
2. **Navigate to:** Machine Setup → Drivers
3. **Add New Driver:** Select "Klipper"
4. **Configure Driver:**

```yaml
Driver Configuration:
  Name: KlipperPlace
  Type: Klipper
  Host: localhost
  Port: 7125
  API Key: (leave empty if authentication disabled)
  Enable WebSocket: true
  WebSocket URL: ws://localhost:7125/ws/v1
  Timeout: 30
```

5. **Save Configuration**

---

#### Step 2: Configure Machine Settings

1. **Navigate to:** Machine Setup → Machine
2. **Set Dimensions:**

```yaml
Machine Configuration:
  X Length: 300mm
  Y Length: 300mm
  Z Length: 400mm
  
  Feedrates:
    Maximum Feedrate: 5000mm/min
    Default Feedrate: 2000mm/min
    Acceleration: 3000mm/s²
    
  Safe Heights:
    Safe Z: 10mm
    Pick Height: 0.5mm
    Place Height: 0.2mm
```

3. **Save Configuration**

---

#### Step 3: Configure Actuators

1. **Navigate to:** Machine Setup → Actuators
2. **Add Vacuum Actuator:**

```yaml
Actuator Configuration:
  Name: Vacuum
  Type: Digital Output
  Pin: vacuum_pin
  Invert: false
  Enabled: true
```

3. **Save Configuration**

---

#### Step 4: Configure Feeders

1. **Navigate to:** Machine Setup → Feeders
2. **Add Feeder:**

```yaml
Feeder Configuration:
  Name: Feeder1
  Type: Slot
  X: 50
  Y: 50
  Rotation: 0
  
  Settings:
    Feed Rate: 100mm/min
    Retract Distance: 5mm
    Pickup Height: 2mm
```

3. **Save Configuration**

---

### OpenPNP Integration Testing

#### Test 1: Connection Test

**Purpose:** Test OpenPNP connection to KlipperPlace

**Test Procedure:**

1. **In OpenPNP:** Machine → Connect
2. **Verify Connection Status:**
   - Check that driver shows "Connected"
   - Check for no error messages
   - Verify driver status is green

**Verification Steps:**
1. [ ] OpenPNP connects to KlipperPlace
2. [ ] No connection errors
3. [ ] Driver status shows connected
4. [ ] WebSocket connection established

---

#### Test 2: Homing Test

**Purpose:** Test homing from OpenPNP

**Test Procedure:**

1. **In OpenPNP:** Machine → Home All
2. **Observe:**
   - All axes move toward endstops
   - Endstops trigger
   - Axes stop at home positions
   - OpenPNP shows homed status

**Verification Steps:**
1. [ ] All axes home correctly
2. [ ] OpenPNP shows homed status
3. [ ] No error messages
4. [ ] Homing completes in reasonable time

---

#### Test 3: Jog Movement Test

**Purpose:** Test jog movement from OpenPNP

**Test Procedure:**

1. **In OpenPNP:** Machine → Jog
2. **Test Movements:**

```bash
# Test X axis movement
- Set X to 100
- Click Move
- Verify toolhead moves to X=100

# Test Y axis movement
- Set Y to 100
- Click Move
- Verify toolhead moves to Y=100

# Test Z axis movement
- Set Z to 10
- Click Move
- Verify toolhead moves to Z=10

# Test diagonal movement
- Set X to 150, Y to 150
- Click Move
- Verify toolhead moves to X=150, Y=150
```

**Verification Steps:**
1. [ ] All jog movements execute correctly
2. [ ] Position in OpenPNP matches actual position
3. [ ] Movement is smooth
4. [ ] No error messages

---

#### Test 4: Pick and Place Test

**Purpose:** Test pick and place from OpenPNP

**Test Procedure:**

1. **Create Test Job:**
   - In OpenPNP: Jobs → New Job
   - Add a simple placement
   - Set pick location: X=100, Y=100
   - Set place location: X=200, Y=200
   - Save job

2. **Run Job:**
   - In OpenPNP: Jobs → Run
   - Observe sequence:
     1. Move to safe height
     2. Move to pick location
     3. Lower to pick height
     4. Enable vacuum
     5. Raise to safe height
     6. Move to place location
     7. Lower to place height
     8. Disable vacuum
     9. Raise to safe height

**Verification Steps:**
1. [ ] Complete pick and place sequence executes
2. [ ] Vacuum activates at correct time
3. [ ] Vacuum deactivates at correct time
4. [ ] Movements are accurate
5. [ ] Job completes successfully
6. [ ] No error messages

---

#### Test 5: Actuator Control Test

**Purpose:** Test actuator control from OpenPNP

**Test Procedure:**

1. **In OpenPNP:** Machine → Actuators
2. **Test Vacuum Actuator:**

```bash
# Turn vacuum on
- Click Vacuum → On
- Verify vacuum pump activates
- Check KlipperPlace API: curl http://localhost:7125/api/v1/status

# Turn vacuum off
- Click Vacuum → Off
- Verify vacuum pump deactivates
- Check KlipperPlace API: curl http://localhost:7125/api/v1/status
```

**Verification Steps:**
1. [ ] Vacuum turns on from OpenPNP
2. [ ] Vacuum turns off from OpenPNP
3. [ ] State syncs correctly
4. [ ] No delay in actuation

---

#### Test 6: Real-Time Updates Test

**Purpose:** Test real-time updates in OpenPNP

**Test Procedure:**

1. **In OpenPNP:** Open Machine Setup → Machine
2. **Observe Position Display:**
   - Note current position
   - Execute movement via API
   - Verify position updates in OpenPNP

```bash
# Execute movement via API
curl -X POST http://localhost:7125/api/v1/motion/move \
  -H "Content-Type: application/json" \
  -d '{"x": 150.0, "y": 150.0, "z": 10.0}'

# Check that OpenPNP position updates
echo "Verify position in OpenPNP matches API command"
```

**Verification Steps:**
1. [ ] Position updates in OpenPNP
2. [ ] Updates are timely (< 1 second)
3. [ ] Position values are accurate
4. [ ] No stale data

---

#### Test 7: Error Handling Test

**Purpose:** Test error handling in OpenPNP integration

**Test Procedure:**

1. **Test Position Out of Bounds:**
   - In OpenPNP: Jog → Set X to 400 (beyond limit)
   - Click Move
   - Verify error message in OpenPNP
   - Verify no movement occurs

2. **Test Emergency Stop:**
   - In OpenPNP: Machine → Emergency Stop
   - Verify immediate stop
   - Check KlipperPlace status

**Verification Steps:**
1. [ ] Errors are reported in OpenPNP
2. [ ] Error messages are clear
3. [ ] No unsafe operations execute
4. [ ] System remains stable after errors

---

#### Test 8: Job Execution Test

**Purpose:** Test complete job execution from OpenPNP

**Test Procedure:**

1. **Create Test Job:**
   - Add multiple placements
   - Set pick and place locations
   - Configure feedrates

2. **Run Job:**
   - Start job execution
   - Monitor progress
   - Verify each placement

3. **Verify Completion:**
   - Check job status
   - Verify all placements completed
   - Check for errors

**Verification Steps:**
1. [ ] Job executes from start to finish
2. [ ] All placements complete
3. [ ] No errors during execution
4. [ ] Job reports completion
5. [ ] Total time is reasonable

---

## Performance Testing

### Latency Testing

#### Test 1: Measure API Response Latency

**Purpose:** Measure API response times for all endpoints

**Test Procedure:**

```bash
# Create test_latency.sh
#!/bin/bash

API_BASE="http://localhost:7125/api/v1"

# Test function
measure_latency() {
    local name=$1
    local method=$2
    local endpoint=$3
    local data=$4
    
    echo "Testing: $name"
    
    start_time=$(date +%s.%N)
    
    if [ -n "$data" ]; then
        curl -s -X $method "$API_BASE$endpoint" \
          -H "Content-Type: application/json" \
          -d "$data" > /dev/null
    else
        curl -s -X $method "$API_BASE$endpoint" > /dev/null
    fi
    
    end_time=$(date +%s.%N)
    latency=$(echo "$end_time - $start_time" | bc)
    
    echo "Latency: ${latency}s (${latency*1000}ms)"
    echo ""
}

# Test various endpoints
measure_latency "GET /version" "GET" "/version"
measure_latency "GET /status" "GET" "/status"
measure_latency "GET /position" "GET" "/position"
measure_latency "POST /motion/move" "POST" "/motion/move" '{"x": 100.0, "y": 100.0, "z": 10.0}'
measure_latency "POST /vacuum/on" "POST" "/vacuum/on" '{"power": 255}'
measure_latency "GET /gpio/read" "GET" "/gpio/read?pin=PB5"
measure_latency "GET /sensor/read" "GET" "/sensor/read?sensor=pressure_sensor"
```

**Run Test:**
```bash
chmod +x test_latency.sh
./test_latency.sh
```

**Expected Results:**

| Endpoint | Expected Latency | Acceptable Latency |
|----------|------------------|-------------------|
| GET /version | < 50ms | < 100ms |
| GET /status | < 100ms | < 200ms |
| GET /position | < 50ms | < 100ms |
| POST /motion/move | < 200ms | < 500ms |
| POST /vacuum/on | < 50ms | < 100ms |
| GET /gpio/read | < 30ms | < 50ms |
| GET /sensor/read | < 50ms | < 100ms |

**Verification Steps:**
1. [ ] All endpoints meet expected latency
2. [ ] No endpoint exceeds acceptable latency
3. [ ] Latency is consistent across multiple runs

---

#### Test 2: Measure WebSocket Update Latency

**Purpose:** Measure WebSocket update latency

**Test Procedure:**

```python
# Create test_websocket_latency.py
import asyncio
import websockets
import json
import time

async def test_websocket_latency():
    uri = "ws://localhost:7125/ws/v1"
    
    async with websockets.connect(uri) as websocket:
        # Subscribe to position updates
        subscribe_msg = {
            "jsonrpc": "2.0",
            "method": "subscribe",
            "params": {"events": ["position"]},
            "id": 1
        }
        await websocket.send(json.dumps(subscribe_msg))
        
        # Wait for subscription confirmation
        await websocket.recv()
        
        # Trigger position change
        trigger_time = time.time()
        import subprocess
        subprocess.run([
            "curl", "-X", "POST",
            "http://localhost:7125/api/v1/motion/move",
            "-H", "Content-Type: application/json",
            "-d", '{"x": 100.0, "y": 100.0, "z": 10.0}'
        ])
        
        # Wait for position update
        update = await websocket.recv()
        update_time = time.time()
        
        latency = update_time - trigger_time
        print(f"WebSocket update latency: {latency*1000:.2f}ms")
        
        if latency < 0.5:  # 500ms
            print("✓ WebSocket latency acceptable")
        else:
            print("✗ WebSocket latency too high")

asyncio.run(test_websocket_latency())
```

**Expected Results:**
- WebSocket update latency < 500ms
- Ideally < 100ms

**Verification Steps:**
1. [ ] WebSocket updates are timely
2. [ ] Latency is consistent
3. [ ] No delayed updates

---

### Throughput Testing

#### Test 3: Measure Command Throughput

**Purpose:** Measure maximum command throughput

**Test Procedure:**

```bash
# Create test_throughput.sh
#!/bin/bash

API_BASE="http://localhost:7125/api/v1"

# Test 100 sequential move commands
echo "Testing 100 sequential move commands..."
start_time=$(date +%s.%N)

for i in {1..100}; do
    x=$((i % 300))
    y=$((i % 300))
    curl -s -X POST "$API_BASE/motion/move" \
      -H "Content-Type: application/json" \
      -d "{\"x\": $x, \"y\": $y, \"z\": 10.0}" > /dev/null
done

end_time=$(date +%s.%N)
total_time=$(echo "$end_time - $start_time" | bc)
throughput=$(echo "100 / $total_time" | bc)

echo "Total time: ${total_time}s"
echo "Throughput: ${throughput} commands/second"

if (( $(echo "$throughput > 50" | bc -l) )); then
    echo "✓ Throughput acceptable (> 50 commands/sec)"
else
    echo "✗ Throughput too low (< 50 commands/sec)"
fi
```

**Expected Results:**
- Throughput > 50 commands/second
- Ideally > 100 commands/second

**Verification Steps:**
1. [ ] Throughput meets expected levels
2. [ ] No command failures
3. [ ] System remains stable

---

### Resource Usage Testing

#### Test 4: Measure CPU Usage

**Purpose:** Measure CPU usage under load

**Test Procedure:**

```bash
# Monitor CPU usage during load test
echo "Starting CPU usage monitoring..."

# Start load test in background
for i in {1..100}; do
    curl -s -X POST http://localhost:7125/api/v1/motion/move \
      -H "Content-Type: application/json" \
      -d "{\"x\": $((i % 300)), \"y\": $((i % 300)), \"z\": 10.0}" > /dev/null &
done

# Monitor CPU usage for 30 seconds
for i in {1..30}; do
    cpu_usage=$(top -b -n 1 | grep "python" | awk '{print $9}')
    echo "CPU usage: ${cpu_usage}%"
    sleep 1
done

# Wait for background processes
wait
```

**Expected Results:**
- CPU usage < 50% under normal load
- CPU usage < 80% under peak load

**Verification Steps:**
1. [ ] CPU usage is within acceptable range
2. [ ] No CPU spikes
3. [ ] System remains responsive

---

#### Test 5: Measure Memory Usage

**Purpose:** Measure memory usage over time

**Test Procedure:**

```bash
# Monitor memory usage
echo "Starting memory usage monitoring..."

# Get KlipperPlace PID
PID=$(pgrep -f "src.api.server")

# Monitor for 10 minutes
for i in {1..600}; do
    if [ -n "$PID" ]; then
        memory_kb=$(ps -p $PID -o rss=)
        memory_mb=$((memory_kb / 1024))
        echo "Memory usage: ${memory_mb}MB"
        
        if [ $memory_mb -gt 500 ]; then
            echo "⚠ Memory usage high: ${memory_mb}MB"
        fi
    fi
    sleep 1
done
```

**Expected Results:**
- Memory usage < 200MB under normal load
- Memory usage < 500MB under peak load
- No memory leaks (stable usage over time)

**Verification Steps:**
1. [ ] Memory usage is within acceptable range
2. [ ] No memory leaks detected
3. [ ] Memory usage is stable over time

---

#### Test 6: Measure Network Usage

**Purpose:** Measure network bandwidth usage

**Test Procedure:**

```bash
# Monitor network usage
echo "Starting network usage monitoring..."

# Monitor for 10 minutes
for i in {1..600}; do
    # Get network statistics
    rx_bytes=$(cat /sys/class/net/eth0/statistics/rx_bytes)
    tx_bytes=$(cat /sys/class/net/eth0/statistics/tx_bytes)
    
    echo "RX: ${rx_bytes} bytes, TX: ${tx_bytes} bytes"
    
    sleep 1
done
```

**Expected Results:**
- Network usage < 10Mbps under normal load
- Network usage scales with command rate

**Verification Steps:**
1. [ ] Network usage is reasonable
2. [ ] No network congestion
3. [ ] Usage scales appropriately with load

---

## Issue Documentation

### Issue Reporting Template

Create a structured format for documenting issues found during hardware testing:

```markdown
## Hardware Testing Issue Report

### Test Information
- **Test Date:** YYYY-MM-DD
- **Tester Name:** [Name]
- **Hardware Configuration:** [Motherboard, Steppers, etc.]
- **Software Versions:**
  - Klipper: [Version]
  - Moonraker: [Version]
  - KlipperPlace: [Version]
  - OpenPNP: [Version]

### Issue Details
- **Issue ID:** [Unique identifier]
- **Severity:** [Critical/High/Medium/Low]
- **Category:** [REST/WebSocket/Safety/OpenPNP/Performance/Hardware]

### Description
[Brief description of the issue]

### Reproduction Steps
1. [Step 1]
2. [Step 2]
3. [Step 3]

### Expected Behavior
[What should happen]

### Actual Behavior
[What actually happened]

### Error Messages
```
[Error messages from logs or API responses]
```

### Logs
```
[Relevant log entries]
```

### Environment
- **Temperature:** [Ambient temperature]
- **Power Supply:** [Voltage, current rating]
- **Network:** [Latency, bandwidth]
- **Other:** [Any other relevant factors]

### Impact
- **Functionality Affected:** [Which features are broken]
- **Workaround Available:** [Yes/No, describe if yes]
- **User Impact:** [High/Medium/Low]

### Attachments
- [Screenshots]
- [Log files]
- [Configuration files]
- [Other relevant files]

### Resolution
- **Status:** [Open/In Progress/Resolved]
- **Resolution Date:** [YYYY-MM-DD]
- **Resolution:** [Description of fix]
- **Verified By:** [Name]
```

---

### Common Issue Categories

#### 1. Communication Issues

**Symptoms:**
- Connection timeouts
- Connection refused
- Intermittent connectivity

**Documentation:**
```markdown
## Communication Issue

### Symptoms
- API requests timeout
- WebSocket connections drop
- Moonraker connection lost

### Root Cause
[Identify root cause: network, firewall, service crash, etc.]

### Investigation Steps
1. Check network connectivity
2. Check service status
3. Check firewall rules
4. Check logs for errors

### Resolution
[Describe fix]
```

---

#### 2. Hardware Issues

**Symptoms:**
- Motors don't move
- Endstops not triggering
- Incorrect sensor readings

**Documentation:**
```markdown
## Hardware Issue

### Symptoms
- [Specific hardware problem]

### Root Cause
[Identify root cause: wiring, configuration, hardware failure, etc.]

### Investigation Steps
1. Check physical connections
2. Check configuration
3. Test with multimeter/oscilloscope
4. Check logs for errors

### Resolution
[Describe fix]
```

---

#### 3. Performance Issues

**Symptoms:**
- High latency
- Low throughput
- High CPU/memory usage

**Documentation:**
```markdown
## Performance Issue

### Symptoms
- [Specific performance problem]

### Root Cause
[Identify root cause: inefficient code, configuration, hardware limitations, etc.]

### Investigation Steps
1. Profile CPU/memory usage
2. Measure latency/throughput
3. Analyze logs for bottlenecks
4. Check configuration settings

### Resolution
[Describe fix]
```

---

#### 4. Safety Issues

**Symptoms:**
- Safety limits not enforced
- Emergency stop not working
- Unsafe operations allowed

**Documentation:**
```markdown
## Safety Issue

### Symptoms
- [Specific safety problem]

### Root Cause
[Identify root cause: configuration bug, missing check, logic error, etc.]

### Investigation Steps
1. Test safety limit enforcement
2. Test emergency stop functionality
3. Review safety configuration
4. Check logs for safety events

### Resolution
[Describe fix]
```

---

## Test Results Reporting

### Test Summary Template

Create a comprehensive summary of all hardware tests:

```markdown
# Hardware Testing Summary Report

## Test Information
- **Test Date:** YYYY-MM-DD
- **Tester Name:** [Name]
- **Test Duration:** [Hours/Days]
- **Hardware Configuration:**
  - Motherboard: [Model]
  - Stepper Motors: [Type/Count]
  - Power Supply: [Voltage/Current]
  - Sensors: [List]
  - Actuators: [List]

## Software Versions
- **Klipper:** [Version]
- **Moonraker:** [Version]
- **KlipperPlace:** [Version]
- **OpenPNP:** [Version]

## Test Results Overview

### REST Endpoint Tests
| Endpoint | Status | Latency | Notes |
|----------|--------|----------|-------|
| POST /motion/move | [Pass/Fail] | [ms] | [Notes] |
| POST /motion/home | [Pass/Fail] | [ms] | [Notes] |
| POST /pnp/pick | [Pass/Fail] | [ms] | [Notes] |
| POST /pnp/place | [Pass/Fail] | [ms] | [Notes] |
| POST /pnp/pick_and_place | [Pass/Fail] | [ms] | [Notes] |
| POST /actuators/actuate | [Pass/Fail] | [ms] | [Notes] |
| POST /actuators/on | [Pass/Fail] | [ms] | [Notes] |
| POST /actuators/off | [Pass/Fail] | [ms] | [Notes] |
| POST /vacuum/on | [Pass/Fail] | [ms] | [Notes] |
| POST /vacuum/off | [Pass/Fail] | [ms] | [Notes] |
| POST /vacuum/set | [Pass/Fail] | [ms] | [Notes] |
| POST /fan/on | [Pass/Fail] | [ms] | [Notes] |
| POST /fan/off | [Pass/Fail] | [ms] | [Notes] |
| POST /fan/set | [Pass/Fail] | [ms] | [Notes] |
| POST /pwm/set | [Pass/Fail] | [ms] | [Notes] |
| POST /pwm/ramp | [Pass/Fail] | [ms] | [Notes] |
| GET /gpio/read | [Pass/Fail] | [ms] | [Notes] |
| POST /gpio/write | [Pass/Fail] | [ms] | [Notes] |
| GET /gpio/read_all | [Pass/Fail] | [ms] | [Notes] |
| GET /sensor/read | [Pass/Fail] | [ms] | [Notes] |
| GET /sensor/read_all | [Pass/Fail] | [ms] | [Notes] |
| GET /sensor/read_by_type | [Pass/Fail] | [ms] | [Notes] |
| POST /feeder/advance | [Pass/Fail] | [ms] | [Notes] |
| POST /feeder/retract | [Pass/Fail] | [ms] | [Notes] |
| GET /status | [Pass/Fail] | [ms] | [Notes] |
| GET /position | [Pass/Fail] | [ms] | [Notes] |
| GET /printer/state | [Pass/Fail] | [ms] | [Notes] |
| POST /queue/add | [Pass/Fail] | [ms] | [Notes] |
| POST /queue/batch | [Pass/Fail] | [ms] | [Notes] |
| GET /queue/status | [Pass/Fail] | [ms] | [Notes] |
| DELETE /queue/clear | [Pass/Fail] | [ms] | [Notes] |
| DELETE /queue/cancel | [Pass/Fail] | [ms] | [Notes] |
| POST /system/emergency_stop | [Pass/Fail] | [ms] | [Notes] |
| POST /system/pause | [Pass/Fail] | [ms] | [Notes] |
| POST /system/resume | [Pass/Fail] | [ms] | [Notes] |
| POST /system/reset | [Pass/Fail] | [ms] | [Notes] |
| POST /batch/execute | [Pass/Fail] | [ms] | [Notes] |
| GET /version | [Pass/Fail] | [ms] | [Notes] |

**Total REST Endpoints:** 38
**Passed:** [Count]
**Failed:** [Count]
**Pass Rate:** [Percentage]%

### WebSocket Tests
| Test | Status | Latency | Notes |
|------|--------|----------|-------|
| Basic Connection | [Pass/Fail] | [ms] | [Notes] |
| Event Subscription | [Pass/Fail] | [ms] | [Notes] |
| Real-Time Updates | [Pass/Fail] | [ms] | [Notes] |
| Command Execution | [Pass/Fail] | [ms] | [Notes] |
| Connection Stability | [Pass/Fail] | [ms] | [Notes] |
| Reconnection | [Pass/Fail] | [ms] | [Notes] |

**Total WebSocket Tests:** 6
**Passed:** [Count]
**Failed:** [Count]
**Pass Rate:** [Percentage]%

### Safety Mechanism Tests
| Test | Status | Notes |
|------|--------|-------|
| Position Limit Enforcement | [Pass/Fail] | [Notes] |
| Feedrate Limit Enforcement | [Pass/Fail] | [Notes] |
| PWM Value Limit Enforcement | [Pass/Fail] | [Notes] |
| Fan Speed Limit Enforcement | [Pass/Fail] | [Notes] |
| Emergency Stop During Motion | [Pass/Fail] | [Notes] |
| Emergency Stop Recovery | [Pass/Fail] | [Notes] |
| Temperature Monitoring | [Pass/Fail] | [Notes] |
| Position Monitoring | [Pass/Fail] | [Notes] |
| State Monitoring | [Pass/Fail] | [Notes] |

**Total Safety Tests:** 9
**Passed:** [Count]
**Failed:** [Count]
**Pass Rate:** [Percentage]%

### OpenPNP Integration Tests
| Test | Status | Notes |
|------|--------|-------|
| Connection Test | [Pass/Fail] | [Notes] |
| Homing Test | [Pass/Fail] | [Notes] |
| Jog Movement Test | [Pass/Fail] | [Notes] |
| Pick and Place Test | [Pass/Fail] | [Notes] |
| Actuator Control Test | [Pass/Fail] | [Notes] |
| Real-Time Updates Test | [Pass/Fail] | [Notes] |
| Error Handling Test | [Pass/Fail] | [Notes] |
| Job Execution Test | [Pass/Fail] | [Notes] |

**Total OpenPNP Tests:** 8
**Passed:** [Count]
**Failed:** [Count]
**Pass Rate:** [Percentage]%

### Performance Tests
| Test | Result | Notes |
|------|---------|-------|
| API Response Latency | [Pass/Fail] | [Average latency] |
| WebSocket Update Latency | [Pass/Fail] | [Average latency] |
| Command Throughput | [Pass/Fail] | [Commands/sec] |
| CPU Usage | [Pass/Fail] | [Peak usage] |
| Memory Usage | [Pass/Fail] | [Peak usage] |
| Network Usage | [Pass/Fail] | [Peak usage] |

**Total Performance Tests:** 6
**Passed:** [Count]
**Failed:** [Count]
**Pass Rate:** [Percentage]%

### Overall Summary
**Total Tests:** [Sum of all tests]
**Total Passed:** [Sum of all passed]
**Total Failed:** [Sum of all failed]
**Overall Pass Rate:** [Percentage]%

### Issues Found
[Number] issues documented

#### Critical Issues: [Count]
1. [Issue description]
2. [Issue description]

#### High Priority Issues: [Count]
1. [Issue description]
2. [Issue description]

#### Medium Priority Issues: [Count]
1. [Issue description]
2. [Issue description]

#### Low Priority Issues: [Count]
1. [Issue description]
2. [Issue description]

### Recommendations
1. [Recommendation 1]
2. [Recommendation 2]
3. [Recommendation 3]

### Conclusion
[Overall assessment of hardware testing results]
```

---

## Troubleshooting

### Common Hardware Testing Issues

#### Issue 1: Service Won't Start

**Symptoms:**
- KlipperPlace service fails to start
- Error: "Address already in use"
- Error: "Connection refused"

**Solutions:**

1. **Check if port is in use:**
```bash
netstat -tuln | grep 7125
lsof -i :7125
```

2. **Kill process using port:**
```bash
sudo kill -9 <PID>
```

3. **Check service status:**
```bash
sudo systemctl status klipperplace
```

4. **Check logs for errors:**
```bash
tail -100 logs/klipperplace.log
sudo journalctl -u klipperplace -n 50
```

---

#### Issue 2: Moonraker Connection Failed

**Symptoms:**
- Error: "Connection refused"
- Error: "Timeout connecting to Moonraker"
- Health check shows `moonraker_connected: false`

**Solutions:**

1. **Verify Moonraker is running:**
```bash
sudo systemctl status moonraker
```

2. **Check Moonraker API:**
```bash
curl http://localhost:7125/server/info
```

3. **Check Moonraker configuration:**
```bash
cat /etc/moonraker.conf
```

4. **Restart Moonraker:**
```bash
sudo systemctl restart moonraker
```

---

#### Issue 3: Klipper Connection Failed

**Symptoms:**
- Error: "Klipper not connected"
- Commands fail with "Klippy disconnected"
- Health check shows `klipper_connected: false`

**Solutions:**

1. **Verify Klipper is running:**
```bash
sudo systemctl status klipper
```

2. **Check Klipper logs:**
```bash
sudo journalctl -u klipper -n 50
```

3. **Restart Klipper:**
```bash
sudo systemctl restart klipper
```

4. **Check MCU connection:**
```bash
ls /dev/serial/by-id/
```

---

#### Issue 4: Commands Timeout

**Symptoms:**
- Error: "Command execution timeout"
- Commands hang indefinitely
- 504 Gateway Timeout errors

**Solutions:**

1. **Check Klipper responsiveness:**
```bash
time curl http://localhost:7125/printer/info
```

2. **Check for emergency stop:**
```bash
curl http://localhost:7125/api/v1/status | grep emergency_stop
```

3. **Check system resources:**
```bash
top
htop
free -h
```

4. **Increase timeout if needed:**
```json
{
    "timeout": 60.0
}
```

---

#### Issue 5: Hardware Not Responding

**Symptoms:**
- Motors don't move
- Endstops not triggering
- Sensors not reading

**Solutions:**

1. **Check physical connections:**
   - Verify all cables are connected
   - Check for loose connections
   - Verify correct wiring

2. **Check configuration:**
```bash
cat /home/pi/printer_data/config/printer.cfg
```

3. **Test with multimeter:**
   - Measure voltage levels
   - Check for continuity
   - Verify signal levels

4. **Check Klipper logs:**
```bash
sudo journalctl -u klipper -f
```

---

#### Issue 6: WebSocket Connection Drops

**Symptoms:**
- WebSocket disconnects frequently
- Error: "Connection reset by peer"
- Real-time updates stop

**Solutions:**

1. **Check WebSocket logs:**
```bash
tail -f logs/klipperplace.log | grep WebSocket
```

2. **Increase keepalive interval:**
```python
# In WebSocket client configuration
ws = websockets.connect(uri, ping_interval=20, ping_timeout=20)
```

3. **Check network stability:**
```bash
ping localhost
```

4. **Implement reconnection logic:**
```python
while True:
    try:
        async with websockets.connect(uri) as ws:
            await handle_connection(ws)
    except Exception as e:
        print(f"Connection lost: {e}")
        await asyncio.sleep(5)
```

---

## Safety Guidelines

### General Safety Rules

⚠️ **CRITICAL:** Follow these safety guidelines during all hardware testing:

1. **Never leave hardware unattended** during testing
2. **Keep emergency stop accessible** at all times
3. **Start with slow movements** and low speeds
4. **Verify all connections** before powering on
5. **Use proper personal protective equipment** (safety glasses, etc.)
6. **Have fire extinguisher nearby** when testing with power
7. **Never bypass safety limits** without understanding risks
8. **Document all unsafe conditions** immediately
9. **Stop testing immediately** if anything seems wrong
10. **Keep hands away from moving parts** during motion tests

### Electrical Safety

1. **Disconnect power** before making any wiring changes
2. **Verify power is off** with multimeter
3. **Use proper wire gauges** for current levels
4. **Check for shorts** before applying power
5. **Never work on live circuits** unless absolutely necessary
6. **Use insulated tools** when working on powered circuits

### Mechanical Safety

1. **Secure all mounting hardware** properly
2. **Check for loose screws** before testing
3. **Keep fingers clear** of moving parts
4. **Use proper tooling** for adjustments
5. **Never force mechanisms** beyond their design limits

### Testing Safety

1. **Test emergency stop** before any motion tests
2. **Start with small movements** to verify operation
3. **Monitor temperature** of motors and drivers
4. **Listen for unusual sounds** (grinding, clicking, whining)
5. **Watch for smoke or burning smells**
6. **Keep fire extinguisher** accessible
7. **Have emergency stop button** within reach

### Emergency Procedures

#### If Something Goes Wrong:

1. **Press emergency stop immediately**
2. **Disconnect power** if emergency stop doesn't work
3. **Assess the situation** before taking further action
4. **Document the incident** thoroughly
5. **Do not resume testing** until issue is resolved

#### Emergency Stop Testing Safety:

1. **Ensure clear path** for all axes
2. **Remove any objects** from work area
3. **Keep hand on emergency stop** button
4. **Be prepared for sudden stop**
5. **Never test emergency stop** at high speeds

---

## Additional Resources

### Documentation

- [Architecture Documentation](ARCHITECTURE.md) - System architecture overview
- [API Reference](API_REFERENCE.md) - Complete API documentation
- [Configuration Guide](CONFIGURATION.md) - Detailed configuration options
- [Setup Guide](SETUP.md) - Installation and setup instructions
- [Testing Guide](TESTING.md) - Unit and integration testing procedures

### External Resources

- [Klipper Documentation](https://www.klipper3d.org/) - Klipper firmware documentation
- [Moonraker Documentation](https://moonraker.readthedocs.io/) - Moonraker API documentation
- [OpenPNP Documentation](https://openpnp.org/) - OpenPNP software documentation
- [Raspberry Pi Documentation](https://www.raspberrypi.com/documentation/) - Raspberry Pi setup guides

### Community

- **GitHub Repository**: https://github.com/klipperplace/KlipperPlace
- **Issues**: https://github.com/klipperplace/KlipperPlace/issues
- **Discussions**: https://github.com/klipperplace/KlipperPlace/discussions

---

## Appendix

### Test Checklist

Use this checklist to ensure all hardware tests are completed:

#### REST Endpoint Tests
- [ ] POST /motion/move
- [ ] POST /motion/home
- [ ] POST /pnp/pick
- [ ] POST /pnp/place
- [ ] POST /pnp/pick_and_place
- [ ] POST /actuators/actuate
- [ ] POST /actuators/on
- [ ] POST /actuators/off
- [ ] POST /vacuum/on
- [ ] POST /vacuum/off
- [ ] POST /vacuum/set
- [ ] POST /fan/on
- [ ] POST /fan/off
- [ ] POST /fan/set
- [ ] POST /pwm/set
- [ ] POST /pwm/ramp
- [ ] GET /gpio/read
- [ ] POST /gpio/write
- [ ] GET /gpio/read_all
- [ ] GET /sensor/read
- [ ] GET /sensor/read_all
- [ ] GET /sensor/read_by_type
- [ ] POST /feeder/advance
- [ ] POST /feeder/retract
- [ ] GET /status
- [ ] GET /position
- [ ] GET /printer/state
- [ ] POST /queue/add
- [ ] POST /queue/batch
- [ ] GET /queue/status
- [ ] DELETE /queue/clear
- [ ] DELETE /queue/cancel
- [ ] POST /system/emergency_stop
- [ ] POST /system/pause
- [ ] POST /system/resume
- [ ] POST /system/reset
- [ ] POST /batch/execute
- [ ] GET /version

#### WebSocket Tests
- [ ] Basic WebSocket Connection
- [ ] WebSocket Event Subscription
- [ ] WebSocket Real-Time Updates
- [ ] WebSocket Command Execution
- [ ] WebSocket Connection Stability
- [ ] WebSocket Reconnection

#### Safety Mechanism Tests
- [ ] Position Limit Enforcement
- [ ] Feedrate Limit Enforcement
- [ ] PWM Value Limit Enforcement
- [ ] Fan Speed Limit Enforcement
- [ ] Emergency Stop During Motion
- [ ] Emergency Stop Recovery
- [ ] Temperature Monitoring
- [ ] Position Monitoring
- [ ] State Monitoring

#### OpenPNP Integration Tests
- [ ] Connection Test
- [ ] Homing Test
- [ ] Jog Movement Test
- [ ] Pick and Place Test
- [ ] Actuator Control Test
- [ ] Real-Time Updates Test
- [ ] Error Handling Test
- [ ] Job Execution Test

#### Performance Tests
- [ ] API Response Latency
- [ ] WebSocket Update Latency
- [ ] Command Throughput
- [ ] CPU Usage
- [ ] Memory Usage
- [ ] Network Usage

---

**Document Version**: 1.0.0  
**Last Updated**: 2024-01-14  
**Maintained By**: KlipperPlace Development Team
