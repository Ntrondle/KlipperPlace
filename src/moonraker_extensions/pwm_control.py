#!/usr/bin/env python3
# PWM Control Component for Moonraker
# Provides PWM output control capabilities for KlipperPlace

import logging
import asyncio
from typing import Dict, Any, Optional

# Moonraker imports
from moonraker import Server

# Component logging
logger = logging.getLogger(__name__)


class PWMControl:
    """Moonraker component for controlling PWM output pins."""
    
    def __init__(self, config: Any) -> None:
        """Initialize the PWM Control component.
        
        Args:
            config: Moonraker configuration object
        """
        self.server = config.get_server()
        self.klippy_apis = self.server.lookup_component('klippy_apis')
        
        # Read configuration
        self.default_value = config.getfloat('default_value', 0.0, minval=0.0, maxval=1.0)
        self.ramp_duration = config.getfloat('ramp_duration', 1.0, minval=0.1, maxval=60.0)
        self.ramp_steps = config.getint('ramp_steps', 10, minval=2, maxval=100)
        self.default_pin = config.get('default_pin', None)
        
        # Track active ramp operations
        self.active_ramps = {}
        
        # Register REST endpoints
        self.server.register_endpoint(
            "/api/pwm_control/set",
            ['POST'],
            self._handle_set_pwm
        )
        
        self.server.register_endpoint(
            "/api/pwm_control/ramp",
            ['POST'],
            self._handle_ramp_pwm
        )
        
        self.server.register_endpoint(
            "/api/pwm_control/status",
            ['GET'],
            self._handle_get_status
        )
        
        logger.info(f"PWM Control initialized with default_value={self.default_value}, "
                   f"ramp_duration={self.ramp_duration}, ramp_steps={self.ramp_steps}")
    
    async def _handle_set_pwm(self, web_request: Any) -> Dict[str, Any]:
        """Handle POST request to set PWM value.
        
        Args:
            web_request: Moonraker web request object
            
        Returns:
            Dictionary containing operation result
        """
        try:
            # Extract parameters
            value = web_request.get_float('value')
            pin_name = web_request.get_str('pin_name', self.default_pin)
            
            # Validate pin name
            if not pin_name:
                return {
                    'success': False,
                    'error': 'Pin name is required (provide pin_name parameter or configure default_pin)',
                    'pin': pin_name
                }
            
            # Validate value
            if value < 0.0 or value > 1.0:
                return {
                    'success': False,
                    'error': f'PWM value must be between 0.0 and 1.0, got {value}',
                    'pin': pin_name
                }
            
            # Send G-code command to set PWM value
            gcode = f"SET_PIN PIN={pin_name} VALUE={value:.3f}"
            
            result = await self.klippy_apis.run_gcode(gcode)
            
            if result.get('result', {}).get('queued', False):
                logger.info(f"PWM pin {pin_name} set to {value:.3f}")
                return {
                    'success': True,
                    'pin': pin_name,
                    'value': value,
                    'gcode': gcode
                }
            else:
                raise Exception(f"Failed to queue G-code command: {gcode}")
                
        except Exception as e:
            logger.error(f"Error setting PWM value: {e}")
            return {
                'success': False,
                'error': str(e),
                'pin': pin_name if 'pin_name' in locals() else 'unknown'
            }
    
    async def _handle_ramp_pwm(self, web_request: Any) -> Dict[str, Any]:
        """Handle POST request to ramp PWM value.
        
        Args:
            web_request: Moonraker web request object
            
        Returns:
            Dictionary containing operation result
        """
        try:
            # Extract parameters
            start_value = web_request.get_float('start_value')
            end_value = web_request.get_float('end_value')
            pin_name = web_request.get_str('pin_name', self.default_pin)
            duration = web_request.get_float('duration', self.ramp_duration)
            steps = web_request.get_int('steps', self.ramp_steps)
            
            # Validate pin name
            if not pin_name:
                return {
                    'success': False,
                    'error': 'Pin name is required (provide pin_name parameter or configure default_pin)',
                    'pin': pin_name
                }
            
            # Validate values
            if start_value < 0.0 or start_value > 1.0:
                return {
                    'success': False,
                    'error': f'Start value must be between 0.0 and 1.0, got {start_value}',
                    'pin': pin_name
                }
            
            if end_value < 0.0 or end_value > 1.0:
                return {
                    'success': False,
                    'error': f'End value must be between 0.0 and 1.0, got {end_value}',
                    'pin': pin_name
                }
            
            # Validate duration
            if duration < 0.1 or duration > 300.0:
                return {
                    'success': False,
                    'error': f'Duration must be between 0.1 and 300.0 seconds, got {duration}',
                    'pin': pin_name
                }
            
            # Validate steps
            if steps < 2 or steps > 200:
                return {
                    'success': False,
                    'error': f'Steps must be between 2 and 200, got {steps}',
                    'pin': pin_name
                }
            
            # Check if a ramp is already active for this pin
            if pin_name in self.active_ramps:
                # Cancel existing ramp
                existing_task = self.active_ramps[pin_name]
                existing_task.cancel()
                del self.active_ramps[pin_name]
                logger.info(f"Cancelled existing ramp for pin {pin_name}")
            
            # Start new ramp operation
            task = asyncio.create_task(
                self._execute_ramp(pin_name, start_value, end_value, duration, steps)
            )
            self.active_ramps[pin_name] = task
            
            logger.info(f"Started PWM ramp for pin {pin_name}: {start_value:.3f} -> {end_value:.3f} "
                       f"over {duration}s in {steps} steps")
            
            return {
                'success': True,
                'pin': pin_name,
                'start_value': start_value,
                'end_value': end_value,
                'duration': duration,
                'steps': steps
            }
            
        except Exception as e:
            logger.error(f"Error ramping PWM value: {e}")
            return {
                'success': False,
                'error': str(e),
                'pin': pin_name if 'pin_name' in locals() else 'unknown'
            }
    
    async def _execute_ramp(self, pin_name: str, start_value: float, 
                            end_value: float, duration: float, steps: int) -> None:
        """Execute PWM ramp operation.
        
        Args:
            pin_name: Name of the PWM pin
            start_value: Starting PWM value (0.0-1.0)
            end_value: Ending PWM value (0.0-1.0)
            duration: Total ramp duration in seconds
            steps: Number of steps in the ramp
        """
        try:
            # Calculate step delay
            step_delay = duration / steps
            
            # Calculate value increment per step
            value_increment = (end_value - start_value) / (steps - 1)
            
            # Execute ramp steps
            for i in range(steps):
                # Calculate current value
                current_value = start_value + (value_increment * i)
                
                # Send G-code command
                gcode = f"SET_PIN PIN={pin_name} VALUE={current_value:.3f}"
                result = await self.klippy_apis.run_gcode(gcode)
                
                if not result.get('result', {}).get('queued', False):
                    logger.error(f"Failed to set PWM value during ramp: {gcode}")
                    break
                
                # Wait before next step (don't delay after last step)
                if i < steps - 1:
                    await asyncio.sleep(step_delay)
            
            # Clean up active ramp tracking
            if pin_name in self.active_ramps:
                del self.active_ramps[pin_name]
            
            logger.info(f"PWM ramp completed for pin {pin_name}: final value {end_value:.3f}")
            
        except asyncio.CancelledError:
            logger.info(f"PWM ramp cancelled for pin {pin_name}")
            if pin_name in self.active_ramps:
                del self.active_ramps[pin_name]
        except Exception as e:
            logger.error(f"Error during PWM ramp execution for pin {pin_name}: {e}")
            if pin_name in self.active_ramps:
                del self.active_ramps[pin_name]
    
    async def _handle_get_status(self, web_request: Any) -> Dict[str, Any]:
        """Handle GET request for PWM status.
        
        Args:
            web_request: Moonraker web request object
            
        Returns:
            Dictionary containing PWM status
        """
        try:
            # Extract parameters
            pin_name = web_request.get_str('pin_name', None)
            
            # Query Klipper for PWM status
            result = await self._query_pwm_status(pin_name)
            
            return {
                'success': True,
                **result
            }
        except Exception as e:
            logger.error(f"Error querying PWM status: {e}")
            return {
                'success': False,
                'error': str(e),
                'pins': {}
            }
    
    async def _query_pwm_status(self, pin_name: Optional[str] = None) -> Dict[str, Any]:
        """Query Klipper for PWM status.
        
        Args:
            pin_name: Optional specific pin name to query. If None, queries all PWM pins.
            
        Returns:
            Dictionary containing PWM status
            
        Raises:
            Exception: If query fails
        """
        import time
        
        timestamp = time.time()
        
        # Query Klipper for output_pin objects (these include PWM pins)
        try:
            # Query output_pin objects
            query_result = await self.klippy_apis.query_objects({'output_pin': None})
            
            if 'result' not in query_result:
                raise Exception("Invalid response from Klipper API")
            
            klipper_result = query_result['result']
            
            # Extract PWM pin status from the result
            pins = {}
            
            # output_pin objects in Klipper contain value and is_pwm fields
            if 'output_pin' in klipper_result:
                output_pins = klipper_result['output_pin']
                
                # Filter for specific pin if requested
                if pin_name:
                    if pin_name in output_pins:
                        pin_data = output_pins[pin_name]
                        pins[pin_name] = {
                            'value': pin_data.get('value', 0.0),
                            'is_pwm': pin_data.get('is_pwm', False),
                            'scale': pin_data.get('scale', 1.0),
                            'is_inverted': pin_data.get('is_inverted', False)
                        }
                    else:
                        raise Exception(f"PWM pin '{pin_name}' not found in Klipper configuration")
                else:
                    # Return all available output pins
                    for name, pin_data in output_pins.items():
                        pins[name] = {
                            'value': pin_data.get('value', 0.0),
                            'is_pwm': pin_data.get('is_pwm', False),
                            'scale': pin_data.get('scale', 1.0),
                            'is_inverted': pin_data.get('is_inverted', False)
                        }
            
            # Include active ramp information
            active_ramps_info = {}
            for ramp_pin, task in self.active_ramps.items():
                active_ramps_info[ramp_pin] = {
                    'active': not task.done(),
                    'cancelled': task.cancelled()
                }
            
            return {
                'pins': pins,
                'active_ramps': active_ramps_info,
                'timestamp': timestamp
            }
            
        except Exception as e:
            logger.error(f"Failed to query Klipper for PWM status: {e}")
            raise
    
    def get_status(self, eventtime: float) -> Dict[str, Any]:
        """Get component status for Moonraker status reporting.
        
        Args:
            eventtime: Current event time
            
        Returns:
            Dictionary containing component status
        """
        # Count active ramps
        active_ramp_count = sum(1 for task in self.active_ramps.values() if not task.done())
        
        return {
            'default_value': self.default_value,
            'ramp_duration': self.ramp_duration,
            'ramp_steps': self.ramp_steps,
            'default_pin': self.default_pin,
            'active_ramps': active_ramp_count,
            'component': 'pwm_control'
        }
    
    def close(self) -> None:
        """Cleanup when component is closed."""
        # Cancel all active ramp operations
        for pin_name, task in self.active_ramps.items():
            if not task.done():
                task.cancel()
                logger.info(f"Cancelled ramp for pin {pin_name} during component shutdown")
        
        self.active_ramps.clear()
        logger.info("PWM Control component closed")


def load_component(config: Any) -> PWMControl:
    """Load the PWM Control component.
    
    This function is called by Moonraker to load the component.
    
    Args:
        config: Moonraker configuration object
        
    Returns:
        Instance of PWMControl component
    """
    return PWMControl(config)
