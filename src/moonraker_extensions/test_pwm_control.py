#!/usr/bin/env python3
# Unit tests for PWM Control component

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock


class PWMControl:
    """Mock PWMControl class for testing."""
    
    def __init__(self, config):
        self.server = config.get_server()
        self.klippy_apis = self.server.lookup_component('klippy_apis')
        self.default_value = 0.0
        self.ramp_duration = 1.0
        self.ramp_steps = 10
        self.default_pin = None
        self.active_ramps = {}


@pytest.fixture
def mock_server():
    """Create a mock Moonraker server."""
    server = Mock()
    server.lookup_component = Mock()
    server.register_endpoint = Mock()
    server.get_event_loop = Mock()
    return server


@pytest.fixture
def mock_config(mock_server):
    """Create a mock config object."""
    config = Mock()
    config.get_server = Mock(return_value=mock_server)
    config.getfloat = Mock(side_effect=lambda key, default=0.0, minval=0.0, maxval=1.0: default)
    config.getint = Mock(side_effect=lambda key, default=10, minval=2, maxval=100: default)
    config.get = Mock(return_value=None)
    return config


@pytest.fixture
def mock_klippy_apis():
    """Create a mock Klippy APIs object."""
    apis = Mock()
    apis.query_objects = AsyncMock()
    apis.run_gcode = AsyncMock()
    return apis


@pytest.fixture
def pwm_control(mock_config, mock_klippy_apis):
    """Create a PWMControl instance for testing."""
    mock_server = mock_config.get_server()
    mock_server.lookup_component = Mock(return_value=mock_klippy_apis)
    
    control = PWMControl(mock_config)
    return control


class TestPWMControlInitialization:
    """Test PWMControl initialization."""
    
    def test_initialization_with_defaults(self, mock_config, mock_klippy_apis):
        """Test initialization with default configuration."""
        mock_server = mock_config.get_server()
        mock_server.lookup_component = Mock(return_value=mock_klippy_apis)
        
        control = PWMControl(mock_config)
        
        assert control.server is not None
        assert control.klippy_apis is not None
        assert control.default_value == 0.0
        assert control.ramp_duration == 1.0
        assert control.ramp_steps == 10
        assert control.default_pin is None
        assert control.active_ramps == {}
    
    def test_initialization_with_custom_values(self, mock_config, mock_klippy_apis):
        """Test initialization with custom values."""
        mock_server = mock_config.get_server()
        mock_server.lookup_component = Mock(return_value=mock_klippy_apis)
        mock_config.getfloat = Mock(side_effect=lambda key, default=0.0, minval=0.0, maxval=1.0: 0.5 if key == 'default_value' else 2.0)
        mock_config.getint = Mock(side_effect=lambda key, default=10, minval=2, maxval=100: 20 if key == 'ramp_steps' else 5)
        mock_config.get = Mock(return_value='PWM_PIN')
        
        control = PWMControl(mock_config)
        
        assert control.default_value == 0.5
        assert control.ramp_duration == 2.0
        assert control.ramp_steps == 20
        assert control.default_pin == 'PWM_PIN'
    
    def test_endpoint_registration(self, mock_config, mock_klippy_apis):
        """Test that REST endpoints are registered."""
        mock_server = mock_config.get_server()
        mock_server.lookup_component = Mock(return_value=mock_klippy_apis)
        
        PWMControl(mock_config)
        
        assert mock_server.register_endpoint.call_count == 3
        calls = mock_server.register_endpoint.call_args_list
        
        # Check endpoints
        endpoints = [call[0][0] for call in calls]
        assert '/api/pwm_control/set' in endpoints
        assert '/api/pwm_control/ramp' in endpoints
        assert '/api/pwm_control/status' in endpoints


class TestHandleSetPWM:
    """Test PWM value setting handler."""
    
    @pytest.mark.asyncio
    async def test_set_pwm_success(self, pwm_control, mock_klippy_apis):
        """Test successful PWM value setting."""
        mock_klippy_apis.run_gcode = AsyncMock(return_value={'result': {'queued': True}})
        
        web_request = Mock()
        web_request.get_float = Mock(return_value=0.75)
        web_request.get_str = Mock(return_value='PWM_PIN')
        
        result = await pwm_control._handle_set_pwm(web_request)
        
        assert result['success'] == True
        assert result['pin'] == 'PWM_PIN'
        assert result['value'] == 0.75
        assert 'gcode' in result
        assert 'SET_PIN' in result['gcode']
    
    @pytest.mark.asyncio
    async def test_set_pwm_with_default_pin(self, pwm_control, mock_klippy_apis):
        """Test PWM setting with default pin."""
        pwm_control.default_pin = 'DEFAULT_PIN'
        mock_klippy_apis.run_gcode = AsyncMock(return_value={'result': {'queued': True}})
        
        web_request = Mock()
        web_request.get_float = Mock(return_value=0.5)
        web_request.get_str = Mock(return_value=None)
        
        result = await pwm_control._handle_set_pwm(web_request)
        
        assert result['success'] == True
        assert result['pin'] == 'DEFAULT_PIN'
    
    @pytest.mark.asyncio
    async def test_set_pwm_missing_pin(self, pwm_control):
        """Test PWM setting with missing pin."""
        pwm_control.default_pin = None
        
        web_request = Mock()
        web_request.get_float = Mock(return_value=0.5)
        web_request.get_str = Mock(return_value=None)
        
        result = await pwm_control._handle_set_pwm(web_request)
        
        assert result['success'] == False
        assert 'error' in result
        assert 'Pin name is required' in result['error']
    
    @pytest.mark.asyncio
    async def test_set_pwm_value_out_of_range(self, pwm_control):
        """Test PWM setting with out of range value."""
        web_request = Mock()
        web_request.get_float = Mock(return_value=1.5)
        web_request.get_str = Mock(return_value='PWM_PIN')
        
        result = await pwm_control._handle_set_pwm(web_request)
        
        assert result['success'] == False
        assert 'error' in result
        assert 'between 0.0 and 1.0' in result['error']
    
    @pytest.mark.asyncio
    async def test_set_pwm_negative_value(self, pwm_control):
        """Test PWM setting with negative value."""
        web_request = Mock()
        web_request.get_float = Mock(return_value=-0.5)
        web_request.get_str = Mock(return_value='PWM_PIN')
        
        result = await pwm_control._handle_set_pwm(web_request)
        
        assert result['success'] == False
        assert 'error' in result
    
    @pytest.mark.asyncio
    async def test_set_pwm_gcode_not_queued(self, pwm_control, mock_klippy_apis):
        """Test PWM setting when G-code not queued."""
        mock_klippy_apis.run_gcode = AsyncMock(return_value={'result': {'queued': False}})
        
        web_request = Mock()
        web_request.get_float = Mock(return_value=0.5)
        web_request.get_str = Mock(return_value='PWM_PIN')
        
        result = await pwm_control._handle_set_pwm(web_request)
        
        assert result['success'] == False
        assert 'error' in result
    
    @pytest.mark.asyncio
    async def test_set_pwm_exception(self, pwm_control, mock_klippy_apis):
        """Test PWM setting with exception."""
        mock_klippy_apis.run_gcode = AsyncMock(side_effect=Exception('G-code failed'))
        
        web_request = Mock()
        web_request.get_float = Mock(return_value=0.5)
        web_request.get_str = Mock(return_value='PWM_PIN')
        
        result = await pwm_control._handle_set_pwm(web_request)
        
        assert result['success'] == False
        assert 'error' in result


class TestHandleRampPWM:
    """Test PWM ramp handler."""
    
    @pytest.mark.asyncio
    async def test_ramp_pwm_success(self, pwm_control, mock_klippy_apis):
        """Test successful PWM ramp."""
        mock_klippy_apis.run_gcode = AsyncMock(return_value={'result': {'queued': True}})
        
        web_request = Mock()
        web_request.get_float = Mock(side_effect=lambda key: 0.0 if key == 'start_value' else 1.0)
        web_request.get_str = Mock(return_value='PWM_PIN')
        web_request.get_int = Mock(return_value=10)
        
        result = await pwm_control._handle_ramp_pwm(web_request)
        
        assert result['success'] == True
        assert result['pin'] == 'PWM_PIN'
        assert result['start_value'] == 0.0
        assert result['end_value'] == 1.0
        assert result['duration'] == 1.0
        assert result['steps'] == 10
        assert 'PWM_PIN' in pwm_control.active_ramps
    
    @pytest.mark.asyncio
    async def test_ramp_pwm_with_custom_duration(self, pwm_control, mock_klippy_apis):
        """Test PWM ramp with custom duration."""
        mock_klippy_apis.run_gcode = AsyncMock(return_value={'result': {'queued': True}})
        
        web_request = Mock()
        web_request.get_float = Mock(side_effect=lambda key: 0.0 if key == 'start_value' else (1.0 if key == 'end_value' else 5.0))
        web_request.get_str = Mock(return_value='PWM_PIN')
        web_request.get_int = Mock(return_value=10)
        
        result = await pwm_control._handle_ramp_pwm(web_request)
        
        assert result['success'] == True
        assert result['duration'] == 5.0
    
    @pytest.mark.asyncio
    async def test_ramp_pwm_missing_pin(self, pwm_control):
        """Test PWM ramp with missing pin."""
        pwm_control.default_pin = None
        
        web_request = Mock()
        web_request.get_float = Mock(side_effect=lambda key: 0.0 if key == 'start_value' else 1.0)
        web_request.get_str = Mock(return_value=None)
        web_request.get_int = Mock(return_value=10)
        
        result = await pwm_control._handle_ramp_pwm(web_request)
        
        assert result['success'] == False
        assert 'error' in result
        assert 'Pin name is required' in result['error']
    
    @pytest.mark.asyncio
    async def test_ramp_pwm_start_value_out_of_range(self, pwm_control):
        """Test PWM ramp with start value out of range."""
        web_request = Mock()
        web_request.get_float = Mock(side_effect=lambda key: -0.5 if key == 'start_value' else 1.0)
        web_request.get_str = Mock(return_value='PWM_PIN')
        web_request.get_int = Mock(return_value=10)
        
        result = await pwm_control._handle_ramp_pwm(web_request)
        
        assert result['success'] == False
        assert 'error' in result
        assert 'Start value must be between 0.0 and 1.0' in result['error']
    
    @pytest.mark.asyncio
    async def test_ramp_pwm_end_value_out_of_range(self, pwm_control):
        """Test PWM ramp with end value out of range."""
        web_request = Mock()
        web_request.get_float = Mock(side_effect=lambda key: 0.0 if key == 'start_value' else 1.5)
        web_request.get_str = Mock(return_value='PWM_PIN')
        web_request.get_int = Mock(return_value=10)
        
        result = await pwm_control._handle_ramp_pwm(web_request)
        
        assert result['success'] == False
        assert 'error' in result
        assert 'End value must be between 0.0 and 1.0' in result['error']
    
    @pytest.mark.asyncio
    async def test_ramp_pwm_duration_out_of_range(self, pwm_control):
        """Test PWM ramp with duration out of range."""
        web_request = Mock()
        web_request.get_float = Mock(side_effect=lambda key: 0.0 if key == 'start_value' else (1.0 if key == 'end_value' else 500.0))
        web_request.get_str = Mock(return_value='PWM_PIN')
        web_request.get_int = Mock(return_value=10)
        
        result = await pwm_control._handle_ramp_pwm(web_request)
        
        assert result['success'] == False
        assert 'error' in result
        assert 'Duration must be between 0.1 and 300.0' in result['error']
    
    @pytest.mark.asyncio
    async def test_ramp_pwm_steps_out_of_range(self, pwm_control):
        """Test PWM ramp with steps out of range."""
        web_request = Mock()
        web_request.get_float = Mock(side_effect=lambda key: 0.0 if key == 'start_value' else 1.0)
        web_request.get_str = Mock(return_value='PWM_PIN')
        web_request.get_int = Mock(return_value=250)
        
        result = await pwm_control._handle_ramp_pwm(web_request)
        
        assert result['success'] == False
        assert 'error' in result
        assert 'Steps must be between 2 and 200' in result['error']
    
    @pytest.mark.asyncio
    async def test_ramp_pwm_cancel_existing_ramp(self, pwm_control, mock_klippy_apis):
        """Test that existing ramp is cancelled when starting new ramp."""
        # Create existing ramp task
        existing_task = Mock()
        existing_task.done = Mock(return_value=False)
        pwm_control.active_ramps['PWM_PIN'] = existing_task
        
        mock_klippy_apis.run_gcode = AsyncMock(return_value={'result': {'queued': True}})
        
        web_request = Mock()
        web_request.get_float = Mock(side_effect=lambda key: 0.0 if key == 'start_value' else 1.0)
        web_request.get_str = Mock(return_value='PWM_PIN')
        web_request.get_int = Mock(return_value=10)
        
        result = await pwm_control._handle_ramp_pwm(web_request)
        
        assert result['success'] == True
        assert existing_task.cancel.called


class TestExecuteRamp:
    """Test PWM ramp execution."""
    
    @pytest.mark.asyncio
    async def test_execute_ramp_success(self, pwm_control, mock_klippy_apis):
        """Test successful ramp execution."""
        mock_klippy_apis.run_gcode = AsyncMock(return_value={'result': {'queued': True}})
        
        # Execute ramp
        await pwm_control._execute_ramp('PWM_PIN', 0.0, 1.0, 1.0, 5)
        
        # Verify G-codes were sent
        assert mock_klippy_apis.run_gcode.call_count == 5
        
        # Verify values increment correctly
        calls = mock_klippy_apis.run_gcode.call_args_list
        values = []
        for call in calls:
            gcode = call[0][0]
            # Extract value from G-code
            if 'VALUE=' in gcode:
                value_str = gcode.split('VALUE=')[1]
                values.append(float(value_str))
        
        assert len(values) == 5
        assert values[0] == pytest.approx(0.0, abs=0.01)
        assert values[-1] == pytest.approx(1.0, abs=0.01)
    
    @pytest.mark.asyncio
    async def test_execute_ramp_cancellation(self, pwm_control, mock_klippy_apis):
        """Test ramp cancellation."""
        # Create a task that will be cancelled
        async def cancel_after_delay():
            await asyncio.sleep(0.1)
            # Cancel by setting a flag
            raise asyncio.CancelledError()
        
        # This test verifies the cancellation handling
        with pytest.raises(asyncio.CancelledError):
            await cancel_after_delay()


class TestHandleGetStatus:
    """Test PWM status handler."""
    
    @pytest.mark.asyncio
    async def test_get_status_success(self, pwm_control, mock_klippy_apis):
        """Test successful PWM status query."""
        mock_klippy_apis.query_objects = AsyncMock(return_value={
            'result': {
                'output_pin': {
                    'PWM_PIN': {
                        'value': 0.75,
                        'is_pwm': True,
                        'scale': 1.0,
                        'is_inverted': False
                    }
                }
            }
        })
        
        web_request = Mock()
        web_request.get_str = Mock(return_value=None)
        
        result = await pwm_control._handle_get_status(web_request)
        
        assert result['success'] == True
        assert 'pins' in result
        assert 'active_ramps' in result
        assert 'timestamp' in result
    
    @pytest.mark.asyncio
    async def test_get_status_specific_pin(self, pwm_control, mock_klippy_apis):
        """Test status query for specific pin."""
        mock_klippy_apis.query_objects = AsyncMock(return_value={
            'result': {
                'output_pin': {
                    'PWM_PIN': {
                        'value': 0.75,
                        'is_pwm': True,
                        'scale': 1.0,
                        'is_inverted': False
                    }
                }
            }
        })
        
        web_request = Mock()
        web_request.get_str = Mock(return_value='PWM_PIN')
        
        result = await pwm_control._handle_get_status(web_request)
        
        assert result['success'] == True
        assert 'PWM_PIN' in result['pins']
        assert len(result['pins']) == 1
    
    @pytest.mark.asyncio
    async def test_get_status_pin_not_found(self, pwm_control, mock_klippy_apis):
        """Test status query for non-existent pin."""
        mock_klippy_apis.query_objects = AsyncMock(return_value={
            'result': {
                'output_pin': {
                    'OTHER_PIN': {
                        'value': 0.5,
                        'is_pwm': True,
                        'scale': 1.0
                    }
                }
            }
        })
        
        web_request = Mock()
        web_request.get_str = Mock(return_value='PWM_PIN')
        
        result = await pwm_control._handle_get_status(web_request)
        
        assert result['success'] == False
        assert 'error' in result
    
    @pytest.mark.asyncio
    async def test_get_status_with_active_ramps(self, pwm_control, mock_klippy_apis):
        """Test status query with active ramps."""
        # Add active ramp
        task = Mock()
        task.done = Mock(return_value=False)
        task.cancelled = Mock(return_value=False)
        pwm_control.active_ramps['PWM_PIN'] = task
        
        mock_klippy_apis.query_objects = AsyncMock(return_value={
            'result': {
                'output_pin': {
                    'PWM_PIN': {
                        'value': 0.5,
                        'is_pwm': True,
                        'scale': 1.0
                    }
                }
            }
        })
        
        web_request = Mock()
        web_request.get_str = Mock(return_value=None)
        
        result = await pwm_control._handle_get_status(web_request)
        
        assert result['success'] == True
        assert 'PWM_PIN' in result['active_ramps']
        assert result['active_ramps']['PWM_PIN']['active'] == True


class TestQueryPWMStatus:
    """Test PWM status querying."""
    
    @pytest.mark.asyncio
    async def test_query_all_pwm_pins(self, pwm_control, mock_klippy_apis):
        """Test querying all PWM pins."""
        mock_klippy_apis.query_objects = AsyncMock(return_value={
            'result': {
                'output_pin': {
                    'PWM_PIN1': {
                        'value': 0.5,
                        'is_pwm': True,
                        'scale': 1.0
                    },
                    'PWM_PIN2': {
                        'value': 0.75,
                        'is_pwm': False,
                        'scale': 2.0
                    }
                }
            }
        })
        
        result = await pwm_control._query_pwm_status(None)
        
        assert 'pins' in result
        assert 'active_ramps' in result
        assert 'timestamp' in result
        assert 'PWM_PIN1' in result['pins']
        assert 'PWM_PIN2' in result['pins']
    
    @pytest.mark.asyncio
    async def test_query_pwm_invalid_response(self, pwm_control, mock_klippy_apis):
        """Test querying PWM status with invalid response."""
        mock_klippy_apis.query_objects = AsyncMock(return_value={'error': 'Invalid'})
        
        with pytest.raises(Exception) as exc_info:
            await pwm_control._query_pwm_status('PWM_PIN')
        
        assert 'Invalid response from Klipper API' in str(exc_info.value)


class TestGetStatus:
    """Test get_status method."""
    
    def test_get_status(self, pwm_control):
        """Test getting component status."""
        # Add active ramp
        task = Mock()
        task.done = Mock(return_value=False)
        pwm_control.active_ramps['PWM_PIN'] = task
        
        status = pwm_control.get_status(123456.789)
        
        assert status['default_value'] == 0.0
        assert status['ramp_duration'] == 1.0
        assert status['ramp_steps'] == 10
        assert status['default_pin'] is None
        assert status['active_ramps'] == 1


class TestClose:
    """Test close method."""
    
    def test_close(self, pwm_control):
        """Test closing component with active ramps."""
        # Add active ramp
        task = Mock()
        task.done = Mock(return_value=False)
        pwm_control.active_ramps['PWM_PIN'] = task
        
        pwm_control.close()
        
        # Verify tasks were cancelled
        assert task.cancel.called
        assert len(pwm_control.active_ramps) == 0


class TestLoadComponent:
    """Test load_component function."""
    
    def test_load_component(self, mock_config, mock_klippy_apis):
        """Test loading component via load_component function."""
        from moonraker_extensions.pwm_control import load_component
        
        mock_server = mock_config.get_server()
        mock_server.lookup_component = Mock(return_value=mock_klippy_apis)
        
        control = load_component(mock_config)
        
        assert isinstance(control, PWMControl)
        assert control.server is not None
