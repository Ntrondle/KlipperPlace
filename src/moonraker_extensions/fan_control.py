#!/usr/bin/env python3
# Fan Control Component for Moonraker
# Provides fan port control capabilities for KlipperPlace

import logging
from typing import Dict, Any, Optional

# Moonraker imports
from moonraker import Server

# Component logging
logger = logging.getLogger(__name__)


class FanControl:
    """Moonraker component for controlling fan ports."""
    
    def __init__(self, config: Any) -> None:
        """Initialize the Fan Control component.
        
        Args:
            config: Moonraker configuration object
        """
        self.server = config.get_server()
        self.klippy_apis = self.server.lookup_component('klippy_apis')
        
        # Read configuration
        self.default_speed = config.getfloat('default_speed', 0.5, minval=0.0, maxval=1.0)
        self.max_speed = config.getfloat('max_speed', 1.0, minval=0.0, maxval=1.0)
        self.default_fan = config.get('default_fan', 'fan')
        
        # Register REST endpoints
        self.server.register_endpoint(
            "/api/fan_control/set",
            ['POST'],
            self._handle_set_fan
        )
        
        self.server.register_endpoint(
            "/api/fan_control/off",
            ['POST'],
            self._handle_fan_off
        )
        
        self.server.register_endpoint(
            "/api/fan_control/status",
            ['GET'],
            self._handle_get_status
        )
        
        logger.info(f"Fan Control initialized with default_fan={self.default_fan}, "
                   f"default_speed={self.default_speed}, max_speed={self.max_speed}")
    
    async def _handle_set_fan(self, web_request: Any) -> Dict[str, Any]:
        """Handle POST request to set fan speed.
        
        Args:
            web_request: Moonraker web request object
            
        Returns:
            Dictionary containing operation result
        """
        try:
            # Extract parameters
            speed = web_request.get_float('speed')
            fan_name = web_request.get_str('fan_name', self.default_fan)
            
            # Validate speed
            if speed < 0.0 or speed > 1.0:
                return {
                    'success': False,
                    'error': f'Speed must be between 0.0 and 1.0, got {speed}',
                    'fan': fan_name
                }
            
            # Apply max_speed limit
            if speed > self.max_speed:
                speed = self.max_speed
                logger.info(f"Speed limited to max_speed={self.max_speed}")
            
            # Send G-code command to set fan speed
            # Convert 0.0-1.0 to 0-255 for M106
            pwm_value = int(speed * 255)
            
            if fan_name == 'fan':
                # Use standard fan command
                gcode = f"M106 S{pwm_value}"
            else:
                # Use generic fan command
                gcode = f"SET_FAN_SPEED FAN={fan_name} SPEED={speed:.3f}"
            
            result = await self.klippy_apis.run_gcode(gcode)
            
            if result.get('result', {}).get('queued', False):
                logger.info(f"Fan {fan_name} speed set to {speed:.3f} (PWM: {pwm_value})")
                return {
                    'success': True,
                    'fan': fan_name,
                    'speed': speed,
                    'pwm_value': pwm_value,
                    'gcode': gcode
                }
            else:
                raise Exception(f"Failed to queue G-code command: {gcode}")
                
        except Exception as e:
            logger.error(f"Error setting fan speed: {e}")
            return {
                'success': False,
                'error': str(e),
                'fan': fan_name if 'fan_name' in locals() else 'unknown'
            }
    
    async def _handle_fan_off(self, web_request: Any) -> Dict[str, Any]:
        """Handle POST request to turn fan off.
        
        Args:
            web_request: Moonraker web request object
            
        Returns:
            Dictionary containing operation result
        """
        try:
            # Extract parameters
            fan_name = web_request.get_str('fan_name', self.default_fan)
            
            # Send G-code command to turn fan off
            if fan_name == 'fan':
                # Use standard fan off command
                gcode = "M107"
            else:
                # Use generic fan command with speed 0
                gcode = f"SET_FAN_SPEED FAN={fan_name} SPEED=0.0"
            
            result = await self.klippy_apis.run_gcode(gcode)
            
            if result.get('result', {}).get('queued', False):
                logger.info(f"Fan {fan_name} turned off")
                return {
                    'success': True,
                    'fan': fan_name,
                    'speed': 0.0,
                    'gcode': gcode
                }
            else:
                raise Exception(f"Failed to queue G-code command: {gcode}")
                
        except Exception as e:
            logger.error(f"Error turning fan off: {e}")
            return {
                'success': False,
                'error': str(e),
                'fan': fan_name if 'fan_name' in locals() else 'unknown'
            }
    
    async def _handle_get_status(self, web_request: Any) -> Dict[str, Any]:
        """Handle GET request for fan status.
        
        Args:
            web_request: Moonraker web request object
            
        Returns:
            Dictionary containing fan status
        """
        try:
            # Extract parameters
            fan_name = web_request.get_str('fan_name', None)
            
            # Query Klipper for fan status
            result = await self._query_fan_status(fan_name)
            
            return {
                'success': True,
                **result
            }
        except Exception as e:
            logger.error(f"Error querying fan status: {e}")
            return {
                'success': False,
                'error': str(e),
                'fans': {}
            }
    
    async def _query_fan_status(self, fan_name: Optional[str] = None) -> Dict[str, Any]:
        """Query Klipper for fan status.
        
        Args:
            fan_name: Optional specific fan name to query. If None, queries all fans.
            
        Returns:
            Dictionary containing fan status
            
        Raises:
            Exception: If query fails
        """
        import time
        
        timestamp = time.time()
        
        # Query Klipper for fan objects
        try:
            # Query both standard fan and generic fan objects
            query_objects = {
                'fan': None,
                'fan_generic': None
            }
            
            query_result = await self.klippy_apis.query_objects(query_objects)
            
            if 'result' not in query_result:
                raise Exception("Invalid response from Klipper API")
            
            klipper_result = query_result['result']
            
            # Extract fan status from the result
            fans = {}
            
            # Process standard fan
            if 'fan' in klipper_result:
                fan_data = klipper_result['fan']
                if fan_name is None or fan_name == 'fan':
                    fans['fan'] = {
                        'speed': fan_data.get('speed', 0.0),
                        'rpm': fan_data.get('rpm', 0),
                        'power': fan_data.get('power', 0.0)
                    }
            
            # Process generic fans
            if 'fan_generic' in klipper_result:
                generic_fans = klipper_result['fan_generic']
                
                for name, fan_data in generic_fans.items():
                    if fan_name is None or fan_name == name:
                        fans[name] = {
                            'speed': fan_data.get('speed', 0.0),
                            'rpm': fan_data.get('rpm', 0),
                            'power': fan_data.get('power', 0.0)
                        }
            
            # If specific fan was requested but not found
            if fan_name is not None and fan_name not in fans:
                raise Exception(f"Fan '{fan_name}' not found in Klipper configuration")
            
            return {
                'fans': fans,
                'timestamp': timestamp
            }
            
        except Exception as e:
            logger.error(f"Failed to query Klipper for fan status: {e}")
            raise
    
    def get_status(self, eventtime: float) -> Dict[str, Any]:
        """Get component status for Moonraker status reporting.
        
        Args:
            eventtime: Current event time
            
        Returns:
            Dictionary containing component status
        """
        return {
            'default_fan': self.default_fan,
            'default_speed': self.default_speed,
            'max_speed': self.max_speed,
            'component': 'fan_control'
        }
    
    def close(self) -> None:
        """Cleanup when component is closed."""
        logger.info("Fan Control component closed")


def load_component(config: Any) -> FanControl:
    """Load the Fan Control component.
    
    This function is called by Moonraker to load the component.
    
    Args:
        config: Moonraker configuration object
        
    Returns:
        Instance of FanControl component
    """
    return FanControl(config)
