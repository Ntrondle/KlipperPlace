#!/usr/bin/env python3
# Unit tests for Safety Manager

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from dataclasses import dataclass
from enum import Enum


# Mock classes for testing
class SafetyLevel(Enum):
    NORMAL = "normal"
    CAUTION = "caution"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class SafetyEventType(Enum):
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
    event_type: SafetyEventType
    level: SafetyLevel
    timestamp: float
    message: str
    details: dict
    component: str
    resolved: bool


@dataclass
class SafetyLimits:
    max_extruder_temp: float = 250.0
    max_bed_temp: float = 120.0
    max_chamber_temp: float = 60.0
    min_temp_delta: float = 5.0
    max_x_position: float = 300.0
    max_y_position: float = 300.0
    max_z_position: float = 400.0
    min_x_position: float = 0.0
    min_y_position: float = 0.0
    min_z_position: float = 0.0
    max_velocity: float = 500.0
    max_acceleration: float = 3000.0
    max_pwm_value: float = 1.0
    min_pwm_value: float = 0.0
    max_fan_speed: float = 1.0
    min_fan_speed: float = 0.0
    max_feedrate: float = 30000.0
    min_feedrate: float = 1.0
    emergency_stop_timeout: float = 5.0
    temperature_check_interval: float = 1.0
    position_check_interval: float = 0.5
    state_check_interval: float = 2.0


@dataclass
class SafetyStatistics:
    total_events: int
    emergency_stops: int
    temperature_violations: int
    position_violations: int
    pwm_violations: int
    bounds_violations: int
    state_changes_logged: int
    last_emergency_stop: float
    last_violation: float


# Import safety module classes
from middleware.safety import (
    SafetyManager,
    SafetyLimits,
    SafetyEvent,
    SafetyLevel,
    SafetyEventType,
    SafetyStatistics
)


@pytest.fixture
def mock_cache_manager():
    """Create a mock cache manager."""
    cache = Mock()
    cache.get = AsyncMock(return_value=None)
    cache.invalidate_category = AsyncMock()
    return cache


@pytest.fixture
def safety_manager(mock_cache_manager):
    """Create a SafetyManager instance for testing."""
    with patch('middleware.safety.aiohttp.ClientSession'):
        manager = SafetyManager(
            moonraker_host='localhost',
            moonraker_port=7125,
            moonraker_api_key='test_key',
            cache_manager=mock_cache_manager,
            auto_start=False  # Don't auto-start for testing
        )
        return manager


class TestSafetyEvent:
    """Test SafetyEvent dataclass."""
    
    def test_safety_event_creation(self):
        """Test creating a safety event."""
        event = SafetyEvent(
            event_type=SafetyEventType.TEMPERATURE_EXCEEDED,
            level=SafetyLevel.CRITICAL,
            timestamp=123456.789,
            message="Temperature exceeded",
            details={'temp': 260.0},
            component='extruder',
            resolved=False
        )
        
        assert event.event_type == SafetyEventType.TEMPERATURE_EXCEEDED
        assert event.level == SafetyLevel.CRITICAL
        assert event.timestamp == 123456.789
        assert event.message == "Temperature exceeded"
        assert event.details == {'temp': 260.0}
        assert event.component == 'extruder'
        assert event.resolved == False
    
    def test_safety_event_to_dict(self):
        """Test converting safety event to dictionary."""
        event = SafetyEvent(
            event_type=SafetyEventType.TEMPERATURE_EXCEEDED,
            level=SafetyLevel.CRITICAL,
            timestamp=123456.789,
            message="Temperature exceeded",
            details={'temp': 260.0},
            component='extruder'
        )
        
        result = event.to_dict()
        
        assert result['event_type'] == "temperature_exceeded"
        assert result['level'] == "critical"
        assert result['timestamp'] == 123456.789
        assert result['message'] == "Temperature exceeded"
        assert result['details'] == {'temp': 260.0}
        assert result['component'] == 'extruder'
        assert result['resolved'] == False


class TestSafetyLimits:
    """Test SafetyLimits dataclass."""
    
    def test_safety_limits_defaults(self):
        """Test creating safety limits with defaults."""
        limits = SafetyLimits()
        
        assert limits.max_extruder_temp == 250.0
        assert limits.max_bed_temp == 120.0
        assert limits.max_chamber_temp == 60.0
        assert limits.min_temp_delta == 5.0
        assert limits.max_x_position == 300.0
        assert limits.max_y_position == 300.0
        assert limits.max_z_position == 400.0
        assert limits.min_x_position == 0.0
        assert limits.min_y_position == 0.0
        assert limits.min_z_position == 0.0
        assert limits.max_velocity == 500.0
        assert limits.max_acceleration == 3000.0
        assert limits.max_pwm_value == 1.0
        assert limits.min_pwm_value == 0.0
        assert limits.max_fan_speed == 1.0
        assert limits.min_fan_speed == 0.0
        assert limits.max_feedrate == 30000.0
        assert limits.min_feedrate == 1.0
        assert limits.emergency_stop_timeout == 5.0
        assert limits.temperature_check_interval == 1.0
        assert limits.position_check_interval == 0.5
        assert limits.state_check_interval == 2.0
    
    def test_safety_limits_custom_values(self):
        """Test creating safety limits with custom values."""
        limits = SafetyLimits(
            max_extruder_temp=300.0,
            max_bed_temp=150.0,
            max_x_position=400.0,
            max_feedrate=40000.0
        )
        
        assert limits.max_extruder_temp == 300.0
        assert limits.max_bed_temp == 150.0
        assert limits.max_x_position == 400.0
        assert limits.max_feedrate == 40000.0


class TestSafetyStatistics:
    """Test SafetyStatistics dataclass."""
    
    def test_safety_statistics_defaults(self):
        """Test creating safety statistics with defaults."""
        stats = SafetyStatistics()
        
        assert stats.total_events == 0
        assert stats.emergency_stops == 0
        assert stats.temperature_violations == 0
        assert stats.position_violations == 0
        assert stats.pwm_violations == 0
        assert stats.bounds_violations == 0
        assert stats.state_changes_logged == 0
        assert stats.last_emergency_stop is None
        assert stats.last_violation is None
    
    def test_safety_statistics_custom_values(self):
        """Test creating safety statistics with custom values."""
        stats = SafetyStatistics(
            total_events=10,
            emergency_stops=2,
            temperature_violations=3,
            position_violations=1,
            pwm_violations=1,
            bounds_violations=2,
            state_changes_logged=5,
            last_emergency_stop=123456.789,
            last_violation=123457.0
        )
        
        assert stats.total_events == 10
        assert stats.emergency_stops == 2
        assert stats.temperature_violations == 3
        assert stats.position_violations == 1
        assert stats.pwm_violations == 1
        assert stats.bounds_violations == 2
        assert stats.state_changes_logged == 5
        assert stats.last_emergency_stop == 123456.789
        assert stats.last_violation == 123457.0
    
    def test_safety_statistics_to_dict(self):
        """Test converting safety statistics to dictionary."""
        stats = SafetyStatistics(
            total_events=10,
            emergency_stops=2,
            temperature_violations=3
        )
        
        result = stats.to_dict()
        
        assert result['total_events'] == 10
        assert result['emergency_stops'] == 2
        assert result['temperature_violations'] == 3
        assert result['last_emergency_stop'] is None
        assert result['last_violation'] is None


class TestSafetyManagerInitialization:
    """Test SafetyManager initialization."""
    
    def test_initialization_with_defaults(self, mock_cache_manager):
        """Test initialization with default configuration."""
        with patch('middleware.safety.aiohttp.ClientSession'):
            manager = SafetyManager(
                moonraker_host='localhost',
                moonraker_port=7125,
                cache_manager=mock_cache_manager,
                auto_start=False
            )
            
            assert manager.moonraker_host == 'localhost'
            assert manager.moonraker_port == 7125
            assert manager.moonraker_api_key == 'test_key'
            assert manager.cache_manager is not None
            assert manager.limits is not None
            assert len(manager._event_history) == 0
            assert len(manager._homed_axes) == 0
            assert manager._emergency_stop_active == False
    
    def test_initialization_with_custom_limits(self, mock_cache_manager):
        """Test initialization with custom safety limits."""
        custom_limits = SafetyLimits(
            max_extruder_temp=300.0,
            max_x_position=400.0
        )
        
        with patch('middleware.safety.aiohttp.ClientSession'):
            manager = SafetyManager(
                moonraker_host='localhost',
                moonraker_port=7125,
                cache_manager=mock_cache_manager,
                safety_limits=custom_limits,
                auto_start=False
            )
            
            assert manager.limits.max_extruder_temp == 300.0
            assert manager.limits.max_x_position == 400.0


class TestCheckTemperatureLimits:
    """Test temperature limit checking."""
    
    @pytest.mark.asyncio
    async def test_check_temperature_normal(self, safety_manager, mock_cache_manager):
        """Test checking temperature within limits."""
        mock_cache_manager.get = AsyncMock(return_value={
            'success': True,
            'sensors': {
                'extruder': {
                    'temperature': 200.0,
                    'target': 210.0
                }
            }
        })
        
        events = await safety_manager.check_temperature_limits()
        
        # Should not generate any events
        assert len(events) == 0
    
    @pytest.mark.asyncio
    async def test_check_temperature_exceeded(self, safety_manager, mock_cache_manager):
        """Test checking exceeded temperature."""
        mock_cache_manager.get = AsyncMock(return_value={
            'success': True,
            'sensors': {
                'extruder': {
                    'temperature': 260.0,
                    'target': 210.0
                }
            }
        })
        
        events = await safety_manager.check_temperature_limits()
        
        # Should generate one event
        assert len(events) == 1
        assert events[0].event_type == SafetyEventType.TEMPERATURE_EXCEEDED
        assert events[0].level == SafetyLevel.CRITICAL
        assert 'exceeded' in events[0].message.lower()
    
    @pytest.mark.asyncio
    async def test_check_temperature_large_delta(self, safety_manager, mock_cache_manager):
        """Test checking large temperature delta."""
        mock_cache_manager.get = AsyncMock(return_value={
            'success': True,
            'sensors': {
                'extruder': {
                    'temperature': 200.0,
                    'target': 260.0
                }
            }
        })
        
        events = await safety_manager.check_temperature_limits()
        
        # Should generate one event
        assert len(events) == 1
        assert events[0].event_type == SafetyEventType.TEMPERATURE_EXCEEDED
        assert events[0].level == SafetyLevel.WARNING
        assert 'delta' in events[0].message.lower()
    
    @pytest.mark.asyncio
    async def test_check_temperature_bed_exceeded(self, safety_manager, mock_cache_manager):
        """Test checking exceeded bed temperature."""
        mock_cache_manager.get = AsyncMock(return_value={
            'success': True,
            'sensors': {
                'heater_bed': {
                    'temperature': 130.0,
                    'target': 100.0
                }
            }
        })
        
        events = await safety_manager.check_temperature_limits()
        
        # Should generate one event
        assert len(events) == 1
        assert 'bed' in events[0].component.lower()


class TestCheckPositionLimits:
    """Test position limit checking."""
    
    @pytest.mark.asyncio
    async def test_check_position_normal(self, safety_manager, mock_cache_manager):
        """Test checking position within limits."""
        mock_cache_manager.get = AsyncMock(return_value={
            'success': True,
            'position': {
                'position': {'x': 150.0, 'y': 150.0, 'z': 200.0}
            }
        })
        
        events = await safety_manager.check_position_limits()
        
        # Should not generate any events
        assert len(events) == 0
    
    @pytest.mark.asyncio
    async def test_check_position_x_exceeded(self, safety_manager, mock_cache_manager):
        """Test checking exceeded X position."""
        mock_cache_manager.get = AsyncMock(return_value={
            'success': True,
            'position': {
                'position': {'x': 350.0, 'y': 150.0, 'z': 200.0}
            }
        })
        
        events = await safety_manager.check_position_limits()
        
        # Should generate one event
        assert len(events) == 1
        assert events[0].event_type == SafetyEventType.POSITION_LIMIT_EXCEEDED
        assert events[0].level == SafetyLevel.CRITICAL
        assert 'x' in events[0].details['axis']
    
    @pytest.mark.asyncio
    async def test_check_position_y_exceeded(self, safety_manager, mock_cache_manager):
        """Test checking exceeded Y position."""
        mock_cache_manager.get = AsyncMock(return_value={
            'success': True,
            'position': {
                'position': {'x': 150.0, 'y': 350.0, 'z': 200.0}
            }
        })
        
        events = await safety_manager.check_position_limits()
        
        # Should generate one event
        assert len(events) == 1
        assert events[0].event_type == SafetyEventType.POSITION_LIMIT_EXCEEDED
        assert 'y' in events[0].details['axis']
    
    @pytest.mark.asyncio
    async def test_check_position_z_exceeded(self, safety_manager, mock_cache_manager):
        """Test checking exceeded Z position."""
        mock_cache_manager.get = AsyncMock(return_value={
            'success': True,
            'position': {
                'position': {'x': 150.0, 'y': 150.0, 'z': 450.0}
            }
        })
        
        events = await safety_manager.check_position_limits()
        
        # Should generate one event
        assert len(events) == 1
        assert events[0].event_type == SafetyEventType.POSITION_LIMIT_EXCEEDED
        assert 'z' in events[0].details['axis']
    
    @pytest.mark.asyncio
    async def test_check_position_with_custom_position(self, safety_manager, mock_cache_manager):
        """Test checking position with provided position."""
        mock_cache_manager.get = AsyncMock(return_value={
            'success': True,
            'position': {
                'position': {'x': 150.0, 'y': 150.0, 'z': 200.0}
            }
        })
        
        # Check custom position
        custom_position = {'x': 150.0, 'y': 350.0, 'z': 200.0}
        events = await safety_manager.check_position_limits(custom_position)
        
        # Should generate one event for Y
        assert len(events) == 1
        assert events[0].event_type == SafetyEventType.POSITION_LIMIT_EXCEEDED
        assert 'y' in events[0].details['axis']


class TestCheckPWMLimits:
    """Test PWM limit checking."""
    
    @pytest.mark.asyncio
    async def test_check_pwm_normal(self, safety_manager):
        """Test checking PWM within limits."""
        event = await safety_manager.check_pwm_limits('PWM_PIN', 0.75)
        
        # Should not generate event
        assert event is None
    
    @pytest.mark.asyncio
    async def test_check_pwm_exceeded(self, safety_manager):
        """Test checking exceeded PWM value."""
        event = await safety_manager.check_pwm_limits('PWM_PIN', 1.5)
        
        # Should generate event
        assert event is not None
        assert event.event_type == SafetyEventType.PWM_LIMIT_EXCEEDED
        assert event.level == SafetyLevel.WARNING
        assert 'out of bounds' in event.message.lower()
    
    @pytest.mark.asyncio
    async def test_check_pwm_negative(self, safety_manager):
        """Test checking negative PWM value."""
        event = await safety_manager.check_pwm_limits('PWM_PIN', -0.5)
        
        # Should generate event
        assert event is not None
        assert event.event_type == SafetyEventType.PWM_LIMIT_EXCEEDED


class TestValidateMoveCommand:
    """Test move command validation."""
    
    @pytest.mark.asyncio
    async def test_validate_move_normal(self, safety_manager):
        """Test validating normal move command."""
        is_valid, errors = await safety_manager.validate_move_command(
            x=100.0,
            y=100.0,
            z=50.0,
            feedrate=1500.0
        )
        
        assert is_valid == True
        assert len(errors) == 0
    
    @pytest.mark.asyncio
    async def test_validate_move_x_out_of_bounds(self, safety_manager):
        """Test validating move with X out of bounds."""
        is_valid, errors = await safety_manager.validate_move_command(
            x=350.0,
            y=100.0,
            z=50.0
        )
        
        assert is_valid == False
        assert len(errors) == 1
        assert 'X position' in errors[0]
    
    @pytest.mark.asyncio
    async def test_validate_move_feedrate_out_of_bounds(self, safety_manager):
        """Test validating move with feedrate out of bounds."""
        is_valid, errors = await safety_manager.validate_move_command(
            x=100.0,
            y=100.0,
            feedrate=35000.0
        )
        
        assert is_valid == False
        assert len(errors) == 1
        assert 'Feedrate' in errors[0]
    
    @pytest.mark.asyncio
    async def test_validate_move_all_out_of_bounds(self, safety_manager):
        """Test validating move with all parameters out of bounds."""
        is_valid, errors = await safety_manager.validate_move_command(
            x=350.0,
            y=350.0,
            z=450.0,
            feedrate=35000.0
        )
        
        assert is_valid == False
        assert len(errors) == 4


class TestValidateTemperatureCommand:
    """Test temperature command validation."""
    
    @pytest.mark.asyncio
    async def test_validate_temperature_normal(self, safety_manager):
        """Test validating normal temperature command."""
        is_valid, error = await safety_manager.validate_temperature_command(
            'extruder',
            210.0
        )
        
        assert is_valid == True
        assert error == ""
    
    @pytest.mark.asyncio
    async def test_validate_temperature_exceeded(self, safety_manager):
        """Test validating exceeded temperature."""
        is_valid, error = await safety_manager.validate_temperature_command(
            'extruder',
            300.0
        )
        
        assert is_valid == False
        assert 'out of bounds' in error.lower()
    
    @pytest.mark.asyncio
    async def test_validate_temperature_negative(self, safety_manager):
        """Test validating negative temperature."""
        is_valid, error = await safety_manager.validate_temperature_command(
            'extruder',
            -10.0
        )
        
        assert is_valid == False
        assert 'out of bounds' in error.lower()
    
    @pytest.mark.asyncio
    async def test_validate_temperature_bed(self, safety_manager):
        """Test validating bed temperature."""
        is_valid, error = await safety_manager.validate_temperature_command(
            'heater_bed',
            100.0
        )
        
        assert is_valid == True
        assert error == ""
    
    @pytest.mark.asyncio
    async def test_validate_temperature_bed_exceeded(self, safety_manager):
        """Test validating exceeded bed temperature."""
        is_valid, error = await safety_manager.validate_temperature_command(
            'heater_bed',
            150.0
        )
        
        assert is_valid == False
        assert 'out of bounds' in error.lower()


class TestValidateFanCommand:
    """Test fan command validation."""
    
    @pytest.mark.asyncio
    async def test_validate_fan_normal(self, safety_manager):
        """Test validating normal fan command."""
        is_valid, error = await safety_manager.validate_fan_command(
            'fan',
            0.75
        )
        
        assert is_valid == True
        assert error == ""
    
    @pytest.mark.asyncio
    async def test_validate_fan_exceeded(self, safety_manager):
        """Test validating exceeded fan speed."""
        is_valid, error = await safety_manager.validate_fan_command(
            'fan',
            1.5
        )
        
        assert is_valid == False
        assert 'out of bounds' in error.lower()
    
    @pytest.mark.asyncio
    async def test_validate_fan_negative(self, safety_manager):
        """Test validating negative fan speed."""
        is_valid, error = await safety_manager.validate_fan_command(
            'fan',
            -0.5
        )
        
        assert is_valid == False
        assert 'out of bounds' in error.lower()


class TestEmergencyStop:
    """Test emergency stop functionality."""
    
    @pytest.mark.asyncio
    async def test_emergency_stop_success(self, safety_manager, mock_cache_manager):
        """Test successful emergency stop."""
        with patch('middleware.safety.aiohttp.ClientSession') as mock_session:
            mock_post = AsyncMock(return_value={'result': True})
            mock_session.return_value.post.return_value.__aenter__ = AsyncMock(return_value=mock_session.return_value)
            mock_session.return_value.post.return_value.__aenter__.json = AsyncMock(return_value={'result': True})
            
            manager = SafetyManager(
                moonraker_host='localhost',
                moonraker_port=7125,
                cache_manager=mock_cache_manager,
                auto_start=False
            )
            
            event = await manager.emergency_stop("Test emergency")
            
            assert event.event_type == SafetyEventType.EMERGENCY_STOP
            assert event.level == SafetyLevel.EMERGENCY
            assert manager._emergency_stop_active == True
            
            # Verify statistics
            stats = await manager.get_statistics()
            assert stats['emergency_stops'] == 1
    
    @pytest.mark.asyncio
    async def test_emergency_stop_invalidates_cache(self, safety_manager, mock_cache_manager):
        """Test that emergency stop invalidates cache."""
        with patch('middleware.safety.aiohttp.ClientSession') as mock_session:
            mock_post = AsyncMock(return_value={'result': True})
            mock_session.return_value.post.return_value.__aenter__ = AsyncMock(return_value=mock_session.return_value)
            mock_session.return_value.post.return_value.__aenter__.json = AsyncMock(return_value={'result': True})
            
            manager = SafetyManager(
                moonraker_host='localhost',
                moonraker_port=7125,
                cache_manager=mock_cache_manager,
                auto_start=False
            )
            
            await manager.emergency_stop("Test emergency")
            
            # Verify cache invalidation
            assert mock_cache_manager.invalidate_category.call_count >= 3  # At least POSITION, GPIO, PWM
    
    def test_is_emergency_stop_active(self, safety_manager):
        """Test checking emergency stop status."""
        # Initially not active
        assert safety_manager.is_emergency_stop_active() == False
        
        # Set active
        safety_manager._emergency_stop_active = True
        
        # Now active
        assert safety_manager.is_emergency_stop_active() == True
    
    def test_clear_emergency_stop(self, safety_manager):
        """Test clearing emergency stop state."""
        # Set active
        safety_manager._emergency_stop_active = True
        
        # Clear
        safety_manager.clear_emergency_stop()
        
        # Verify cleared
        assert safety_manager.is_emergency_stop_active() == False


class TestHoming:
    """Test homing functionality."""
    
    @pytest.mark.asyncio
    async def test_check_homing_required(self, safety_manager):
        """Test checking if homing is required."""
        # No axes homed
        assert await safety_manager.check_homing_required() == True
        
        # Mark X as homed
        await safety_manager.mark_axis_homed('x')
        
        # X should not be required
        assert await safety_manager.check_homing_required(['x']) == False
        
        # Y and Z should still be required
        assert await safety_manager.check_homing_required(['y', 'z']) == True
    
    @pytest.mark.asyncio
    async def test_check_homing_all_axes(self, safety_manager):
        """Test checking homing for all axes."""
        # Mark all axes as homed
        await safety_manager.mark_axis_homed('x')
        await safety_manager.mark_axis_homed('y')
        await safety_manager.mark_axis_homed('z')
        
        # Should not require homing
        assert await safety_manager.check_homing_required() == False
    
    @pytest.mark.asyncio
    async def test_mark_axis_homed(self, safety_manager):
        """Test marking axis as homed."""
        await safety_manager.mark_axis_homed('x')
        
        assert 'x' in safety_manager._homed_axes
    
    @pytest.mark.asyncio
    async def test_mark_axes_unhomed(self, safety_manager):
        """Test marking axes as not homed."""
        # Mark all axes as homed
        await safety_manager.mark_axis_homed('x')
        await safety_manager.mark_axis_homed('y')
        await safety_manager.mark_axis_homed('z')
        
        # Mark Y and Z as not homed
        await safety_manager.mark_axes_unhomed(['y', 'z'])
        
        assert 'x' in safety_manager._homed_axes
        assert 'y' not in safety_manager._homed_axes
        assert 'z' not in safety_manager._homed_axes
    
    @pytest.mark.asyncio
    async def test_mark_all_axes_unhomed(self, safety_manager):
        """Test marking all axes as not homed."""
        # Mark all axes as homed
        await safety_manager.mark_axis_homed('x')
        await safety_manager.mark_axis_homed('y')
        await safety_manager.mark_axis_homed('z')
        
        # Mark all as not homed
        await safety_manager.mark_axes_unhomed()
        
        assert len(safety_manager._homed_axes) == 0
    
    def test_get_homed_axes(self, safety_manager):
        """Test getting homed axes."""
        # Mark some axes as homed
        safety_manager._homed_axes.add('x')
        safety_manager._homed_axes.add('z')
        
        axes = safety_manager.get_homed_axes()
        
        assert len(axes) == 2
        assert 'x' in axes
        assert 'z' in axes
        assert 'y' not in axes


class TestStateChangeLogging:
    """Test state change logging."""
    
    @pytest.mark.asyncio
    async def test_log_state_change(self, safety_manager):
        """Test logging state change."""
        event = await safety_manager.log_state_change(
            'test_component',
            'old_state',
            'new_state',
            {'detail': 'data'}
        )
        
        assert event.event_type == SafetyEventType.STATE_CHANGE
        assert event.level == SafetyLevel.NORMAL
        assert event.component == 'test_component'
        assert event.details['old_state'] == 'old_state'
        assert event.details['new_state'] == 'new_state'
        assert event.details['detail'] == 'data'
        
        # Verify statistics
        stats = await safety_manager.get_statistics()
        assert stats['state_changes_logged'] == 1


class TestEventHistory:
    """Test event history operations."""
    
    @pytest.mark.asyncio
    async def test_get_event_history(self, safety_manager):
        """Test getting event history."""
        # Create some events
        await safety_manager.log_state_change('comp1', 'old1', 'new1')
        await safety_manager.log_state_change('comp2', 'old2', 'new2')
        
        # Get all history
        history = await safety_manager.get_event_history()
        
        assert len(history) == 2
    
    @pytest.mark.asyncio
    async def test_get_event_history_with_limit(self, safety_manager):
        """Test getting event history with limit."""
        # Create 5 events
        for i in range(5):
            await safety_manager.log_state_change(f'comp{i}', f'old{i}', f'new{i}')
        
        # Get with limit
        history = await safety_manager.get_event_history(limit=3)
        
        assert len(history) == 3
    
    @pytest.mark.asyncio
    async def test_get_event_history_with_type_filter(self, safety_manager):
        """Test getting event history filtered by type."""
        # Create events of different types
        await safety_manager.log_state_change('comp1', 'old1', 'new1')
        await safety_manager.emergency_stop("Test")
        
        # Get temperature events only
        history = await safety_manager.get_event_history(
            event_type=SafetyEventType.TEMPERATURE_EXCEEDED
        )
        
        assert len(history) == 1
        assert history[0].event_type == SafetyEventType.STATE_CHANGE
    
    @pytest.mark.asyncio
    async def test_clear_event_history(self, safety_manager):
        """Test clearing event history."""
        # Create some events
        await safety_manager.log_state_change('comp1', 'old1', 'new1')
        await safety_manager.log_state_change('comp2', 'old2', 'new2')
        
        # Clear
        await safety_manager.clear_event_history()
        
        # Verify empty
        history = await safety_manager.get_event_history()
        assert len(history) == 0


class TestGetStatistics:
    """Test getting safety statistics."""
    
    @pytest.mark.asyncio
    async def test_get_statistics(self, safety_manager):
        """Test getting safety statistics."""
        # Create some events
        await safety_manager.log_state_change('comp1', 'old1', 'new1')
        await safety_manager.emergency_stop("Test")
        
        stats = await safety_manager.get_statistics()
        
        assert 'total_events' in stats
        assert 'emergency_stops' in stats
        assert 'temperature_violations' in stats
        assert stats['total_events'] == 2
        assert stats['emergency_stops'] == 1


class TestGetCurrentLimits:
    """Test getting current safety limits."""
    
    @pytest.mark.asyncio
    async def test_get_current_limits(self, safety_manager):
        """Test getting current safety limits."""
        limits = await safety_manager.get_current_limits()
        
        assert 'temperature' in limits
        assert 'position' in limits
        assert 'velocity' in limits
        assert 'pwm' in limits
        assert 'fan' in limits
        assert 'feedrate' in limits
        
        assert limits['temperature']['max_extruder_temp'] == 250.0
        assert limits['position']['max_x'] == 300.0


class TestUpdateLimits:
    """Test updating safety limits."""
    
    @pytest.mark.asyncio
    async def test_update_limits(self, safety_manager):
        """Test updating safety limits."""
        # Update limits
        safety_manager.update_limits({
            'max_extruder_temp': 300.0,
            'max_x_position': 400.0
        })
        
        # Verify updates
        assert safety_manager.limits.max_extruder_temp == 300.0
        assert safety_manager.limits.max_x_position == 400.0


class TestResolveEvent:
    """Test resolving safety events."""
    
    @pytest.mark.asyncio
    async def test_resolve_event(self, safety_manager):
        """Test resolving a safety event."""
        # Create an event
        await safety_manager.log_state_change('comp1', 'old1', 'new1')
        
        # Get history
        history = await safety_manager.get_event_history()
        assert len(history) == 1
        assert not history[0].resolved
        
        # Resolve event
        result = await safety_manager.resolve_event(0)
        
        assert result == True
        
        # Verify resolved
        history = await safety_manager.get_event_history()
        assert history[0].resolved == True
    
    @pytest.mark.asyncio
    async def test_resolve_nonexistent_event(self, safety_manager):
        """Test resolving non-existent event."""
        result = await safety_manager.resolve_event(999)
        
        assert result == False


class TestGetCurrentState:
    """Test getting current safety state."""
    
    @pytest.mark.asyncio
    async def test_get_current_state(self, safety_manager):
        """Test getting current safety state."""
        # Set some state
        safety_manager._current_position = {'x': 100.0, 'y': 100.0, 'z': 50.0}
        safety_manager._current_temperatures = {'extruder': 200.0}
        safety_manager._homed_axes.add('x')
        safety_manager._emergency_stop_active = True
        
        state = safety_manager.get_current_state()
        
        assert state['position'] == {'x': 100.0, 'y': 100.0, 'z': 50.0}
        assert state['temperatures'] == {'extruder': 200.0}
        assert 'x' in state['homed_axes']
        assert state['emergency_stop_active'] == True
        assert state['running'] == False


class TestStartAndStop:
    """Test starting and stopping safety manager."""
    
    @pytest.mark.asyncio
    async def test_start_and_stop(self, safety_manager):
        """Test starting and stopping safety manager."""
        # Start
        await safety_manager.start()
        
        assert safety_manager._running == True
        
        # Stop
        await safety_manager.stop()
        
        assert safety_manager._running == False


class TestEventCallbacks:
    """Test event callback functionality."""
    
    @pytest.mark.asyncio
    async def test_add_event_callback(self, safety_manager):
        """Test adding event callback."""
        callback_called = []
        
        def callback(event):
            callback_called.append(event)
        
        safety_manager.add_event_callback(callback)
        
        # Trigger an event
        await safety_manager.log_state_change('comp1', 'old1', 'new1')
        
        # Verify callback was called
        assert len(callback_called) == 1
        assert callback_called[0].event_type == SafetyEventType.STATE_CHANGE
    
    @pytest.mark.asyncio
    async def test_remove_event_callback(self, safety_manager):
        """Test removing event callback."""
        callback_called = []
        
        def callback(event):
            callback_called.append(event)
        
        safety_manager.add_event_callback(callback)
        safety_manager.remove_event_callback(callback)
        
        # Trigger an event
        await safety_manager.log_state_change('comp1', 'old1', 'new1')
        
        # Verify callback was NOT called
        assert len(callback_called) == 0
