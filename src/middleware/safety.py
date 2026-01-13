#!/usr/bin/env python3
# Safety Mechanisms Module for KlipperPlace Middleware
# Provides hardware protection, bounds checking, emergency stop, and safety monitoring

import logging
import asyncio
import time
import json
from typing import Dict, Any, Optional, List, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import aiohttp

# Import from cache module
from middleware.cache import StateCacheManager, CacheCategory

# Component logging
logger = logging.getLogger(__name__)


class SafetyLevel(Enum):
    """Safety level for different operations."""
    NORMAL = "normal"
    CAUTION = "caution"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class SafetyEventType(Enum):
    """Types of safety events."""
    TEMPERATURE_EXCEEDED = "temperature_exceeded"
    POSITION_LIMIT_EXCEEDED = "position_limit_exceeded"
    PWM_LIMIT_EXCEEDED = "pwm_limit_exceeded"
    EMERGENCY_STOP = "emergency_stop"
    HOMING_REQUIRED = "homing_required"
    STATE_CHANGE = "state_change"
    BOUNDS_VIOLATION = "bounds_violation"
    HARDWARE_FAULT = "hardware_fault"


@dataclass
class SafetyEvent:
    """Represents a safety event."""
    
    event_type: SafetyEventType
    level: SafetyLevel
    timestamp: float = field(default_factory=time.time)
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    component: str = ""
    resolved: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            'event_type': self.event_type.value,
            'level': self.level.value,
            'timestamp': self.timestamp,
            'message': self.message,
            'details': self.details,
            'component': self.component,
            'resolved': self.resolved
        }


@dataclass
class SafetyLimits:
    """Configurable safety limits."""
    
    # Temperature limits (in Celsius)
    max_extruder_temp: float = 250.0
    max_bed_temp: float = 120.0
    max_chamber_temp: float = 60.0
    min_temp_delta: float = 5.0  # Minimum delta between target and current
    
    # Position limits (in mm)
    max_x_position: float = 300.0
    max_y_position: float = 300.0
    max_z_position: float = 400.0
    min_x_position: float = 0.0
    min_y_position: float = 0.0
    min_z_position: float = 0.0
    
    # Velocity limits (in mm/s)
    max_velocity: float = 500.0
    max_acceleration: float = 3000.0
    
    # PWM limits (0.0 to 1.0)
    max_pwm_value: float = 1.0
    min_pwm_value: float = 0.0
    
    # Fan limits (0.0 to 1.0)
    max_fan_speed: float = 1.0
    min_fan_speed: float = 0.0
    
    # Feedrate limits (in mm/min)
    max_feedrate: float = 30000.0
    min_feedrate: float = 1.0
    
    # Emergency stop timeout (in seconds)
    emergency_stop_timeout: float = 5.0
    
    # Monitoring intervals (in seconds)
    temperature_check_interval: float = 1.0
    position_check_interval: float = 0.5
    state_check_interval: float = 2.0


@dataclass
class SafetyStatistics:
    """Statistics for safety monitoring."""
    
    total_events: int = 0
    emergency_stops: int = 0
    temperature_violations: int = 0
    position_violations: int = 0
    pwm_violations: int = 0
    bounds_violations: int = 0
    state_changes_logged: int = 0
    last_emergency_stop: Optional[float] = None
    last_violation: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert statistics to dictionary."""
        return {
            'total_events': self.total_events,
            'emergency_stops': self.emergency_stops,
            'temperature_violations': self.temperature_violations,
            'position_violations': self.position_violations,
            'pwm_violations': self.pwm_violations,
            'bounds_violations': self.bounds_violations,
            'state_changes_logged': self.state_changes_logged,
            'last_emergency_stop': self.last_emergency_stop,
            'last_violation': self.last_violation
        }


class SafetyManager:
    """Manages safety mechanisms for KlipperPlace middleware."""
    
    def __init__(self,
                 moonraker_host: str = 'localhost',
                 moonraker_port: int = 7125,
                 moonraker_api_key: Optional[str] = None,
                 cache_manager: Optional[StateCacheManager] = None,
                 safety_limits: Optional[SafetyLimits] = None):
        """Initialize safety manager.
        
        Args:
            moonraker_host: Moonraker host address
            moonraker_port: Moonraker port
            moonraker_api_key: Optional Moonraker API key
            cache_manager: Optional state cache manager
            safety_limits: Optional custom safety limits
        """
        self.moonraker_host = moonraker_host
        self.moonraker_port = moonraker_port
        self.moonraker_api_key = moonraker_api_key
        self.base_url = f"http://{moonraker_host}:{moonraker_port}"
        
        # Cache manager
        self.cache_manager = cache_manager
        
        # Safety limits
        self.limits = safety_limits or SafetyLimits()
        
        # Event history
        self._event_history: List[SafetyEvent] = []
        self._max_history_size = 1000
        
        # Statistics
        self._stats = SafetyStatistics()
        
        # State tracking
        self._current_position = {'x': 0.0, 'y': 0.0, 'z': 0.0}
        self._current_temperatures = {}
        self._homed_axes = set()
        self._emergency_stop_active = False
        
        # Monitoring tasks
        self._temperature_monitor_task: Optional[asyncio.Task] = None
        self._position_monitor_task: Optional[asyncio.Task] = None
        self._state_monitor_task: Optional[asyncio.Task] = None
        
        # Callbacks for safety events
        self._event_callbacks: List[Callable[[SafetyEvent], None]] = []
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        
        # Running state
        self._running = False
        
        logger.info("Safety manager initialized")
    
    async def start(self) -> None:
        """Start safety monitoring."""
        if self._running:
            logger.warning("Safety manager is already running")
            return
        
        self._running = True
        
        # Start monitoring tasks
        self._temperature_monitor_task = asyncio.create_task(
            self._temperature_monitor_loop()
        )
        self._position_monitor_task = asyncio.create_task(
            self._position_monitor_loop()
        )
        self._state_monitor_task = asyncio.create_task(
            self._state_monitor_loop()
        )
        
        logger.info("Safety manager started")
    
    async def stop(self) -> None:
        """Stop safety monitoring."""
        if not self._running:
            return
        
        self._running = False
        
        # Cancel monitoring tasks
        for task in [self._temperature_monitor_task, 
                   self._position_monitor_task,
                   self._state_monitor_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        logger.info("Safety manager stopped")
    
    # Hardware protection mechanisms
    
    async def check_temperature_limits(self) -> List[SafetyEvent]:
        """Check if any temperature limits are exceeded.
        
        Returns:
            List of safety events for violations
        """
        events = []
        
        try:
            # Fetch temperature data from cache or Moonraker
            if self.cache_manager:
                temp_data = await self.cache_manager.get(
                    'sensor:all',
                    category=CacheCategory.SENSOR
                )
            else:
                temp_data = await self._fetch_temperature_data()
            
            if temp_data and temp_data.get('success'):
                sensors = temp_data.get('sensors', {})
                
                # Check extruder temperatures
                for sensor_name, sensor_data in sensors.items():
                    if 'extruder' in sensor_name.lower() or 'heater' in sensor_name.lower():
                        current_temp = sensor_data.get('temperature', 0.0)
                        target_temp = sensor_data.get('target', 0.0)
                        
                        # Check max temperature
                        max_limit = self.limits.max_extruder_temp
                        if current_temp > max_limit:
                            event = SafetyEvent(
                                event_type=SafetyEventType.TEMPERATURE_EXCEEDED,
                                level=SafetyLevel.CRITICAL,
                                message=f"Extruder temperature exceeded: {current_temp}°C > {max_limit}°C",
                                details={
                                    'sensor': sensor_name,
                                    'current_temp': current_temp,
                                    'max_limit': max_limit
                                },
                                component=sensor_name
                            )
                            events.append(event)
                            await self._handle_safety_event(event)
                        
                        # Check temperature delta
                        if target_temp > 0 and abs(current_temp - target_temp) > 50.0:
                            event = SafetyEvent(
                                event_type=SafetyEventType.TEMPERATURE_EXCEEDED,
                                level=SafetyLevel.WARNING,
                                message=f"Large temperature delta detected: {abs(current_temp - target_temp)}°C",
                                details={
                                    'sensor': sensor_name,
                                    'current_temp': current_temp,
                                    'target_temp': target_temp,
                                    'delta': abs(current_temp - target_temp)
                                },
                                component=sensor_name
                            )
                            events.append(event)
                            await self._handle_safety_event(event)
                
                # Check bed temperature
                for sensor_name, sensor_data in sensors.items():
                    if 'bed' in sensor_name.lower():
                        current_temp = sensor_data.get('temperature', 0.0)
                        max_limit = self.limits.max_bed_temp
                        
                        if current_temp > max_limit:
                            event = SafetyEvent(
                                event_type=SafetyEventType.TEMPERATURE_EXCEEDED,
                                level=SafetyLevel.CRITICAL,
                                message=f"Bed temperature exceeded: {current_temp}°C > {max_limit}°C",
                                details={
                                    'sensor': sensor_name,
                                    'current_temp': current_temp,
                                    'max_limit': max_limit
                                },
                                component=sensor_name
                            )
                            events.append(event)
                            await self._handle_safety_event(event)
                
                # Update cached temperatures
                self._current_temperatures = sensors
        
        except Exception as e:
            logger.error(f"Error checking temperature limits: {e}")
        
        return events
    
    async def check_position_limits(self, position: Optional[Dict[str, float]] = None) -> List[SafetyEvent]:
        """Check if position limits are exceeded.
        
        Args:
            position: Optional position dictionary to check (uses current if not provided)
            
        Returns:
            List of safety events for violations
        """
        events = []
        
        try:
            # Use provided position or fetch current
            if position is None:
                if self.cache_manager:
                    pos_data = await self.cache_manager.get(
                        'position',
                        category=CacheCategory.POSITION
                    )
                    if pos_data and pos_data.get('success'):
                        pos_info = pos_data.get('position', {})
                        position = pos_info.get('position', {'x': 0.0, 'y': 0.0, 'z': 0.0})
                else:
                    position = await self._fetch_position_data()
            
            if position:
                # Check X axis
                x = position.get('x', 0.0)
                if x < self.limits.min_x_position or x > self.limits.max_x_position:
                    event = SafetyEvent(
                        event_type=SafetyEventType.POSITION_LIMIT_EXCEEDED,
                        level=SafetyLevel.CRITICAL,
                        message=f"X position out of bounds: {x} mm",
                        details={
                            'axis': 'x',
                            'position': x,
                            'min_limit': self.limits.min_x_position,
                            'max_limit': self.limits.max_x_position
                        },
                        component='axis_x'
                    )
                    events.append(event)
                    await self._handle_safety_event(event)
                
                # Check Y axis
                y = position.get('y', 0.0)
                if y < self.limits.min_y_position or y > self.limits.max_y_position:
                    event = SafetyEvent(
                        event_type=SafetyEventType.POSITION_LIMIT_EXCEEDED,
                        level=SafetyLevel.CRITICAL,
                        message=f"Y position out of bounds: {y} mm",
                        details={
                            'axis': 'y',
                            'position': y,
                            'min_limit': self.limits.min_y_position,
                            'max_limit': self.limits.max_y_position
                        },
                        component='axis_y'
                    )
                    events.append(event)
                    await self._handle_safety_event(event)
                
                # Check Z axis
                z = position.get('z', 0.0)
                if z < self.limits.min_z_position or z > self.limits.max_z_position:
                    event = SafetyEvent(
                        event_type=SafetyEventType.POSITION_LIMIT_EXCEEDED,
                        level=SafetyLevel.CRITICAL,
                        message=f"Z position out of bounds: {z} mm",
                        details={
                            'axis': 'z',
                            'position': z,
                            'min_limit': self.limits.min_z_position,
                            'max_limit': self.limits.max_z_position
                        },
                        component='axis_z'
                    )
                    events.append(event)
                    await self._handle_safety_event(event)
                
                # Update cached position
                self._current_position = position
        
        except Exception as e:
            logger.error(f"Error checking position limits: {e}")
        
        return events
    
    async def check_pwm_limits(self, pin_name: str, value: float) -> Optional[SafetyEvent]:
        """Check if PWM value is within limits.
        
        Args:
            pin_name: PWM pin name
            value: PWM value to check
            
        Returns:
            Safety event if limit exceeded, None otherwise
        """
        try:
            if value < self.limits.min_pwm_value or value > self.limits.max_pwm_value:
                event = SafetyEvent(
                    event_type=SafetyEventType.PWM_LIMIT_EXCEEDED,
                    level=SafetyLevel.WARNING,
                    message=f"PWM value out of bounds: {value}",
                    details={
                        'pin': pin_name,
                        'value': value,
                        'min_limit': self.limits.min_pwm_value,
                        'max_limit': self.limits.max_pwm_value
                    },
                    component=pin_name
                )
                await self._handle_safety_event(event)
                return event
        
        except Exception as e:
            logger.error(f"Error checking PWM limits: {e}")
        
        return None
    
    # Bounds checking for control inputs
    
    async def validate_move_command(self, x: Optional[float] = None,
                                 y: Optional[float] = None,
                                 z: Optional[float] = None,
                                 feedrate: Optional[float] = None) -> Tuple[bool, List[str]]:
        """Validate a move command parameters.
        
        Args:
            x: X coordinate
            y: Y coordinate
            z: Z coordinate
            feedrate: Feedrate in mm/min
            
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        # Check position bounds
        if x is not None:
            if x < self.limits.min_x_position or x > self.limits.max_x_position:
                errors.append(f"X position {x} mm out of bounds [{self.limits.min_x_position}, {self.limits.max_x_position}]")
        
        if y is not None:
            if y < self.limits.min_y_position or y > self.limits.max_y_position:
                errors.append(f"Y position {y} mm out of bounds [{self.limits.min_y_position}, {self.limits.max_y_position}]")
        
        if z is not None:
            if z < self.limits.min_z_position or z > self.limits.max_z_position:
                errors.append(f"Z position {z} mm out of bounds [{self.limits.min_z_position}, {self.limits.max_z_position}]")
        
        # Check feedrate bounds
        if feedrate is not None:
            if feedrate < self.limits.min_feedrate or feedrate > self.limits.max_feedrate:
                errors.append(f"Feedrate {feedrate} mm/min out of bounds [{self.limits.min_feedrate}, {self.limits.max_feedrate}]")
        
        # Log bounds violation if errors found
        if errors:
            event = SafetyEvent(
                event_type=SafetyEventType.BOUNDS_VIOLATION,
                level=SafetyLevel.WARNING,
                message=f"Move command bounds violation: {', '.join(errors)}",
                details={
                    'x': x,
                    'y': y,
                    'z': z,
                    'feedrate': feedrate,
                    'errors': errors
                },
                component='move_validator'
            )
            await self._handle_safety_event(event)
        
        return (len(errors) == 0, errors)
    
    async def validate_temperature_command(self, heater: str, target_temp: float) -> Tuple[bool, str]:
        """Validate a temperature command.
        
        Args:
            heater: Heater name
            target_temp: Target temperature in Celsius
            
        Returns:
            Tuple of (is_valid, error message)
        """
        # Determine max temperature based on heater type
        if 'extruder' in heater.lower() or 'heater' in heater.lower():
            max_temp = self.limits.max_extruder_temp
        elif 'bed' in heater.lower():
            max_temp = self.limits.max_bed_temp
        elif 'chamber' in heater.lower():
            max_temp = self.limits.max_chamber_temp
        else:
            max_temp = self.limits.max_extruder_temp  # Default
        
        # Check bounds
        if target_temp < 0 or target_temp > max_temp:
            error = f"Temperature {target_temp}°C out of bounds [0, {max_temp}] for {heater}"
            event = SafetyEvent(
                event_type=SafetyEventType.BOUNDS_VIOLATION,
                level=SafetyLevel.WARNING,
                message=error,
                details={
                    'heater': heater,
                    'target_temp': target_temp,
                    'max_temp': max_temp
                },
                component=heater
            )
            await self._handle_safety_event(event)
            return (False, error)
        
        return (True, "")
    
    async def validate_fan_command(self, fan_name: str, speed: float) -> Tuple[bool, str]:
        """Validate a fan command.
        
        Args:
            fan_name: Fan name
            speed: Fan speed (0.0 to 1.0)
            
        Returns:
            Tuple of (is_valid, error message)
        """
        if speed < self.limits.min_fan_speed or speed > self.limits.max_fan_speed:
            error = f"Fan speed {speed} out of bounds [{self.limits.min_fan_speed}, {self.limits.max_fan_speed}] for {fan_name}"
            event = SafetyEvent(
                event_type=SafetyEventType.BOUNDS_VIOLATION,
                level=SafetyLevel.WARNING,
                message=error,
                details={
                    'fan': fan_name,
                    'speed': speed,
                    'min_speed': self.limits.min_fan_speed,
                    'max_speed': self.limits.max_fan_speed
                },
                component=fan_name
            )
            await self._handle_safety_event(event)
            return (False, error)
        
        return (True, "")
    
    # Emergency stop functionality
    
    async def emergency_stop(self, reason: str = "Manual emergency stop") -> SafetyEvent:
        """Execute emergency stop.
        
        Args:
            reason: Reason for emergency stop
            
        Returns:
            Safety event for the emergency stop
        """
        logger.warning(f"Emergency stop triggered: {reason}")
        
        # Mark emergency stop as active
        self._emergency_stop_active = True
        
        # Create safety event
        event = SafetyEvent(
            event_type=SafetyEventType.EMERGENCY_STOP,
            level=SafetyLevel.EMERGENCY,
            message=f"Emergency stop: {reason}",
            details={'reason': reason},
            component='system'
        )
        
        try:
            # Send M112 command to Klipper
            async with aiohttp.ClientSession() as session:
                headers = {}
                if self.moonraker_api_key:
                    headers['X-Api-Key'] = self.moonraker_api_key
                
                url = f"{self.base_url}/api/printer/gcode/script"
                payload = {'script': 'M112'}
                
                async with session.post(url, headers=headers, json=payload) as response:
                    data = await response.json()
                    
                    if data.get('result'):
                        logger.info("Emergency stop command sent successfully")
                    else:
                        logger.error(f"Failed to send emergency stop: {data}")
            
            # Update statistics
            self._stats.emergency_stops += 1
            self._stats.last_emergency_stop = time.time()
            
            # Invalidate cache
            if self.cache_manager:
                await self.cache_manager.invalidate_category(CacheCategory.POSITION)
                await self.cache_manager.invalidate_category(CacheCategory.GPIO)
                await self.cache_manager.invalidate_category(CacheCategory.PWM)
                await self.cache_manager.invalidate_category(CacheCategory.FAN)
            
        except Exception as e:
            logger.error(f"Error executing emergency stop: {e}")
            event.message += f" (Error: {str(e)})"
        
        # Record event
        await self._handle_safety_event(event)
        
        return event
    
    def is_emergency_stop_active(self) -> bool:
        """Check if emergency stop is currently active.
        
        Returns:
            True if emergency stop is active
        """
        return self._emergency_stop_active
    
    def clear_emergency_stop(self) -> None:
        """Clear emergency stop state (after recovery)."""
        self._emergency_stop_active = False
        logger.info("Emergency stop state cleared")
    
    # State change logging
    
    async def log_state_change(self, component: str, old_state: Any, 
                            new_state: Any, details: Optional[Dict[str, Any]] = None) -> SafetyEvent:
        """Log a state change for safety monitoring.
        
        Args:
            component: Component name
            old_state: Previous state
            new_state: New state
            details: Optional additional details
            
        Returns:
            Safety event for the state change
        """
        event = SafetyEvent(
            event_type=SafetyEventType.STATE_CHANGE,
            level=SafetyLevel.NORMAL,
            message=f"State change: {component}",
            details={
                'old_state': old_state,
                'new_state': new_state,
                **(details or {})
            },
            component=component
        )
        
        # Record event
        await self._handle_safety_event(event)
        
        # Update statistics
        self._stats.state_changes_logged += 1
        
        logger.debug(f"State change logged: {component} - {old_state} -> {new_state}")
        
        return event
    
    # Position limits and homing safety
    
    async def check_homing_required(self, axes: Optional[List[str]] = None) -> bool:
        """Check if homing is required for specified axes.
        
        Args:
            axes: List of axes to check (checks all if not provided)
            
        Returns:
            True if homing is required
        """
        if axes is None:
            axes = ['x', 'y', 'z']
        
        for axis in axes:
            if axis.lower() not in self._homed_axes:
                event = SafetyEvent(
                    event_type=SafetyEventType.HOMING_REQUIRED,
                    level=SafetyLevel.WARNING,
                    message=f"Homing required for {axis.upper()} axis",
                    details={'axis': axis, 'homed_axes': list(self._homed_axes)},
                    component=f'axis_{axis}'
                )
                await self._handle_safety_event(event)
                return True
        
        return False
    
    async def mark_axis_homed(self, axis: str) -> None:
        """Mark an axis as homed.
        
        Args:
            axis: Axis name (x, y, or z)
        """
        self._homed_axes.add(axis.lower())
        logger.info(f"Axis {axis.upper()} marked as homed")
    
    async def mark_axes_unhomed(self, axes: Optional[List[str]] = None) -> None:
        """Mark axes as not homed.
        
        Args:
            axes: List of axes to mark (clears all if not provided)
        """
        if axes is None:
            self._homed_axes.clear()
            logger.info("All axes marked as not homed")
        else:
            for axis in axes:
                self._homed_axes.discard(axis.lower())
                logger.info(f"Axis {axis.upper()} marked as not homed")
    
    def get_homed_axes(self) -> List[str]:
        """Get list of homed axes.
        
        Returns:
            List of homed axis names
        """
        return list(self._homed_axes)
    
    # Monitoring loops
    
    async def _temperature_monitor_loop(self) -> None:
        """Background loop for temperature monitoring."""
        while self._running:
            try:
                await asyncio.sleep(self.limits.temperature_check_interval)
                await self.check_temperature_limits()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in temperature monitor loop: {e}")
    
    async def _position_monitor_loop(self) -> None:
        """Background loop for position monitoring."""
        while self._running:
            try:
                await asyncio.sleep(self.limits.position_check_interval)
                await self.check_position_limits()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in position monitor loop: {e}")
    
    async def _state_monitor_loop(self) -> None:
        """Background loop for state monitoring."""
        while self._running:
            try:
                await asyncio.sleep(self.limits.state_check_interval)
                
                # Check if emergency stop is still active
                if self._emergency_stop_active:
                    logger.warning("Emergency stop still active - waiting for recovery")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in state monitor loop: {e}")
    
    # Event handling
    
    async def _handle_safety_event(self, event: SafetyEvent) -> None:
        """Handle a safety event.
        
        Args:
            event: Safety event to handle
        """
        async with self._lock:
            # Add to history
            self._event_history.append(event)
            
            # Trim history if needed
            if len(self._event_history) > self._max_history_size:
                self._event_history = self._event_history[-self._max_history_size:]
            
            # Update statistics
            self._stats.total_events += 1
            self._stats.last_violation = time.time()
            
            if event.event_type == SafetyEventType.TEMPERATURE_EXCEEDED:
                self._stats.temperature_violations += 1
            elif event.event_type == SafetyEventType.POSITION_LIMIT_EXCEEDED:
                self._stats.position_violations += 1
            elif event.event_type == SafetyEventType.PWM_LIMIT_EXCEEDED:
                self._stats.pwm_violations += 1
            elif event.event_type == SafetyEventType.BOUNDS_VIOLATION:
                self._stats.bounds_violations += 1
            
            # Log event
            log_level = logging.ERROR if event.level in [SafetyLevel.CRITICAL, SafetyLevel.EMERGENCY] else logging.WARNING
            logger.log(log_level, f"Safety event: {event.message}")
            
            # Notify callbacks
            for callback in self._event_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                except Exception as e:
                    logger.error(f"Error in safety event callback: {e}")
    
    def add_event_callback(self, callback: Callable[[SafetyEvent], None]) -> None:
        """Add a callback for safety events.
        
        Args:
            callback: Callback function
        """
        self._event_callbacks.append(callback)
        logger.info("Safety event callback added")
    
    def remove_event_callback(self, callback: Callable[[SafetyEvent], None]) -> None:
        """Remove a safety event callback.
        
        Args:
            callback: Callback function to remove
        """
        if callback in self._event_callbacks:
            self._event_callbacks.remove(callback)
            logger.info("Safety event callback removed")
    
    # Data fetching helpers
    
    async def _fetch_temperature_data(self) -> Optional[Dict[str, Any]]:
        """Fetch temperature data from Moonraker.
        
        Returns:
            Temperature data dictionary
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {}
                if self.moonraker_api_key:
                    headers['X-Api-Key'] = self.moonraker_api_key
                
                url = f"{self.base_url}/api/printer/query"
                payload = {'objects': {'heaters': None, 'temperature_sensor': None}}
                
                async with session.post(url, headers=headers, json=payload) as response:
                    data = await response.json()
                    
                    if data.get('result'):
                        return {
                            'success': True,
                            'sensors': data['result']
                        }
                    
                    return None
        except Exception as e:
            logger.error(f"Error fetching temperature data: {e}")
            return None
    
    async def _fetch_position_data(self) -> Optional[Dict[str, float]]:
        """Fetch position data from Moonraker.
        
        Returns:
            Position dictionary
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {}
                if self.moonraker_api_key:
                    headers['X-Api-Key'] = self.moonraker_api_key
                
                url = f"{self.base_url}/api/printer/query"
                payload = {'objects': {'toolhead': None}}
                
                async with session.post(url, headers=headers, json=payload) as response:
                    data = await response.json()
                    
                    if data.get('result'):
                        toolhead = data['result'].get('toolhead', {})
                        return toolhead.get('position', {'x': 0.0, 'y': 0.0, 'z': 0.0})
                    
                    return None
        except Exception as e:
            logger.error(f"Error fetching position data: {e}")
            return None
    
    # Public API
    
    async def get_event_history(self, limit: Optional[int] = None,
                             event_type: Optional[SafetyEventType] = None,
                             level: Optional[SafetyLevel] = None) -> List[SafetyEvent]:
        """Get safety event history.
        
        Args:
            limit: Maximum number of events to return
            event_type: Filter by event type
            level: Filter by safety level
            
        Returns:
            List of safety events
        """
        async with self._lock:
            events = self._event_history.copy()
            
            # Apply filters
            if event_type:
                events = [e for e in events if e.event_type == event_type]
            
            if level:
                events = [e for e in events if e.level == level]
            
            # Apply limit
            if limit:
                events = events[-limit:]
            
            return events
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get safety statistics.
        
        Returns:
            Dictionary containing safety statistics
        """
        async with self._lock:
            return self._stats.to_dict()
    
    async def get_current_limits(self) -> Dict[str, Any]:
        """Get current safety limits.
        
        Returns:
            Dictionary containing safety limits
        """
        return {
            'temperature': {
                'max_extruder_temp': self.limits.max_extruder_temp,
                'max_bed_temp': self.limits.max_bed_temp,
                'max_chamber_temp': self.limits.max_chamber_temp
            },
            'position': {
                'max_x': self.limits.max_x_position,
                'max_y': self.limits.max_y_position,
                'max_z': self.limits.max_z_position,
                'min_x': self.limits.min_x_position,
                'min_y': self.limits.min_y_position,
                'min_z': self.limits.min_z_position
            },
            'velocity': {
                'max_velocity': self.limits.max_velocity,
                'max_acceleration': self.limits.max_acceleration
            },
            'pwm': {
                'max_value': self.limits.max_pwm_value,
                'min_value': self.limits.min_pwm_value
            },
            'fan': {
                'max_speed': self.limits.max_fan_speed,
                'min_speed': self.limits.min_fan_speed
            },
            'feedrate': {
                'max': self.limits.max_feedrate,
                'min': self.limits.min_feedrate
            }
        }
    
    def update_limits(self, limits: Dict[str, Any]) -> None:
        """Update safety limits.
        
        Args:
            limits: Dictionary of limits to update
        """
        for key, value in limits.items():
            if hasattr(self.limits, key):
                setattr(self.limits, key, value)
                logger.info(f"Updated safety limit: {key} = {value}")
    
    async def clear_event_history(self) -> None:
        """Clear all safety event history."""
        async with self._lock:
            self._event_history.clear()
            logger.info("Safety event history cleared")
    
    async def resolve_event(self, event_index: int) -> bool:
        """Mark a safety event as resolved.
        
        Args:
            event_index: Index of event to resolve
            
        Returns:
            True if event was resolved
        """
        async with self._lock:
            if 0 <= event_index < len(self._event_history):
                self._event_history[event_index].resolved = True
                logger.info(f"Safety event {event_index} marked as resolved")
                return True
            return False
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current safety state.
        
        Returns:
            Dictionary containing current state
        """
        return {
            'position': self._current_position.copy(),
            'temperatures': self._current_temperatures.copy(),
            'homed_axes': list(self._homed_axes),
            'emergency_stop_active': self._emergency_stop_active,
            'running': self._running
        }


# Convenience functions

async def create_safety_manager(moonraker_host: str = 'localhost',
                              moonraker_port: int = 7125,
                              moonraker_api_key: Optional[str] = None,
                              cache_manager: Optional[StateCacheManager] = None,
                              safety_limits: Optional[SafetyLimits] = None,
                              auto_start: bool = True) -> SafetyManager:
    """Create and optionally start a safety manager.
    
    Args:
        moonraker_host: Moonraker host address
        moonraker_port: Moonraker port
        moonraker_api_key: Optional Moonraker API key
        cache_manager: Optional state cache manager
        safety_limits: Optional custom safety limits
        auto_start: Automatically start safety monitoring
        
    Returns:
        SafetyManager instance
    """
    safety_manager = SafetyManager(
        moonraker_host=moonraker_host,
        moonraker_port=moonraker_port,
        moonraker_api_key=moonraker_api_key,
        cache_manager=cache_manager,
        safety_limits=safety_limits
    )
    
    if auto_start:
        await safety_manager.start()
    
    return safety_manager
