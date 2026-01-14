#!/usr/bin/env python3
# Unit tests for Sensor Query component

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock


class SensorQuery:
    """Mock SensorQuery class for testing."""
    
    def __init__(self, config):
        self.server = config.get_server()
        self.klippy_apis = self.server.lookup_component('klippy_apis')
        self.enabled_sensors = []
        self.include_timestamp = True
        self.flatten_response = False


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
    config.getboolean = Mock(side_effect=lambda key, default=True: default)
    config.get = Mock(return_value='')
    return config


@pytest.fixture
def mock_klippy_apis():
    """Create a mock Klippy APIs object."""
    apis = Mock()
    apis.query_objects = AsyncMock()
    return apis


@pytest.fixture
def sensor_query(mock_config, mock_klippy_apis):
    """Create a SensorQuery instance for testing."""
    mock_server = mock_config.get_server()
    mock_server.lookup_component = Mock(return_value=mock_klippy_apis)
    
    query = SensorQuery(mock_config)
    return query


class TestSensorQueryInitialization:
    """Test SensorQuery initialization."""
    
    def test_initialization_with_defaults(self, mock_config, mock_klippy_apis):
        """Test initialization with default configuration."""
        mock_server = mock_config.get_server()
        mock_server.lookup_component = Mock(return_value=mock_klippy_apis)
        
        query = SensorQuery(mock_config)
        
        assert query.server is not None
        assert query.klippy_apis is not None
        assert query.enabled_sensors == []
        assert query.include_timestamp == True
        assert query.flatten_response == False
    
    def test_initialization_with_enabled_sensors(self, mock_config, mock_klippy_apis):
        """Test initialization with enabled sensors."""
        mock_server = mock_config.get_server()
        mock_server.lookup_component = Mock(return_value=mock_klippy_apis)
        mock_config.get = Mock(return_value='temperature_sensor,heater,load_cell')
        
        query = SensorQuery(mock_config)
        
        assert query.enabled_sensors == ['temperature_sensor', 'heater', 'load_cell']
    
    def test_initialization_with_timestamp_disabled(self, mock_config, mock_klippy_apis):
        """Test initialization with timestamp disabled."""
        mock_server = mock_config.get_server()
        mock_server.lookup_component = Mock(return_value=mock_klippy_apis)
        mock_config.getboolean = Mock(side_effect=lambda key, default=True: False if key == 'include_timestamp' else True)
        
        query = SensorQuery(mock_config)
        
        assert query.include_timestamp == False
    
    def test_endpoint_registration(self, mock_config, mock_klippy_apis):
        """Test that REST endpoints are registered."""
        mock_server = mock_config.get_server()
        mock_server.lookup_component = Mock(return_value=mock_klippy_apis)
        
        SensorQuery(mock_config)
        
        assert mock_server.register_endpoint.call_count == 3
        calls = mock_server.register_endpoint.call_args_list
        
        # Check endpoints
        endpoints = [call[0][0] for call in calls]
        assert '/api/sensor_query/all' in endpoints
        assert '/api/sensor_query/type/{sensor_type}' in endpoints
        assert '/api/sensor_query/{sensor_name}' in endpoints


class TestParseEnabledSensors:
    """Test parsing of enabled sensors configuration."""
    
    def test_parse_empty_enabled_sensors(self, mock_config, mock_klippy_apis):
        """Test parsing empty enabled sensors."""
        mock_server = mock_config.get_server()
        mock_server.lookup_component = Mock(return_value=mock_klippy_apis)
        mock_config.get = Mock(return_value='')
        
        query = SensorQuery(mock_config)
        
        assert query.enabled_sensors == []
    
    def test_parse_single_sensor(self, mock_config, mock_klippy_apis):
        """Test parsing single enabled sensor."""
        mock_server = mock_config.get_server()
        mock_server.lookup_component = Mock(return_value=mock_klippy_apis)
        mock_config.get = Mock(return_value='temperature_sensor')
        
        query = SensorQuery(mock_config)
        
        assert query.enabled_sensors == ['temperature_sensor']
    
    def test_parse_multiple_sensors(self, mock_config, mock_klippy_apis):
        """Test parsing multiple enabled sensors."""
        mock_server = mock_config.get_server()
        mock_server.lookup_component = Mock(return_value=mock_klippy_apis)
        mock_config.get = Mock(return_value='temperature_sensor, heater, load_cell, adxl345')
        
        query = SensorQuery(mock_config)
        
        assert query.enabled_sensors == ['temperature_sensor', 'heater', 'load_cell', 'adxl345']
    
    def test_parse_sensors_with_whitespace(self, mock_config, mock_klippy_apis):
        """Test parsing sensors with extra whitespace."""
        mock_server = mock_config.get_server()
        mock_server.lookup_component = Mock(return_value=mock_klippy_apis)
        mock_config.get = Mock(return_value='  temperature_sensor  ,  heater  ,  load_cell  ')
        
        query = SensorQuery(mock_config)
        
        assert query.enabled_sensors == ['temperature_sensor', 'heater', 'load_cell']


class TestHandleGetAllSensors:
    """Test handler for getting all sensors."""
    
    @pytest.mark.asyncio
    async def test_get_all_sensors_success(self, sensor_query, mock_klippy_apis):
        """Test successful query for all sensors."""
        mock_klippy_apis.query_objects = AsyncMock(return_value={
            'result': {
                'temperature_sensor': {
                    'sensor1': {'temperature': 25.5},
                    'sensor2': {'temperature': 30.0}
                },
                'heater': {
                    'extruder': {'temperature': 200.0, 'target': 210.0}
                }
            }
        })
        
        web_request = Mock()
        result = await sensor_query._handle_get_all_sensors(web_request)
        
        assert result['success'] == True
        assert 'sensors' in result
        assert 'timestamp' in result
    
    @pytest.mark.asyncio
    async def test_get_all_sensors_error(self, sensor_query, mock_klippy_apis):
        """Test query for all sensors with error."""
        mock_klippy_apis.query_objects = AsyncMock(side_effect=Exception('Query failed'))
        
        web_request = Mock()
        result = await sensor_query._handle_get_all_sensors(web_request)
        
        assert result['success'] == False
        assert 'error' in result
        assert result['sensors'] == {}


class TestHandleGetSensorType:
    """Test handler for getting sensors by type."""
    
    @pytest.mark.asyncio
    async def test_get_sensor_type_success(self, sensor_query, mock_klippy_apis):
        """Test successful query for sensor type."""
        mock_klippy_apis.query_objects = AsyncMock(return_value={
            'result': {
                'temperature_sensor': {
                    'sensor1': {'temperature': 25.5},
                    'sensor2': {'temperature': 30.0}
                }
            }
        })
        
        web_request = Mock()
        web_request.get_str = Mock(return_value='temperature_sensor')
        
        result = await sensor_query._handle_get_sensor_type(web_request)
        
        assert result['success'] == True
        assert 'sensor_type' in result
        assert result['sensor_type'] == 'temperature_sensor'
        assert 'sensors' in result
    
    @pytest.mark.asyncio
    async def test_get_sensor_type_missing_type(self, sensor_query):
        """Test query with missing sensor type."""
        web_request = Mock()
        web_request.get_str = Mock(return_value='')
        
        result = await sensor_query._handle_get_sensor_type(web_request)
        
        assert result['success'] == False
        assert 'error' in result
        assert 'Sensor type is required' in result['error']
    
    @pytest.mark.asyncio
    async def test_get_sensor_type_invalid_type(self, sensor_query):
        """Test query with invalid sensor type."""
        web_request = Mock()
        web_request.get_str = Mock(return_value='invalid_sensor_type')
        
        result = await sensor_query._handle_get_sensor_type(web_request)
        
        assert result['success'] == False
        assert 'error' in result
        assert 'Unknown sensor type' in result['error']
        assert 'available_types' in result
    
    @pytest.mark.asyncio
    async def test_get_sensor_type_error(self, sensor_query, mock_klippy_apis):
        """Test query for sensor type with error."""
        mock_klippy_apis.query_objects = AsyncMock(side_effect=Exception('Query failed'))
        
        web_request = Mock()
        web_request.get_str = Mock(return_value='temperature_sensor')
        
        result = await sensor_query._handle_get_sensor_type(web_request)
        
        assert result['success'] == False
        assert 'error' in result


class TestHandleGetSensor:
    """Test handler for getting specific sensor."""
    
    @pytest.mark.asyncio
    async def test_get_sensor_success(self, sensor_query, mock_klippy_apis):
        """Test successful query for specific sensor."""
        mock_klippy_apis.query_objects = AsyncMock(return_value={
            'result': {
                'temperature_sensor': {
                    'sensor1': {'temperature': 25.5}
                }
            }
        })
        
        web_request = Mock()
        web_request.get_str = Mock(return_value='sensor1')
        
        result = await sensor_query._handle_get_sensor(web_request)
        
        assert result['success'] == True
        assert result['sensor'] == 'sensor1'
        assert 'type' in result
        assert 'data' in result
        assert 'timestamp' in result
    
    @pytest.mark.asyncio
    async def test_get_sensor_missing_name(self, sensor_query):
        """Test query with missing sensor name."""
        web_request = Mock()
        web_request.get_str = Mock(return_value='')
        
        result = await sensor_query._handle_get_sensor(web_request)
        
        assert result['success'] == False
        assert 'error' in result
        assert 'Sensor name is required' in result['error']
    
    @pytest.mark.asyncio
    async def test_get_sensor_not_found(self, sensor_query, mock_klippy_apis):
        """Test query for non-existent sensor."""
        mock_klippy_apis.query_objects = AsyncMock(return_value={
            'result': {
                'temperature_sensor': {
                    'sensor1': {'temperature': 25.5}
                }
            }
        })
        
        web_request = Mock()
        web_request.get_str = Mock(return_value='nonexistent_sensor')
        
        result = await sensor_query._handle_get_sensor(web_request)
        
        assert result['success'] == False
        assert 'error' in result
        assert 'not found' in result['error']
    
    @pytest.mark.asyncio
    async def test_get_sensor_without_timestamp(self, sensor_query, mock_klippy_apis):
        """Test query with timestamp disabled."""
        sensor_query.include_timestamp = False
        mock_klippy_apis.query_objects = AsyncMock(return_value={
            'result': {
                'temperature_sensor': {
                    'sensor1': {'temperature': 25.5}
                }
            }
        })
        
        web_request = Mock()
        web_request.get_str = Mock(return_value='sensor1')
        
        result = await sensor_query._handle_get_sensor(web_request)
        
        assert result['success'] == True
        assert 'timestamp' not in result


class TestQueryAllSensors:
    """Test querying all sensors."""
    
    @pytest.mark.asyncio
    async def test_query_all_sensors(self, sensor_query, mock_klippy_apis):
        """Test querying all sensors."""
        mock_klippy_apis.query_objects = AsyncMock(return_value={
            'result': {
                'temperature_sensor': {
                    'sensor1': {'temperature': 25.5}
                },
                'heater': {
                    'extruder': {'temperature': 200.0}
                }
            }
        })
        
        result = await sensor_query._query_all_sensors()
        
        assert 'sensors' in result
        assert 'timestamp' in result
        assert 'temperature_sensor' in result['sensors']
        assert 'heater' in result['sensors']
    
    @pytest.mark.asyncio
    async def test_query_all_sensors_with_filter(self, sensor_query, mock_klippy_apis):
        """Test querying all sensors with enabled filter."""
        sensor_query.enabled_sensors = ['sensor1']
        mock_klippy_apis.query_objects = AsyncMock(return_value={
            'result': {
                'temperature_sensor': {
                    'sensor1': {'temperature': 25.5},
                    'sensor2': {'temperature': 30.0}
                }
            }
        })
        
        result = await sensor_query._query_all_sensors()
        
        assert 'sensors' in result
        assert 'sensor1' in result['sensors']['temperature_sensor']
        assert 'sensor2' not in result['sensors']['temperature_sensor']
    
    @pytest.mark.asyncio
    async def test_query_all_sensors_invalid_response(self, sensor_query, mock_klippy_apis):
        """Test querying all sensors with invalid response."""
        mock_klippy_apis.query_objects = AsyncMock(return_value={'error': 'Invalid'})
        
        with pytest.raises(Exception) as exc_info:
            await sensor_query._query_all_sensors()
        
        assert 'Invalid response from Klipper API' in str(exc_info.value)


class TestQuerySensorType:
    """Test querying sensors by type."""
    
    @pytest.mark.asyncio
    async def test_query_sensor_type(self, sensor_query, mock_klippy_apis):
        """Test querying sensors by type."""
        mock_klippy_apis.query_objects = AsyncMock(return_value={
            'result': {
                'temperature_sensor': {
                    'sensor1': {'temperature': 25.5},
                    'sensor2': {'temperature': 30.0}
                }
            }
        })
        
        result = await sensor_query._query_sensor_type('temperature_sensor')
        
        assert 'sensor_type' in result
        assert 'sensors' in result
        assert 'timestamp' in result
        assert result['sensor_type'] == 'temperature_sensor'
    
    @pytest.mark.asyncio
    async def test_query_sensor_type_with_filter(self, sensor_query, mock_klippy_apis):
        """Test querying sensor type with enabled filter."""
        sensor_query.enabled_sensors = ['sensor1']
        mock_klippy_apis.query_objects = AsyncMock(return_value={
            'result': {
                'temperature_sensor': {
                    'sensor1': {'temperature': 25.5},
                    'sensor2': {'temperature': 30.0}
                }
            }
        })
        
        result = await sensor_query._query_sensor_type('temperature_sensor')
        
        assert 'sensor1' in result['sensors']
        assert 'sensor2' not in result['sensors']


class TestGetStatus:
    """Test get_status method."""
    
    def test_get_status(self, sensor_query):
        """Test getting component status."""
        sensor_query.enabled_sensors = ['temperature_sensor', 'heater']
        sensor_query.include_timestamp = True
        sensor_query.flatten_response = False
        
        status = sensor_query.get_status(123456.789)
        
        assert status['enabled_sensors'] == ['temperature_sensor', 'heater']
        assert status['include_timestamp'] == True
        assert status['flatten_response'] == False
        assert status['component'] == 'sensor_query'


class TestClose:
    """Test close method."""
    
    def test_close(self, sensor_query):
        """Test closing component."""
        # Should not raise any exception
        sensor_query.close()
        assert True


class TestLoadComponent:
    """Test load_component function."""
    
    def test_load_component(self, mock_config, mock_klippy_apis):
        """Test loading component via load_component function."""
        from moonraker_extensions.sensor_query import load_component
        
        mock_server = mock_config.get_server()
        mock_server.lookup_component = Mock(return_value=mock_klippy_apis)
        
        query = load_component(mock_config)
        
        assert isinstance(query, SensorQuery)
        assert query.server is not None
