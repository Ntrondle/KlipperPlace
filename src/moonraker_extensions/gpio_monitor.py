#!/usr/bin/env python3
# GPIO Monitor Component for Moonraker
# Provides GPIO state reading capabilities for KlipperPlace

import logging
from typing import Dict, List, Optional, Any

# Moonraker imports
from moonraker import Server

# Component logging
logger = logging.getLogger(__name__)


class GPIO_Monitor:
    """Moonraker component for monitoring GPIO pin states."""
    
    def __init__(self, config: Any) -> None:
        """Initialize the GPIO Monitor component.
        
        Args:
            config: Moonraker configuration object
        """
        self.server = config.get_server()
        self.klippy_apis = self.server.lookup_component('klippy_apis')
        
        # Read configuration
        self.enabled_pins = self._parse_enabled_pins(config)
        self.poll_interval = config.getint('poll_interval', 100, minval=10, maxval=5000)
        
        # Register REST endpoint
        self.server.register_endpoint(
            "/api/gpio_monitor/inputs",
            ['GET'],
            self._handle_get_gpio_inputs
        )
        
        # Register endpoint for specific pin query
        self.server.register_endpoint(
            "/api/gpio_monitor/input/{pin_name}",
            ['GET'],
            self._handle_get_gpio_input
        )
        
        logger.info(f"GPIO Monitor initialized with {len(self.enabled_pins)} enabled pins")
    
    def _parse_enabled_pins(self, config: Any) -> List[str]:
        """Parse enabled pins from configuration.
        
        Args:
            config: Moonraker configuration object
            
        Returns:
            List of enabled pin names
        """
        pins_str = config.get('enabled_pins', '')
        if not pins_str:
            logger.info("No specific pins configured, will query all available GPIO pins")
            return []
        
        # Parse comma-separated list
        pins = [pin.strip() for pin in pins_str.split(',') if pin.strip()]
        logger.info(f"Configured enabled pins: {pins}")
        return pins
    
    async def _handle_get_gpio_inputs(self, web_request: Any) -> Dict[str, Any]:
        """Handle GET request for GPIO input states.
        
        Args:
            web_request: Moonraker web request object
            
        Returns:
            Dictionary containing GPIO pin states
        """
        try:
            # Query Klipper for GPIO pin states
            result = await self._query_gpio_states()
            
            return {
                'success': True,
                'inputs': result['inputs'],
                'timestamp': result['timestamp']
            }
        except Exception as e:
            logger.error(f"Error querying GPIO inputs: {e}")
            return {
                'success': False,
                'error': str(e),
                'inputs': {}
            }
    
    async def _handle_get_gpio_input(self, web_request: Any) -> Dict[str, Any]:
        """Handle GET request for specific GPIO pin state.
        
        Args:
            web_request: Moonraker web request object
            
        Returns:
            Dictionary containing specific pin state
        """
        try:
            # Extract pin name from URL path
            pin_name = web_request.get_str('pin_name')
            
            if not pin_name:
                return {
                    'success': False,
                    'error': 'Pin name is required'
                }
            
            # Query all GPIO states and filter for requested pin
            result = await self._query_gpio_states()
            
            if pin_name not in result['inputs']:
                return {
                    'success': False,
                    'error': f'Pin {pin_name} not found',
                    'pin': pin_name
                }
            
            return {
                'success': True,
                'pin': pin_name,
                'state': result['inputs'][pin_name],
                'timestamp': result['timestamp']
            }
        except Exception as e:
            logger.error(f"Error querying GPIO input {pin_name}: {e}")
            return {
                'success': False,
                'error': str(e),
                'pin': pin_name
            }
    
    async def _query_gpio_states(self) -> Dict[str, Any]:
        """Query Klipper for GPIO pin states.
        
        Returns:
            Dictionary containing GPIO pin states and timestamp
            
        Raises:
            Exception: If query fails
        """
        import time
        import json
        
        timestamp = time.time()
        
        # Query Klipper for output_pin objects (these are the GPIO pins we can monitor)
        try:
            # Query all output_pin objects
            query_result = await self.klippy_apis.query_objects({'output_pin': None})
            
            if 'result' not in query_result:
                raise Exception("Invalid response from Klipper API")
            
            klipper_result = query_result['result']
            
            # Extract pin states from the result
            inputs = {}
            
            # output_pin objects in Klipper contain 'value' field
            if 'output_pin' in klipper_result:
                output_pins = klipper_result['output_pin']
                
                # If specific pins are configured, filter for those
                if self.enabled_pins:
                    for pin_name in self.enabled_pins:
                        if pin_name in output_pins:
                            pin_data = output_pins[pin_name]
                            inputs[pin_name] = {
                                'value': pin_data.get('value', 0),
                                'is_pwm': pin_data.get('is_pwm', False),
                                'scale': pin_data.get('scale', 1.0)
                            }
                else:
                    # Return all available output pins
                    for pin_name, pin_data in output_pins.items():
                        inputs[pin_name] = {
                            'value': pin_data.get('value', 0),
                            'is_pwm': pin_data.get('is_pwm', False),
                            'scale': pin_data.get('scale', 1.0)
                        }
            
            return {
                'inputs': inputs,
                'timestamp': timestamp
            }
            
        except Exception as e:
            logger.error(f"Failed to query Klipper for GPIO states: {e}")
            raise
    
    def get_status(self, eventtime: float) -> Dict[str, Any]:
        """Get component status for Moonraker status reporting.
        
        Args:
            eventtime: Current event time
            
        Returns:
            Dictionary containing component status
        """
        return {
            'enabled_pins': self.enabled_pins,
            'poll_interval': self.poll_interval,
            'component': 'gpio_monitor'
        }
    
    def close(self) -> None:
        """Cleanup when component is closed."""
        logger.info("GPIO Monitor component closed")


def load_component(config: Any) -> GPIO_Monitor:
    """Load the GPIO Monitor component.
    
    This function is called by Moonraker to load the component.
    
    Args:
        config: Moonraker configuration object
        
    Returns:
        Instance of GPIO_Monitor component
    """
    return GPIO_Monitor(config)
