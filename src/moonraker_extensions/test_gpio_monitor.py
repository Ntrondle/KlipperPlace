#!/usr/bin/env python3
# Unit tests for GPIO Monitor component

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock, patch
import time


class GPIO_Monitor:
    """Mock GPIO_Monitor class for testing."""
    
    def __init__(self, config):
        self.server = config.get_server()
        self.klippy_apis = self.server.lookup_component('klippy_apis')
        self.enabled_pins = []
        self.poll_interval = 100


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
    config.getint = Mock(side_effect=lambda key, default=100, minval=10, maxval=5000: default)
    config.get = Mock(return_value='')
    return config


@pytest.fixture
def mock_klippy_apis():
    """Create a mock Klippy APIs object."""
    apis = Mock()
    apis.query_objects = AsyncMock()
    return apis


@pytest.fixture
def gpio_monitor(mock_config, mock_klippy_apis):
    """Create a GPIO_Monitor instance for testing."""
    mock_server = mock_config.get_server()
    mock_server.lookup_component = Mock(return_value=mock_klippy_apis)
    
    monitor = GPIO_Monitor(mock_config)
    return monitor


class TestGPIO_MonitorInitialization:
    """Test GPIO_Monitor initialization."""
    
    def test_initialization_with_default_config(self, mock_config, mock_klippy_apis):
        """Test initialization with default configuration."""
        mock_server = mock_config.get_server()
        mock_server.lookup_component = Mock(return_value=mock_klippy_apis)
        
        monitor = GPIO_Monitor(mock_config)
        
        assert monitor.server is not None
        assert monitor.klippy_apis is not None
        assert monitor.enabled_pins == []
        assert monitor.poll_interval == 100
    
    def test_initialization_with_custom_poll_interval(self, mock_config, mock_klippy_apis):
        """Test initialization with custom poll interval."""
        mock_server = mock_config.get_server()
        mock_server.lookup_component = Mock(return_value=mock_klippy_apis)
        mock_config.getint = Mock(side_effect=lambda key, default=100, minval=10, maxval=5000: 200)
        
        monitor = GPIO_Monitor(mock_config)
        
        assert monitor.poll_interval == 200
    
    def test_initialization_with_enabled_pins(self, mock_config, mock_klippy_apis):
        """Test initialization with enabled pins."""
        mock_server = mock_config.get_server()
        mock_server.lookup_component = Mock(return_value=mock_klippy_apis)
        mock_config.get = Mock(return_value='PIN1,PIN2,PIN3')
        
        monitor = GPIO_Monitor(mock_config)
        
        assert monitor.enabled_pins == ['PIN1', 'PIN2', 'PIN3']
    
    def test_endpoint_registration(self, mock_config, mock_klippy_apis):
        """Test that REST endpoints are registered."""
        mock_server = mock_config.get_server()
        mock_server.lookup_component = Mock(return_value=mock_klippy_apis)
        
        GPIO_Monitor(mock_config)
        
        assert mock_server.register_endpoint.call_count == 2
        calls = mock_server.register_endpoint.call_args_list
        
        # Check first endpoint
        assert calls[0][0][0] == "/api/gpio_monitor/inputs"
        assert calls[0][0][1] == ['GET']
        
        # Check second endpoint
        assert calls[1][0][0] == "/api/gpio_monitor/input/{pin_name}"
        assert calls[1][0][1] == ['GET']


class TestParseEnabledPins:
    """Test parsing of enabled pins configuration."""
    
    def test_parse_empty_enabled_pins(self, mock_config, mock_klippy_apis):
        """Test parsing empty enabled pins."""
        mock_server = mock_config.get_server()
        mock_server.lookup_component = Mock(return_value=mock_klippy_apis)
        mock_config.get = Mock(return_value='')
        
        monitor = GPIO_Monitor(mock_config)
        
        assert monitor.enabled_pins == []
    
    def test_parse_single_enabled_pin(self, mock_config, mock_klippy_apis):
        """Test parsing single enabled pin."""
        mock_server = mock_config.get_server()
        mock_server.lookup_component = Mock(return_value=mock_klippy_apis)
        mock_config.get = Mock(return_value='PIN1')
        
        monitor = GPIO_Monitor(mock_config)
        
        assert monitor.enabled_pins == ['PIN1']
    
    def test_parse_multiple_enabled_pins(self, mock_config, mock_klippy_apis):
        """Test parsing multiple enabled pins."""
        mock_server = mock_config.get_server()
        mock_server.lookup_component = Mock(return_value=mock_klippy_apis)
        mock_config.get = Mock(return_value='PIN1, PIN2, PIN3')
        
        monitor = GPIO_Monitor(mock_config)
        
        assert monitor.enabled_pins == ['PIN1', 'PIN2', 'PIN3']
    
    def test_parse_pins_with_whitespace(self, mock_config, mock_klippy_apis):
        """Test parsing pins with extra whitespace."""
        mock_server = mock_config.get_server()
        mock_server.lookup_component = Mock(return_value=mock_klippy_apis)
        mock_config.get = Mock(return_value='  PIN1  ,  PIN2  ,  PIN3  ')
        
        monitor = GPIO_Monitor(mock_config)
        
        assert monitor.enabled_pins == ['PIN1', 'PIN2', 'PIN3']


class TestQueryGPIOStates:
    """Test GPIO state querying."""
    
    @pytest.mark.asyncio
    async def test_query_all_gpio_states(self, gpio_monitor, mock_klippy_apis):
        """Test querying all GPIO states."""
        mock_klippy_apis.query_objects = AsyncMock(return_value={
            'result': {
                'output_pin': {
                    'PIN1': {'value': 1, 'is_pwm': False, 'scale': 1.0},
                    'PIN2': {'value': 0, 'is_pwm': True, 'scale': 1.0},
                    'PIN3': {'value': 0.5, 'is_pwm': True, 'scale': 2.0}
                }
            }
        })
        
        result = await gpio_monitor._query_gpio_states()
        
        assert 'inputs' in result
        assert 'timestamp' in result
        assert len(result['inputs']) == 3
        assert result['inputs']['PIN1']['value'] == 1
        assert result['inputs']['PIN2']['is_pwm'] == True
        assert result['inputs']['PIN3']['scale'] == 2.0
    
    @pytest.mark.asyncio
    async def test_query_filtered_gpio_states(self, gpio_monitor, mock_klippy_apis):
        """Test querying filtered GPIO states."""
        gpio_monitor.enabled_pins = ['PIN1', 'PIN3']
        mock_klippy_apis.query_objects = AsyncMock(return_value={
            'result': {
                'output_pin': {
                    'PIN1': {'value': 1, 'is_pwm': False, 'scale': 1.0},
                    'PIN2': {'value': 0, 'is_pwm': True, 'scale': 1.0},
                    'PIN3': {'value': 0.5, 'is_pwm': True, 'scale': 2.0}
                }
            }
        })
        
        result = await gpio_monitor._query_gpio_states()
        
        assert len(result['inputs']) == 2
        assert 'PIN1' in result['inputs']
        assert 'PIN3' in result['inputs']
        assert 'PIN2' not in result['inputs']
    
    @pytest.mark.asyncio
    async def test_query_gpio_states_invalid_response(self, gpio_monitor, mock_klippy_apis):
        """Test querying GPIO states with invalid response."""
        mock_klippy_apis.query_objects = AsyncMock(return_value={'error': 'Invalid request'})
        
        with pytest.raises(Exception) as exc_info:
            await gpio_monitor._query_gpio_states()
        
        assert 'Invalid response from Klipper API' in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_query_gpio_states_no_output_pins(self, gpio_monitor, mock_klippy_apis):
        """Test querying GPIO states when no output pins exist."""
        mock_klippy_apis.query_objects = AsyncMock(return_value={
            'result': {}
        })
        
        result = await gpio_monitor._query_gpio_states()
        
        assert result['inputs'] == {}
        assert 'timestamp' in result


class TestHandleGetGPIOInputs:
    """Test GET handler for all GPIO inputs."""
    
    @pytest.mark.asyncio
    async def test_handle_get_gpio_inputs_success(self, gpio_monitor, mock_klippy_apis):
        """Test successful GET request for all GPIO inputs."""
        mock_klippy_apis.query_objects = AsyncMock(return_value={
            'result': {
                'output_pin': {
                    'PIN1': {'value': 1, 'is_pwm': False, 'scale': 1.0}
                }
            }
        })
        
        web_request = Mock()
        result = await gpio_monitor._handle_get_gpio_inputs(web_request)
        
        assert result['success'] == True
        assert 'inputs' in result
        assert 'timestamp' in result
        assert len(result['inputs']) == 1
    
    @pytest.mark.asyncio
    async def test_handle_get_gpio_inputs_error(self, gpio_monitor, mock_klippy_apis):
        """Test GET request with error."""
        mock_klippy_apis.query_objects = AsyncMock(side_effect=Exception('Query failed'))
        
        web_request = Mock()
        result = await gpio_monitor._handle_get_gpio_inputs(web_request)
        
        assert result['success'] == False
        assert 'error' in result
        assert result['inputs'] == {}


class TestHandleGetGPIOInput:
    """Test GET handler for specific GPIO input."""
    
    @pytest.mark.asyncio
    async def test_handle_get_gpio_input_success(self, gpio_monitor, mock_klippy_apis):
        """Test successful GET request for specific GPIO input."""
        mock_klippy_apis.query_objects = AsyncMock(return_value={
            'result': {
                'output_pin': {
                    'PIN1': {'value': 1, 'is_pwm': False, 'scale': 1.0}
                }
            }
        })
        
        web_request = Mock()
        web_request.get_str = Mock(return_value='PIN1')
        
        result = await gpio_monitor._handle_get_gpio_input(web_request)
        
        assert result['success'] == True
        assert result['pin'] == 'PIN1'
        assert 'state' in result
        assert 'timestamp' in result
    
    @pytest.mark.asyncio
    async def test_handle_get_gpio_input_missing_pin_name(self, gpio_monitor):
        """Test GET request with missing pin name."""
        web_request = Mock()
        web_request.get_str = Mock(return_value='')
        
        result = await gpio_monitor._handle_get_gpio_input(web_request)
        
        assert result['success'] == False
        assert 'error' in result
        assert 'Pin name is required' in result['error']
    
    @pytest.mark.asyncio
    async def test_handle_get_gpio_input_pin_not_found(self, gpio_monitor, mock_klippy_apis):
        """Test GET request for non-existent pin."""
        mock_klippy_apis.query_objects = AsyncMock(return_value={
            'result': {
                'output_pin': {
                    'PIN1': {'value': 1, 'is_pwm': False, 'scale': 1.0}
                }
            }
        })
        
        web_request = Mock()
        web_request.get_str = Mock(return_value='PIN2')
        
        result = await gpio_monitor._handle_get_gpio_input(web_request)
        
        assert result['success'] == False
        assert 'error' in result
        assert 'not found' in result['error']
        assert result['pin'] == 'PIN2'
    
    @pytest.mark.asyncio
    async def test_handle_get_gpio_input_error(self, gpio_monitor, mock_klippy_apis):
        """Test GET request with error."""
        mock_klippy_apis.query_objects = AsyncMock(side_effect=Exception('Query failed'))
        
        web_request = Mock()
        web_request.get_str = Mock(return_value='PIN1')
        
        result = await gpio_monitor._handle_get_gpio_input(web_request)
        
        assert result['success'] == False
        assert 'error' in result
        assert result['pin'] == 'PIN1'


class TestGetStatus:
    """Test get_status method."""
    
    def test_get_status(self, gpio_monitor):
        """Test getting component status."""
        gpio_monitor.enabled_pins = ['PIN1', 'PIN2']
        gpio_monitor.poll_interval = 200
        
        status = gpio_monitor.get_status(123456.789)
        
        assert status['enabled_pins'] == ['PIN1', 'PIN2']
        assert status['poll_interval'] == 200
        assert status['component'] == 'gpio_monitor'


class TestClose:
    """Test close method."""
    
    def test_close(self, gpio_monitor):
        """Test closing the component."""
        # Should not raise any exception
        gpio_monitor.close()
        assert True


class TestLoadComponent:
    """Test load_component function."""
    
    def test_load_component(self, mock_config, mock_klippy_apis):
        """Test loading component via load_component function."""
        from moonraker_extensions.gpio_monitor import load_component
        
        mock_server = mock_config.get_server()
        mock_server.lookup_component = Mock(return_value=mock_klippy_apis)
        
        monitor = load_component(mock_config)
        
        assert isinstance(monitor, GPIO_Monitor)
        assert monitor.server is not None
