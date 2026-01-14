#!/usr/bin/env python3
# Unit tests for Fan Control component

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock


class FanControl:
    """Mock FanControl class for testing."""
    
    def __init__(self, config):
        self.server = config.get_server()
        self.klippy_apis = self.server.lookup_component('klippy_apis')
        self.default_speed = 0.5
        self.max_speed = 1.0
        self.default_fan = 'fan'


@pytest.fixture
def mock_server():
    """Create a mock Moonraker server."""
    server = Mock()
    server.lookup_component = Mock()
    server.register_endpoint = Mock()
    return server


@pytest.fixture
def mock_config(mock_server):
    """Create a mock config object."""
    config = Mock()
    config.get_server = Mock(return_value=mock_server)
    config.getfloat = Mock(side_effect=lambda key, default=0.5, minval=0.0, maxval=1.0: default)
    config.get = Mock(return_value='fan')
    return config


@pytest.fixture
def mock_klippy_apis():
    """Create a mock Klippy APIs object."""
    apis = Mock()
    apis.query_objects = AsyncMock()
    apis.run_gcode = AsyncMock()
    return apis


@pytest.fixture
def fan_control(mock_config, mock_klippy_apis):
    """Create a FanControl instance for testing."""
    mock_server = mock_config.get_server()
    mock_server.lookup_component = Mock(return_value=mock_klippy_apis)
    
    control = FanControl(mock_config)
    return control


class TestFanControlInitialization:
    """Test FanControl initialization."""
    
    def test_initialization_with_defaults(self, mock_config, mock_klippy_apis):
        """Test initialization with default configuration."""
        mock_server = mock_config.get_server()
        mock_server.lookup_component = Mock(return_value=mock_klippy_apis)
        
        control = FanControl(mock_config)
        
        assert control.server is not None
        assert control.klippy_apis is not None
        assert control.default_speed == 0.5
        assert control.max_speed == 1.0
        assert control.default_fan == 'fan'
    
    def test_initialization_with_custom_values(self, mock_config, mock_klippy_apis):
        """Test initialization with custom values."""
        mock_server = mock_config.get_server()
        mock_server.lookup_component = Mock(return_value=mock_klippy_apis)
        mock_config.getfloat = Mock(side_effect=lambda key, default=0.5, minval=0.0, maxval=1.0: 0.8 if key == 'default_speed' else 0.9)
        mock_config.get = Mock(return_value='fan_generic')
        
        control = FanControl(mock_config)
        
        assert control.default_speed == 0.8
        assert control.max_speed == 0.9
        assert control.default_fan == 'fan_generic'
    
    def test_endpoint_registration(self, mock_config, mock_klippy_apis):
        """Test that REST endpoints are registered."""
        mock_server = mock_config.get_server()
        mock_server.lookup_component = Mock(return_value=mock_klippy_apis)
        
        FanControl(mock_config)
        
        assert mock_server.register_endpoint.call_count == 3
        calls = mock_server.register_endpoint.call_args_list
        
        # Check endpoints
        endpoints = [call[0][0] for call in calls]
        assert '/api/fan_control/set' in endpoints
        assert '/api/fan_control/off' in endpoints
        assert '/api/fan_control/status' in endpoints


class TestHandleSetFan:
    """Test fan speed setting handler."""
    
    @pytest.mark.asyncio
    async def test_set_fan_success(self, fan_control, mock_klippy_apis):
        """Test successful fan speed setting."""
        mock_klippy_apis.run_gcode = AsyncMock(return_value={'result': {'queued': True}})
        
        web_request = Mock()
        web_request.get_float = Mock(return_value=0.75)
        web_request.get_str = Mock(return_value='fan')
        
        result = await fan_control._handle_set_fan(web_request)
        
        assert result['success'] == True
        assert result['fan'] == 'fan'
        assert result['speed'] == 0.75
        assert result['pwm_value'] == 191  # 0.75 * 255
        assert 'gcode' in result
    
    @pytest.mark.asyncio
    async def test_set_fan_with_max_speed_limit(self, fan_control, mock_klippy_apis):
        """Test fan speed setting with max speed limit."""
        fan_control.max_speed = 0.8
        mock_klippy_apis.run_gcode = AsyncMock(return_value={'result': {'queued': True}})
        
        web_request = Mock()
        web_request.get_float = Mock(return_value=1.0)
        web_request.get_str = Mock(return_value='fan')
        
        result = await fan_control._handle_set_fan(web_request)
        
        assert result['success'] == True
        assert result['speed'] == 0.8  # Limited to max_speed
    
    @pytest.mark.asyncio
    async def test_set_fan_speed_out_of_range(self, fan_control):
        """Test fan speed setting with out of range value."""
        web_request = Mock()
        web_request.get_float = Mock(return_value=1.5)
        web_request.get_str = Mock(return_value='fan')
        
        result = await fan_control._handle_set_fan(web_request)
        
        assert result['success'] == False
        assert 'error' in result
        assert 'between 0.0 and 1.0' in result['error']
    
    @pytest.mark.asyncio
    async def test_set_fan_negative_speed(self, fan_control):
        """Test fan speed setting with negative value."""
        web_request = Mock()
        web_request.get_float = Mock(return_value=-0.5)
        web_request.get_str = Mock(return_value='fan')
        
        result = await fan_control._handle_set_fan(web_request)
        
        assert result['success'] == False
        assert 'error' in result
    
    @pytest.mark.asyncio
    async def test_set_generic_fan(self, fan_control, mock_klippy_apis):
        """Test setting generic fan speed."""
        mock_klippy_apis.run_gcode = AsyncMock(return_value={'result': {'queued': True}})
        
        web_request = Mock()
        web_request.get_float = Mock(return_value=0.5)
        web_request.get_str = Mock(return_value='fan_generic')
        
        result = await fan_control._handle_set_fan(web_request)
        
        assert result['success'] == True
        assert result['fan'] == 'fan_generic'
        assert 'SET_FAN_SPEED' in result['gcode']
    
    @pytest.mark.asyncio
    async def test_set_fan_gcode_not_queued(self, fan_control, mock_klippy_apis):
        """Test fan speed setting when G-code not queued."""
        mock_klippy_apis.run_gcode = AsyncMock(return_value={'result': {'queued': False}})
        
        web_request = Mock()
        web_request.get_float = Mock(return_value=0.5)
        web_request.get_str = Mock(return_value='fan')
        
        result = await fan_control._handle_set_fan(web_request)
        
        assert result['success'] == False
        assert 'error' in result
    
    @pytest.mark.asyncio
    async def test_set_fan_exception(self, fan_control, mock_klippy_apis):
        """Test fan speed setting with exception."""
        mock_klippy_apis.run_gcode = AsyncMock(side_effect=Exception('G-code failed'))
        
        web_request = Mock()
        web_request.get_float = Mock(return_value=0.5)
        web_request.get_str = Mock(return_value='fan')
        
        result = await fan_control._handle_set_fan(web_request)
        
        assert result['success'] == False
        assert 'error' in result


class TestHandleFanOff:
    """Test fan off handler."""
    
    @pytest.mark.asyncio
    async def test_fan_off_success(self, fan_control, mock_klippy_apis):
        """Test successful fan off."""
        mock_klippy_apis.run_gcode = AsyncMock(return_value={'result': {'queued': True}})
        
        web_request = Mock()
        web_request.get_str = Mock(return_value='fan')
        
        result = await fan_control._handle_fan_off(web_request)
        
        assert result['success'] == True
        assert result['fan'] == 'fan'
        assert result['speed'] == 0.0
        assert result['gcode'] == 'M107'
    
    @pytest.mark.asyncio
    async def test_generic_fan_off(self, fan_control, mock_klippy_apis):
        """Test generic fan off."""
        mock_klippy_apis.run_gcode = AsyncMock(return_value={'result': {'queued': True}})
        
        web_request = Mock()
        web_request.get_str = Mock(return_value='fan_generic')
        
        result = await fan_control._handle_fan_off(web_request)
        
        assert result['success'] == True
        assert result['fan'] == 'fan_generic'
        assert 'SET_FAN_SPEED' in result['gcode']
        assert 'SPEED=0.0' in result['gcode']
    
    @pytest.mark.asyncio
    async def test_fan_off_gcode_not_queued(self, fan_control, mock_klippy_apis):
        """Test fan off when G-code not queued."""
        mock_klippy_apis.run_gcode = AsyncMock(return_value={'result': {'queued': False}})
        
        web_request = Mock()
        web_request.get_str = Mock(return_value='fan')
        
        result = await fan_control._handle_fan_off(web_request)
        
        assert result['success'] == False
        assert 'error' in result


class TestHandleGetStatus:
    """Test fan status handler."""
    
    @pytest.mark.asyncio
    async def test_get_status_success(self, fan_control, mock_klippy_apis):
        """Test successful fan status query."""
        mock_klippy_apis.query_objects = AsyncMock(return_value={
            'result': {
                'fan': {
                    'speed': 0.75,
                    'rpm': 1500,
                    'power': 0.75
                },
                'fan_generic': {
                    'fan_generic_1': {
                        'speed': 0.5,
                        'rpm': 1000,
                        'power': 0.5
                    }
                }
            }
        })
        
        web_request = Mock()
        web_request.get_str = Mock(return_value=None)
        
        result = await fan_control._handle_get_status(web_request)
        
        assert result['success'] == True
        assert 'fans' in result
        assert 'fan' in result['fans']
        assert result['fans']['fan']['speed'] == 0.75
    
    @pytest.mark.asyncio
    async def test_get_status_specific_fan(self, fan_control, mock_klippy_apis):
        """Test status query for specific fan."""
        mock_klippy_apis.query_objects = AsyncMock(return_value={
            'result': {
                'fan': {
                    'speed': 0.75,
                    'rpm': 1500,
                    'power': 0.75
                }
            }
        })
        
        web_request = Mock()
        web_request.get_str = Mock(return_value='fan')
        
        result = await fan_control._handle_get_status(web_request)
        
        assert result['success'] == True
        assert 'fan' in result['fans']
        assert len(result['fans']) == 1
    
    @pytest.mark.asyncio
    async def test_get_status_fan_not_found(self, fan_control, mock_klippy_apis):
        """Test status query for non-existent fan."""
        mock_klippy_apis.query_objects = AsyncMock(return_value={
            'result': {
                'fan': {
                    'speed': 0.75,
                    'rpm': 1500,
                    'power': 0.75
                }
            }
        })
        
        web_request = Mock()
        web_request.get_str = Mock(return_value='nonexistent_fan')
        
        result = await fan_control._handle_get_status(web_request)
        
        assert result['success'] == False
        assert 'error' in result
    
    @pytest.mark.asyncio
    async def test_get_status_error(self, fan_control, mock_klippy_apis):
        """Test status query with error."""
        mock_klippy_apis.query_objects = AsyncMock(side_effect=Exception('Query failed'))
        
        web_request = Mock()
        web_request.get_str = Mock(return_value=None)
        
        result = await fan_control._handle_get_status(web_request)
        
        assert result['success'] == False
        assert 'error' in result


class TestQueryFanStatus:
    """Test fan status querying."""
    
    @pytest.mark.asyncio
    async def test_query_all_fans(self, fan_control, mock_klippy_apis):
        """Test querying all fans."""
        mock_klippy_apis.query_objects = AsyncMock(return_value={
            'result': {
                'fan': {
                    'speed': 0.75,
                    'rpm': 1500,
                    'power': 0.75
                },
                'fan_generic': {
                    'fan_generic_1': {
                        'speed': 0.5,
                        'rpm': 1000,
                        'power': 0.5
                    }
                }
            }
        })
        
        result = await fan_control._query_fan_status(None)
        
        assert 'fans' in result
        assert 'timestamp' in result
        assert 'fan' in result['fans']
        assert 'fan_generic_1' in result['fans']
    
    @pytest.mark.asyncio
    async def test_query_specific_fan(self, fan_control, mock_klippy_apis):
        """Test querying specific fan."""
        mock_klippy_apis.query_objects = AsyncMock(return_value={
            'result': {
                'fan': {
                    'speed': 0.75,
                    'rpm': 1500,
                    'power': 0.75
                }
            }
        })
        
        result = await fan_control._query_fan_status('fan')
        
        assert 'fans' in result
        assert 'fan' in result['fans']
        assert len(result['fans']) == 1
    
    @pytest.mark.asyncio
    async def test_query_fan_invalid_response(self, fan_control, mock_klippy_apis):
        """Test querying fan status with invalid response."""
        mock_klippy_apis.query_objects = AsyncMock(return_value={'error': 'Invalid'})
        
        with pytest.raises(Exception) as exc_info:
            await fan_control._query_fan_status('fan')
        
        assert 'Invalid response from Klipper API' in str(exc_info.value)


class TestGetStatus:
    """Test get_status method."""
    
    def test_get_status(self, fan_control):
        """Test getting component status."""
        fan_control.default_fan = 'fan_generic'
        fan_control.default_speed = 0.8
        fan_control.max_speed = 0.9
        
        status = fan_control.get_status(123456.789)
        
        assert status['default_fan'] == 'fan_generic'
        assert status['default_speed'] == 0.8
        assert status['max_speed'] == 0.9
        assert status['component'] == 'fan_control'


class TestClose:
    """Test close method."""
    
    def test_close(self, fan_control):
        """Test closing component."""
        # Should not raise any exception
        fan_control.close()
        assert True


class TestLoadComponent:
    """Test load_component function."""
    
    def test_load_component(self, mock_config, mock_klippy_apis):
        """Test loading component via load_component function."""
        from moonraker_extensions.fan_control import load_component
        
        mock_server = mock_config.get_server()
        mock_server.lookup_component = Mock(return_value=mock_klippy_apis)
        
        control = load_component(mock_config)
        
        assert isinstance(control, FanControl)
        assert control.server is not None
