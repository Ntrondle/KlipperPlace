# KlipperPlace Setup Guide

This guide provides step-by-step instructions for installing, configuring, and running KlipperPlace - the middleware layer that connects Klipper firmware with OpenPNP pick-and-place software.

## Table of Contents

- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Starting the API Server](#starting-the-api-server)
- [OpenPNP Integration](#openpnp-integration)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)
- [Advanced Setup](#advanced-setup)
- [Uninstallation](#uninstallation)

---

## Quick Start

Get KlipperPlace up and running in 5 minutes:

```bash
# 1. Clone the repository (if not already cloned)
cd ~/KlipperPlace

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create minimal configuration
cat > config/klipperplace.json << EOF
{
    "host": "0.0.0.0",
    "port": 7125,
    "moonraker_host": "localhost",
    "moonraker_port": 7125,
    "api_key_enabled": false
}
EOF

# 4. Start the server
python -m src.api.server

# 5. Test the API
curl http://localhost:7125/api/v1/version
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

---

## Prerequisites

### System Requirements

KlipperPlace runs on the same Raspberry Pi as Klipper and Moonraker. The minimum requirements are:

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Raspberry Pi | Pi 3B+ | Pi 4 or Pi 5 |
| RAM | 1GB | 4GB+ |
| Storage | 8GB | 16GB+ |
| OS | Raspberry Pi OS 64-bit | Raspberry Pi OS 64-bit |

### Software Prerequisites

#### 1. Python

**Required Version:** Python 3.8 or higher

**Check Python Version:**
```bash
python3 --version
# Output should be: Python 3.8.x or higher
```

**Install Python (if needed):**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

#### 2. Klipper

**Required Version:** Klipper with Moonraker support

**Verify Klipper Installation:**
```bash
# Check if Klipper service is running
sudo systemctl status klipper

# Check Klipper version
~/klipper-env/bin/python ~/klipper/klippy/klippy.py --version
```

**Install Klipper (if needed):**
```bash
# Follow official Klipper installation guide
# https://www.klipper3d.org/Installation.html
```

#### 3. Moonraker

**Required Version:** Moonraker 0.8.0 or higher

**Verify Moonraker Installation:**
```bash
# Check if Moonraker service is running
sudo systemctl status moonraker

# Check Moonraker API
curl http://localhost:7125/server/info
```

**Expected Output:**
```json
{
  "klipper_version": "v0.12.0-123-g1234567",
  "moonraker_version": "v0.9.0-456-gabcdef",
  "api_version": 1,
  "api_server_version": "v0.9.0-456-gabcdef"
}
```

**Install Moonraker (if needed):**
```bash
# Follow official Moonraker installation guide
# https://moonraker.readthedocs.io/en/latest/installation/
```

#### 4. Git

**Required for cloning the repository:**
```bash
sudo apt install git
```

### Network Requirements

- **Local Network:** KlipperPlace and OpenPNP must be on the same network
- **Firewall:** Port 7125 must be accessible (or use alternative port)
- **Bandwidth:** Minimum 100Mbps recommended for real-time operations

---

## Installation

### Step 1: Clone the Repository

If you haven't already cloned the repository:

```bash
# Navigate to home directory
cd ~

# Clone the repository
git clone https://github.com/klipperplace/KlipperPlace.git

# Navigate to the project directory
cd KlipperPlace
```

**Alternative: Download as ZIP**

If you prefer not to use Git:

```bash
# Download the repository
wget https://github.com/klipperplace/KlipperPlace/archive/main.zip

# Extract the archive
unzip main.zip

# Navigate to the project directory
cd KlipperPlace-main
```

### Step 2: Create Virtual Environment (Optional but Recommended)

Creating a virtual environment isolates KlipperPlace dependencies from system Python:

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Verify activation (prompt should show (venv))
which python
```

### Step 3: Install Python Dependencies

Install the required Python packages:

```bash
# Install from requirements.txt
pip install -r requirements.txt

# For development, install dev dependencies
pip install -r requirements-dev.txt
```

**Dependencies included in `requirements.txt`:**
- `aiohttp` - Async HTTP server/client
- `aiohttp-cors` - CORS support
- `websockets` - WebSocket server
- `python-dotenv` - Environment variable loading
- `pydantic` - Data validation

**Verify Installation:**
```bash
# Check installed packages
pip list | grep -E "aiohttp|websockets|pydantic"

# Test import
python3 -c "import aiohttp; import websockets; import pydantic; print('All dependencies OK')"
```

### Step 4: Create Configuration Directory

```bash
# Create config directory if it doesn't exist
mkdir -p config

# Create logs directory
mkdir -p logs
```

### Step 5: Set Permissions

Ensure proper permissions for configuration and log directories:

```bash
# Set ownership to your user
sudo chown -R $USER:$USER config logs

# Set appropriate permissions
chmod 755 config
chmod 644 config/*
```

---

## Configuration

### Step 1: Create Basic Configuration

Create the main configuration file:

```bash
cat > config/klipperplace.json << 'EOF'
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
EOF
```

### Step 2: Configure Moonraker Extensions

Add KlipperPlace extensions to your Moonraker configuration:

```bash
# Backup existing Moonraker config
sudo cp /etc/moonraker.conf /etc/moonraker.conf.backup

# Add KlipperPlace extensions to Moonraker config
sudo tee -a /etc/moonraker.conf << 'EOF'

# KlipperPlace Extensions
[gpio_monitor]
enabled_pins:
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
enabled_sensors:
include_timestamp: true
flatten_response: false
EOF
```

**Restart Moonraker to apply changes:**
```bash
sudo systemctl restart moonraker
```

### Step 3: Configure Klipper for PnP Operations

Add PnP-specific configuration to your Klipper printer configuration:

```bash
# Add to your printer.cfg
sudo tee -a /home/pi/printer_data/config/printer.cfg << 'EOF'

# PnP Vacuum Control
[output_pin vacuum_pin]
pin: !PA2
pwm: True
cycle_time: 0.01
value: 0
shutdown_value: 0

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
EOF
```

**Restart Klipper to apply changes:**
```bash
sudo systemctl restart klipper
```

### Step 4: Configure API Keys (Optional)

If you want to enable API key authentication:

```bash
# Create API keys file
cat > config/api_keys.json << 'EOF'
{
    "api_keys": []
}
EOF

# Set secure permissions
chmod 600 config/api_keys.json
```

You can create API keys after starting the server (see [API Key Management](#api-key-management)).

### Step 5: Configure Environment Variables (Optional)

Create a `.env` file for environment-specific configuration:

```bash
cat > .env << 'EOF'
# Server Configuration
KLIPPERPLACE_HOST=0.0.0.0
KLIPPERPLACE_PORT=7125

# Moonraker Connection
KLIPPERPLACE_MOONRAKER_HOST=localhost
KLIPPERPLACE_MOONRAKER_PORT=7125

# Authentication
KLIPPERPLACE_API_KEY_ENABLED=false
KLIPPERPLACE_RATE_LIMIT=100

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF
```

**Security Note:** Never commit `.env` files to version control. Add to `.gitignore`:

```bash
echo ".env" >> .gitignore
```

---

## Starting the API Server

### Method 1: Manual Start (Development)

Start the server manually for testing and development:

```bash
# Activate virtual environment (if using)
source venv/bin/activate

# Start the server
python -m src.api.server

# Or with specific configuration
python -m src.api.server --config config/klipperplace.json
```

**Expected Output:**
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:7125 (Press CTRL+C to quit)
```

### Method 2: Systemd Service (Production)

Create a systemd service for automatic startup:

```bash
# Create service file
sudo tee /etc/systemd/system/klipperplace.service << 'EOF'
[Unit]
Description=KlipperPlace API Server
After=network.target moonraker.service klipper.service
Wants=moonraker.service klipper.service

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/home/pi/KlipperPlace
Environment="PATH=/home/pi/KlipperPlace/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/home/pi/KlipperPlace/venv/bin/python -m src.api.server --config config/klipperplace.json
Restart=always
RestartSec=10

# Logging
StandardOutput=append:/home/pi/KlipperPlace/logs/klipperplace.log
StandardError=append:/home/pi/KlipperPlace/logs/klipperplace_error.log

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable klipperplace

# Start the service
sudo systemctl start klipperplace

# Check service status
sudo systemctl status klipperplace
```

### Method 3: Supervisor (Alternative)

If you prefer Supervisor over systemd:

```bash
# Install Supervisor
sudo apt install supervisor

# Create configuration file
sudo tee /etc/supervisor/conf.d/klipperplace.conf << 'EOF'
[program:klipperplace]
command=/home/pi/KlipperPlace/venv/bin/python -m src.api.server --config config/klipperplace.json
directory=/home/pi/KlipperPlace
user=pi
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/home/pi/KlipperPlace/logs/klipperplace_supervisor.log
environment=KLIPPERPLACE_HOST="0.0.0.0",KLIPPERPLACE_PORT="7125"
EOF

# Update Supervisor
sudo supervisorctl update

# Start the service
sudo supervisorctl start klipperplace

# Check status
sudo supervisorctl status klipperplace
```

### Verifying Server Startup

Test that the server is running correctly:

```bash
# Check if port is listening
netstat -tuln | grep 7125

# Test API endpoint
curl http://localhost:7125/api/v1/version

# Test health endpoint
curl http://localhost:7125/health
```

**Expected Health Check Output:**
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

## OpenPNP Integration

### Step 1: Configure OpenPNP Klipper Driver

KlipperPlace provides a Klipper-compatible API that OpenPNP can use with its Klipper driver.

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
  API Key: (if enabled)
  Enable WebSocket: true
  WebSocket URL: ws://localhost:7125/ws/v1
```

### Step 2: Configure OpenPNP Machine Settings

Set up your machine configuration in OpenPNP:

1. **Navigate to:** Machine Setup → Machine
2. **Set Dimensions:**
   - X Length: 300mm (or your machine size)
   - Y Length: 300mm (or your machine size)
   - Z Length: 100mm (or your machine size)
3. **Configure Feedrates:**
   - Maximum Feedrate: 5000mm/min
   - Default Feedrate: 2000mm/min
4. **Set Safe Heights:**
   - Safe Z: 10mm
   - Pick Height: 0.5mm
   - Place Height: 0.2mm

### Step 3: Configure Vacuum and Actuators

Set up vacuum and actuator controls in OpenPNP:

1. **Navigate to:** Machine Setup → Actuators
2. **Add Vacuum Actuator:**
   ```yaml
   Actuator Configuration:
     Name: Vacuum
     Type: Digital Output
     Pin: vacuum_pin
     Invert: false
   ```
3. **Add Additional Actuators:**
   ```yaml
   Actuator Configuration:
     Name: Actuator1
     Type: Digital Output
     Pin: actuator_pin
     Invert: false
   ```

### Step 4: Configure Feeders

Set up component feeders in OpenPNP:

1. **Navigate to:** Machine Setup → Feeders
2. **Add Feeder:**
   ```yaml
   Feeder Configuration:
     Name: Feeder1
     Type: Slot
     X: 50
     Y: 50
     Rotation: 0
   ```
3. **Configure Feeder Settings:**
   - Feed Rate: 100mm/min
   - Retract Distance: 5mm
   - Pickup Height: 2mm

### Step 5: Test Integration

Test the OpenPNP integration:

1. **Home the Machine:**
   - In OpenPNP: Machine → Home All
   - Verify axes move to home position

2. **Test Movement:**
   - In OpenPNP: Machine → Jog
   - Move to X: 100, Y: 100, Z: 10
   - Verify movement in KlipperPlace logs

3. **Test Vacuum:**
   - In OpenPNP: Machine → Actuators → Vacuum → On
   - Verify vacuum activates
   - Check KlipperPlace API: `curl http://localhost:7125/api/v1/vacuum/on`

4. **Test Pick and Place:**
   - Create a simple job in OpenPNP
   - Run the job
   - Verify pick and place operations complete successfully

### Step 6: Configure OpenPNP Job Settings

Optimize job settings for KlipperPlace:

```yaml
Job Configuration:
  Safety Height: 10mm
  Approach Height: 2mm
  Place Height: 0.2mm
  Pick Height: 0.5mm
  
  Motion Settings:
    Maximum Feedrate: 5000mm/min
    Acceleration: 3000mm/s²
    Jerk: 10mm/s³
    
  Vacuum Settings:
    Pickup Delay: 100ms
    Place Delay: 100ms
    Vacuum Power: 255
```

---

## Verification

### Verify KlipperPlace Installation

Run comprehensive verification tests:

```bash
# 1. Check server is running
curl http://localhost:7125/health

# 2. Check API version
curl http://localhost:7125/api/v1/version

# 3. Check system status
curl http://localhost:7125/api/v1/status

# 4. Check position
curl http://localhost:7125/api/v1/position

# 5. Test movement (ensure machine is homed first)
curl -X POST http://localhost:7125/api/v1/motion/move \
  -H "Content-Type: application/json" \
  -d '{"x": 10, "y": 10, "z": 5, "feedrate": 1000}'
```

### Verify Moonraker Connection

Test Moonraker extension endpoints:

```bash
# Test GPIO monitor
curl http://localhost:7125/api/gpio_monitor/inputs

# Test fan control
curl http://localhost:7125/api/fan_control/fan

# Test PWM control
curl http://localhost:7125/api/pwm_control/pins

# Test sensor query
curl http://localhost:7125/api/sensor_query/sensors
```

### Verify Klipper Connection

Test Klipper through Moonraker:

```bash
# Get printer info
curl http://localhost:7125/printer/info

# Get printer objects
curl http://localhost:7125/printer/objects?gcode_move=1&toolhead=1

# Send G-code
curl -X POST http://localhost:7125/api/printer/gcode/script \
  -H "Content-Type: application/json" \
  -d '{"script": "G28"}'
```

### Verify WebSocket Connection

Test WebSocket connectivity:

```python
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:7125/ws/v1"
    async with websockets.connect(uri) as websocket:
        # Subscribe to events
        subscribe_msg = {
            "jsonrpc": "2.0",
            "method": "subscribe",
            "params": {
                "events": ["position", "sensors", "status"]
            },
            "id": 1
        }
        await websocket.send(json.dumps(subscribe_msg))
        
        # Receive response
        response = await websocket.recv()
        print(f"WebSocket connected: {response}")
        
        # Wait for a few updates
        for _ in range(3):
            update = await websocket.recv()
            print(f"Update received: {update}")

asyncio.run(test_websocket())
```

### Run Integration Tests

If you have the test suite installed:

```bash
# Run all tests
python -m pytest tests/

# Run integration tests only
python -m pytest tests/integration/

# Run with verbose output
python -m pytest tests/ -v

# Run specific test
python -m pytest tests/integration/test_api.py::test_version_endpoint
```

---

## Troubleshooting

### Common Issues and Solutions

#### Issue: Server Won't Start

**Symptoms:**
- Service fails to start
- Error: "Address already in use"
- Error: "Permission denied"

**Solutions:**

1. **Check if port is already in use:**
   ```bash
   netstat -tuln | grep 7125
   lsof -i :7125
   ```

2. **Kill process using the port:**
   ```bash
   sudo kill -9 <PID>
   ```

3. **Use a different port:**
   ```json
   {
       "port": 7126
   }
   ```

4. **Check file permissions:**
   ```bash
   ls -la config/
   chmod 644 config/klipperplace.json
   ```

#### Issue: Moonraker Connection Failed

**Symptoms:**
- Error: "Connection refused"
- Error: "Timeout connecting to Moonraker"
- Health check shows `moonraker_connected: false`

**Solutions:**

1. **Verify Moonraker is running:**
   ```bash
   sudo systemctl status moonraker
   ```

2. **Check Moonraker logs:**
   ```bash
   sudo journalctl -u moonraker -f
   ```

3. **Test Moonraker API directly:**
   ```bash
   curl http://localhost:7125/server/info
   ```

4. **Verify Moonraker configuration:**
   ```bash
   cat /etc/moonraker.conf
   ```

5. **Check firewall settings:**
   ```bash
   sudo iptables -L -n | grep 7125
   ```

6. **Restart Moonraker:**
   ```bash
   sudo systemctl restart moonraker
   ```

#### Issue: Klipper Connection Failed

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
   sudo journalctl -u klipper -f
   ```

3. **Restart Klipper:**
   ```bash
   sudo systemctl restart klipper
   ```

4. **Check Klipper configuration:**
   ```bash
   cat /home/pi/printer_data/config/printer.cfg
   ```

5. **Verify MCU connection:**
   ```bash
   ls /dev/serial/by-id/
   ```

#### Issue: API Key Authentication Fails

**Symptoms:**
- 401 Unauthorized responses
- Error: "Invalid API key"
- Error: "Authentication required"

**Solutions:**

1. **Check if authentication is enabled:**
   ```bash
   grep api_key_enabled config/klipperplace.json
   ```

2. **Verify API key file exists:**
   ```bash
   ls -la config/api_keys.json
   ```

3. **Check API key permissions:**
   ```bash
   chmod 600 config/api_keys.json
   ```

4. **Create a new API key:**
   ```bash
   curl -X POST http://localhost:7125/api/v1/auth/keys \
     -H "Content-Type: application/json" \
     -d '{"name": "Test Key", "permissions": ["read", "write"]}'
   ```

5. **Test with correct header:**
   ```bash
   curl -H "X-API-Key: your-api-key" http://localhost:7125/api/v1/status
   ```

#### Issue: Commands Timeout

**Symptoms:**
- Error: "Command execution timeout"
- Commands hang indefinitely
- 504 Gateway Timeout errors

**Solutions:**

1. **Increase timeout in configuration:**
   ```json
   {
       "timeout": 60.0
   }
   ```

2. **Check Moonraker responsiveness:**
   ```bash
   time curl http://localhost:7125/printer/info
   ```

3. **Reduce command queue size:**
   ```json
   {
       "max_queue_size": 100
   }
   ```

4. **Check system resources:**
   ```bash
   top
   htop
   free -h
   ```

#### Issue: Safety Limits Triggering

**Symptoms:**
- Error: "Position out of bounds"
- Error: "Temperature exceeded"
- Error: "Feedrate out of bounds"

**Solutions:**

1. **Check current safety limits:**
   ```bash
   curl http://localhost:7125/api/v1/status | grep safety
   ```

2. **Update limits in configuration:**
   ```json
   {
       "safety_max_x_position": 400.0,
       "safety_max_feedrate": 50000.0
   }
   ```

3. **Verify machine dimensions:**
   ```bash
   curl http://localhost:7125/printer/objects?stepper_enable=1
   ```

4. **Home axes before movement:**
   ```bash
   curl -X POST http://localhost:7125/api/v1/motion/home
   ```

#### Issue: WebSocket Connection Drops

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

#### Issue: High CPU Usage

**Symptoms:**
- System becomes sluggish
- CPU usage > 80%
- Commands execute slowly

**Solutions:**

1. **Check CPU usage:**
   ```bash
   top -p $(pgrep -f src.api.server)
   ```

2. **Reduce polling frequency:**
   ```ini
   # In Moonraker configuration
   [gpio_monitor]
   poll_interval: 200
   ```

3. **Increase cache TTL:**
   ```json
   {
       "cache_default_ttl": 2.0
   }
   ```

4. **Reduce monitoring intervals:**
   ```json
   {
       "safety_temperature_check_interval": 2.0,
       "safety_position_check_interval": 1.0
   }
   ```

### Debug Mode

Enable debug logging for troubleshooting:

```bash
# Set log level to DEBUG
export LOG_LEVEL=DEBUG

# Or in configuration
cat > config/klipperplace.json << EOF
{
    "log_level": "DEBUG",
    "log_format": "detailed"
}
EOF

# Restart server
sudo systemctl restart klipperplace

# View logs
tail -f logs/klipperplace.log
```

### Getting Help

If you encounter issues not covered here:

1. **Check Logs:**
   ```bash
   # KlipperPlace logs
   tail -f logs/klipperplace.log
   
   # Systemd service logs
   sudo journalctl -u klipperplace -f
   
   # Moonraker logs
   sudo journalctl -u moonraker -f
   
   # Klipper logs
   sudo journalctl -u klipper -f
   ```

2. **Verify Configuration:**
   ```bash
   # Validate JSON syntax
   python3 -m json.tool config/klipperplace.json
   
   # Check Moonraker config
   python3 -m configparser /etc/moonraker.conf
   ```

3. **Test Components Individually:**
   ```bash
   # Test Moonraker
   curl http://localhost:7125/server/info
   
   # Test Klipper
   curl http://localhost:7125/printer/info
   
   # Test KlipperPlace
   curl http://localhost:7125/api/v1/version
   ```

4. **Consult Documentation:**
   - [Architecture Documentation](ARCHITECTURE.md)
   - [API Reference](API_REFERENCE.md)
   - [Configuration Guide](CONFIGURATION.md)
   - [Testing Guide](TESTING.md)

5. **Report Issues:**
   - GitHub Issues: https://github.com/klipperplace/KlipperPlace/issues
   - Include:
     - Configuration files (with sensitive data removed)
     - Error messages
     - System information (OS, Python version)
     - Steps to reproduce

---

## Advanced Setup

### Running Behind a Reverse Proxy

Configure Nginx as a reverse proxy:

```bash
# Install Nginx
sudo apt install nginx

# Create configuration
sudo tee /etc/nginx/sites-available/klipperplace << 'EOF'
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:7125;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }

    location /ws/ {
        proxy_pass http://localhost:7125/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/klipperplace /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

### Enabling HTTPS with Let's Encrypt

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal is configured automatically
sudo certbot renew --dry-run
```

### Running Multiple Instances

Run multiple KlipperPlace instances for different machines:

```bash
# Create separate configuration files
cp config/klipperplace.json config/klipperplace_machine1.json
cp config/klipperplace.json config/klipperplace_machine2.json

# Modify ports in each config
# machine1: port 7125
# machine2: port 7126

# Create systemd services
sudo tee /etc/systemd/system/klipperplace-machine1.service << 'EOF'
[Unit]
Description=KlipperPlace Machine 1
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/KlipperPlace
ExecStart=/home/pi/KlipperPlace/venv/bin/python -m src.api.server --config config/klipperplace_machine1.json
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Repeat for machine2 with different port
sudo systemctl enable klipperplace-machine1
sudo systemctl enable klipperplace-machine2
sudo systemctl start klipperplace-machine1
sudo systemctl start klipperplace-machine2
```

### Monitoring with Prometheus

Add Prometheus metrics endpoint:

```bash
# Install dependencies
pip install prometheus-client

# Modify server to expose metrics
# Add to src/api/server.py:
from prometheus_client import start_http_server, Counter, Histogram

# Start metrics server on separate port
start_http_server(9090)

# Access metrics
curl http://localhost:9090/metrics
```

### Log Rotation

Configure log rotation to prevent disk space issues:

```bash
# Create logrotate configuration
sudo tee /etc/logrotate.d/klipperplace << 'EOF'
/home/pi/KlipperPlace/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 pi pi
    sharedscripts
    postrotate
        systemctl reload klipperplace > /dev/null 2>&1 || true
    endscript
}
EOF

# Test logrotate
sudo logrotate -f /etc/logrotate.d/klipperplace
```

### Backup and Restore

Create backup script:

```bash
#!/bin/bash
# backup-klipperplace.sh

BACKUP_DIR="/home/pi/backups/klipperplace"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup configuration
tar -czf $BACKUP_DIR/config_$DATE.tar.gz config/

# Backup logs (last 7 days)
find logs/ -name "*.log" -mtime -7 -exec tar -czf $BACKUP_DIR/logs_$DATE.tar.gz {} +

# Keep last 30 backups
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

**Restore from backup:**

```bash
# Restore configuration
tar -xzf /home/pi/backups/klipperplace/config_20240113_120000.tar.gz -C /

# Restart services
sudo systemctl restart klipperplace
```

---

## API Key Management

### Creating API Keys

Create a new API key:

```bash
curl -X POST http://localhost:7125/api/v1/auth/keys \
  -H "Content-Type: application/json" \
  -d '{
    "name": "OpenPNP Client",
    "permissions": ["read", "write"],
    "rate_limit": 50,
    "description": "API key for OpenPNP integration"
  }'
```

**Response:**
```json
{
  "key_id": "abc123def456",
  "api_key": "kp_abc123def4567890123456789012345678901234",
  "name": "OpenPNP Client",
  "permissions": ["read", "write"],
  "rate_limit": 50,
  "created_at": 1640000000.0
}
```

**Important:** Store the API key securely. You won't be able to retrieve it again.

### Listing API Keys

List all API keys:

```bash
curl -X GET http://localhost:7125/api/v1/auth/keys \
  -H "X-API-Key: your-admin-key"
```

### Updating API Keys

Update an existing API key:

```bash
curl -X PUT http://localhost:7125/api/v1/auth/keys/abc123def456 \
  -H "X-API-Key: your-admin-key" \
  -H "Content-Type: application/json" \
  -d '{
    "rate_limit": 100,
    "is_active": true
  }'
```

### Deleting API Keys

Delete an API key:

```bash
curl -X DELETE http://localhost:7125/api/v1/auth/keys/abc123def456 \
  -H "X-API-Key: your-admin-key"
```

---

## Uninstallation

### Remove Systemd Service

```bash
# Stop service
sudo systemctl stop klipperplace

# Disable service
sudo systemctl disable klipperplace

# Remove service file
sudo rm /etc/systemd/system/klipperplace.service

# Reload systemd
sudo systemctl daemon-reload
```

### Remove Supervisor Service (if used)

```bash
# Stop service
sudo supervisorctl stop klipperplace

# Remove service
sudo rm /etc/supervisor/conf.d/klipperplace.conf

# Update Supervisor
sudo supervisorctl update
```

### Remove Files

```bash
# Remove project directory
cd ~
rm -rf KlipperPlace

# Remove virtual environment (if created separately)
rm -rf ~/klipperplace-venv
```

### Remove Dependencies (Optional)

```bash
# Deactivate virtual environment first
deactivate

# Remove Python packages
pip uninstall -y aiohttp aiohttp-cors websockets python-dotenv pydantic

# Remove virtual environment
rm -rf venv
```

### Remove Configuration Files

```bash
# Remove Moonraker extensions from config
sudo nano /etc/moonraker.conf
# Remove [gpio_monitor], [fan_control], [pwm_control], [sensor_query] sections

# Restart Moonraker
sudo systemctl restart moonraker
```

---

## Additional Resources

### Documentation

- [Architecture Documentation](ARCHITECTURE.md) - System architecture overview
- [API Reference](API_REFERENCE.md) - Complete API documentation
- [Configuration Guide](CONFIGURATION.md) - Detailed configuration options
- [Testing Guide](TESTING.md) - Testing procedures and examples

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

## Checklist

Use this checklist to verify your installation:

- [ ] Python 3.8+ installed
- [ ] Klipper installed and running
- [ ] Moonraker installed and running
- [ ] KlipperPlace repository cloned
- [ ] Python dependencies installed
- [ ] Configuration files created
- [ ] Moonraker extensions configured
- [ ] Klipper PnP configuration added
- [ ] API server started
- [ ] Systemd service enabled (production)
- [ ] Health check passing
- [ ] API version endpoint working
- [ ] Status endpoint working
- [ ] Movement commands working
- [ ] Vacuum control working
- [ ] OpenPNP driver configured
- [ ] OpenPNP integration tested
- [ ] Log rotation configured (production)
- [ ] Backup strategy in place (production)

---

**Document Version**: 1.0.0  
**Last Updated**: 2024-01-14  
**Maintained By**: KlipperPlace Development Team
