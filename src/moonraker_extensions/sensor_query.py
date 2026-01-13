#!/usr/bin/env python3
# Sensor Query Component for Moonraker
# Provides sensor data query capabilities for KlipperPlace

import logging
import time
from typing import Dict, Any, Optional, List

# Moonraker imports
from moonraker import Server

# Component logging
logger = logging.getLogger(__name__)


class SensorQuery:
    """Moonraker component for querying sensor data."""
    
    # Supported sensor types in Klipper
    SENSOR_TYPES = {
        # Temperature sensors
        'temperature_sensor',
        'heater',
        'temperature_fan',
        'bme280',
        'htu21d',
        'lm75',
        'rpi_temperature',
        'temperature_host',
        # Force/load sensors
        'load_cell',
        'load_cell_probe',
        # Motion sensors
        'adxl345',
        'angle',
        'motion_report',
        # Filament sensors
        'hall_filament_width_sensor',
        'filament_switch_sensor',
        'filament_motion_sensor',
        # Other sensors
        'tmc2209',
        'tmc2660',
        'tmc5160',
        'tmc2240',
        'resonance_tester',
        'probe',
        'bed_mesh',
        'endstop',
        'gcode_macro',
        'gcode_button',
        'temperature_mcu',
        'adc_scaled',
        'angle_sensor'
    }
    
    def __init__(self, config: Any) -> None:
        """Initialize the Sensor Query component.
        
        Args:
            config: Moonraker configuration object
        """
        self.server = config.get_server()
        self.klippy_apis = self.server.lookup_component('klippy_apis')
        
        # Read configuration
        self.enabled_sensors = self._parse_enabled_sensors(config)
        self.include_timestamp = config.getboolean('include_timestamp', True)
        self.flatten_response = config.getboolean('flatten_response', False)
        
        # Register REST endpoints
        self.server.register_endpoint(
            "/api/sensor_query/all",
            ['GET'],
            self._handle_get_all_sensors
        )
        
        self.server.register_endpoint(
            "/api/sensor_query/type/{sensor_type}",
            ['GET'],
            self._handle_get_sensor_type
        )
        
        self.server.register_endpoint(
            "/api/sensor_query/{sensor_name}",
            ['GET'],
            self._handle_get_sensor
        )
        
        logger.info(f"Sensor Query initialized with {len(self.enabled_sensors)} enabled sensors")
    
    def _parse_enabled_sensors(self, config: Any) -> List[str]:
        """Parse enabled sensors from configuration.
        
        Args:
            config: Moonraker configuration object
            
        Returns:
            List of enabled sensor names/types
        """
        sensors_str = config.get('enabled_sensors', '')
        if not sensors_str:
            logger.info("No specific sensors configured, will query all available sensors")
            return []
        
        # Parse comma-separated list
        sensors = [sensor.strip() for sensor in sensors_str.split(',') if sensor.strip()]
        logger.info(f"Configured enabled sensors: {sensors}")
        return sensors
    
    async def _handle_get_all_sensors(self, web_request: Any) -> Dict[str, Any]:
        """Handle GET request for all sensors.
        
        Args:
            web_request: Moonraker web request object
            
        Returns:
            Dictionary containing all sensor data
        """
        try:
            # Query all available sensors
            result = await self._query_all_sensors()
            
            return {
                'success': True,
                **result
            }
        except Exception as e:
            logger.error(f"Error querying all sensors: {e}")
            return {
                'success': False,
                'error': str(e),
                'sensors': {}
            }
    
    async def _handle_get_sensor_type(self, web_request: Any) -> Dict[str, Any]:
        """Handle GET request for specific sensor type.
        
        Args:
            web_request: Moonraker web request object
            
        Returns:
            Dictionary containing sensor type data
        """
        try:
            # Extract sensor type from URL path
            sensor_type = web_request.get_str('sensor_type')
            
            if not sensor_type:
                return {
                    'success': False,
                    'error': 'Sensor type is required'
                }
            
            # Validate sensor type
            if sensor_type not in self.SENSOR_TYPES:
                return {
                    'success': False,
                    'error': f'Unknown sensor type: {sensor_type}',
                    'available_types': sorted(list(self.SENSOR_TYPES))
                }
            
            # Query sensors of this type
            result = await self._query_sensor_type(sensor_type)
            
            return {
                'success': True,
                **result
            }
        except Exception as e:
            logger.error(f"Error querying sensor type {sensor_type}: {e}")
            return {
                'success': False,
                'error': str(e),
                'sensors': {}
            }
    
    async def _handle_get_sensor(self, web_request: Any) -> Dict[str, Any]:
        """Handle GET request for specific sensor.
        
        Args:
            web_request: Moonraker web request object
            
        Returns:
            Dictionary containing specific sensor data
        """
        try:
            # Extract sensor name from URL path
            sensor_name = web_request.get_str('sensor_name')
            
            if not sensor_name:
                return {
                    'success': False,
                    'error': 'Sensor name is required'
                }
            
            # Query all sensors and filter for requested sensor
            result = await self._query_all_sensors()
            
            # Search for sensor in all sensor types
            sensor_data = None
            sensor_type = None
            
            for stype, sensors in result['sensors'].items():
                if sensor_name in sensors:
                    sensor_data = sensors[sensor_name]
                    sensor_type = stype
                    break
            
            if sensor_data is None:
                return {
                    'success': False,
                    'error': f'Sensor {sensor_name} not found',
                    'sensor': sensor_name
                }
            
            response = {
                'success': True,
                'sensor': sensor_name,
                'type': sensor_type,
                'data': sensor_data
            }
            
            if self.include_timestamp:
                response['timestamp'] = result['timestamp']
            
            return response
        except Exception as e:
            logger.error(f"Error querying sensor {sensor_name}: {e}")
            return {
                'success': False,
                'error': str(e),
                'sensor': sensor_name
            }
    
    async def _query_all_sensors(self) -> Dict[str, Any]:
        """Query Klipper for all available sensors.
        
        Returns:
            Dictionary containing all sensor data
            
        Raises:
            Exception: If query fails
        """
        timestamp = time.time()
        
        # Build query objects for all supported sensor types
        query_objects = {}
        
        if self.enabled_sensors:
            # If specific sensors are configured, only query those types
            for sensor in self.enabled_sensors:
                if sensor in self.SENSOR_TYPES:
                    query_objects[sensor] = None
                else:
                    # Could be a specific sensor name, try to query all types
                    query_objects = {stype: None for stype in self.SENSOR_TYPES}
                    break
        else:
            # Query all supported sensor types
            query_objects = {stype: None for stype in self.SENSOR_TYPES}
        
        # Query Klipper for sensor data
        try:
            query_result = await self.klippy_apis.query_objects(query_objects)
            
            if 'result' not in query_result:
                raise Exception("Invalid response from Klipper API")
            
            klipper_result = query_result['result']
            
            # Extract sensor data from the result
            sensors = {}
            
            for sensor_type in self.SENSOR_TYPES:
                if sensor_type in klipper_result:
                    sensor_data = klipper_result[sensor_type]
                    
                    # If specific sensors are configured, filter for those
                    if self.enabled_sensors:
                        filtered_data = {}
                        for sensor_name in self.enabled_sensors:
                            if sensor_name in sensor_data:
                                filtered_data[sensor_name] = sensor_data[sensor_name]
                        
                        if filtered_data:
                            sensors[sensor_type] = filtered_data
                    else:
                        # Return all sensors of this type
                        if sensor_data:
                            sensors[sensor_type] = sensor_data
            
            response = {
                'sensors': sensors
            }
            
            if self.include_timestamp:
                response['timestamp'] = timestamp
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to query Klipper for sensor data: {e}")
            raise
    
    async def _query_sensor_type(self, sensor_type: str) -> Dict[str, Any]:
        """Query Klipper for specific sensor type.
        
        Args:
            sensor_type: Type of sensor to query
            
        Returns:
            Dictionary containing sensor type data
            
        Raises:
            Exception: If query fails
        """
        timestamp = time.time()
        
        # Query Klipper for specific sensor type
        try:
            query_result = await self.klippy_apis.query_objects({sensor_type: None})
            
            if 'result' not in query_result:
                raise Exception("Invalid response from Klipper API")
            
            klipper_result = query_result['result']
            
            # Extract sensor data
            sensors = {}
            
            if sensor_type in klipper_result:
                sensor_data = klipper_result[sensor_type]
                
                # If specific sensors are configured, filter for those
                if self.enabled_sensors:
                    filtered_data = {}
                    for sensor_name in self.enabled_sensors:
                        if sensor_name in sensor_data:
                            filtered_data[sensor_name] = sensor_data[sensor_name]
                    
                    sensors = filtered_data
                else:
                    # Return all sensors of this type
                    if sensor_data:
                        sensors = sensor_data
            
            response = {
                'sensor_type': sensor_type,
                'sensors': sensors
            }
            
            if self.include_timestamp:
                response['timestamp'] = timestamp
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to query Klipper for sensor type {sensor_type}: {e}")
            raise
    
    def get_status(self, eventtime: float) -> Dict[str, Any]:
        """Get component status for Moonraker status reporting.
        
        Args:
            eventtime: Current event time
            
        Returns:
            Dictionary containing component status
        """
        return {
            'enabled_sensors': self.enabled_sensors,
            'include_timestamp': self.include_timestamp,
            'flatten_response': self.flatten_response,
            'component': 'sensor_query'
        }
    
    def close(self) -> None:
        """Cleanup when component is closed."""
        logger.info("Sensor Query component closed")


def load_component(config: Any) -> SensorQuery:
    """Load the Sensor Query component.
    
    This function is called by Moonraker to load the component.
    
    Args:
        config: Moonraker configuration object
        
    Returns:
        Instance of SensorQuery component
    """
    return SensorQuery(config)
