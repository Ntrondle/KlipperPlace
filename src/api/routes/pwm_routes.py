#!/usr/bin/env python3
# PWM Command Routes
# Handlers for PWM commands (SET, RAMP)

from aiohttp import web
import logging

from middleware.translator import OpenPNPCommand, OpenPNPCommandType
from . import create_response, create_error_response

logger = logging.getLogger(__name__)


def setup(app: web.Application) -> None:
    """Setup PWM command routes.
    
    Args:
        app: aiohttp application
    """
    app.router.add_post('/api/v1/pwm/set', handle_pwm_set)
    app.router.add_post('/api/v1/pwm/ramp', handle_pwm_ramp)


async def handle_pwm_set(request: web.Request) -> web.Response:
    """Handle PWM_SET command.
    
    Args:
        request: aiohttp request
        
    Returns:
        aiohttp response
    """
    try:
        # Get server instance
        server = request.app['server']
        
        # Parse request body
        data = await request.json()
        
        # Extract parameters
        pin = data.get('pin')
        value = data.get('value')
        cycle_time = data.get('cycle_time', 0.01)
        
        # Validate required parameters
        if pin is None:
            return create_error_response(
                'MISSING_PARAMETER',
                'Pin name is required'
            )
        
        if value is None:
            return create_error_response(
                'MISSING_PARAMETER',
                'Value parameter is required'
            )
        
        # Validate value range
        if not isinstance(value, (int, float)) or value < 0.0 or value > 1.0:
            return create_error_response(
                'INVALID_PARAMETER',
                'Value must be a float between 0.0 and 1.0'
            )
        
        # Validate with safety manager
        if server.safety_manager:
            event = await server.safety_manager.check_pwm_limits(pin, value)
            if event:
                return create_error_response(
                    'PWM_LIMIT_EXCEEDED',
                    event.message,
                    details=event.details,
                    status=400
                )
        
        # Create command
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.PWM_SET,
            parameters={
                'pin': pin,
                'value': value,
                'cycle_time': cycle_time
            }
        )
        
        # Execute command
        response = await server.execute_command(command)
        
        # Return response
        return create_response(response.to_dict())
    
    except Exception as e:
        logger.error(f"Error handling pwm_set command: {e}", exc_info=True)
        return create_error_response(
            'EXECUTION_ERROR',
            str(e),
            status=500
        )


async def handle_pwm_ramp(request: web.Request) -> web.Response:
    """Handle PWM_RAMP command.
    
    Args:
        request: aiohttp request
        
    Returns:
        aiohttp response
    """
    try:
        # Get server instance
        server = request.app['server']
        
        # Parse request body
        data = await request.json()
        
        # Extract parameters
        pin = data.get('pin')
        start_value = data.get('start_value')
        end_value = data.get('end_value')
        duration = data.get('duration')
        steps = data.get('steps', 10)
        
        # Validate required parameters
        if pin is None:
            return create_error_response(
                'MISSING_PARAMETER',
                'Pin name is required'
            )
        
        if start_value is None:
            return create_error_response(
                'MISSING_PARAMETER',
                'Start value parameter is required'
            )
        
        if end_value is None:
            return create_error_response(
                'MISSING_PARAMETER',
                'End value parameter is required'
            )
        
        if duration is None:
            return create_error_response(
                'MISSING_PARAMETER',
                'Duration parameter is required'
            )
        
        # Validate value ranges
        if not isinstance(start_value, (int, float)) or start_value < 0.0 or start_value > 1.0:
            return create_error_response(
                'INVALID_PARAMETER',
                'Start value must be a float between 0.0 and 1.0'
            )
        
        if not isinstance(end_value, (int, float)) or end_value < 0.0 or end_value > 1.0:
            return create_error_response(
                'INVALID_PARAMETER',
                'End value must be a float between 0.0 and 1.0'
            )
        
        if not isinstance(duration, (int, float)) or duration <= 0:
            return create_error_response(
                'INVALID_PARAMETER',
                'Duration must be a positive number'
            )
        
        # Validate with safety manager
        if server.safety_manager:
            event = await server.safety_manager.check_pwm_limits(pin, max(start_value, end_value))
            if event:
                return create_error_response(
                    'PWM_LIMIT_EXCEEDED',
                    event.message,
                    details=event.details,
                    status=400
                )
        
        # Create command
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.PWM_RAMP,
            parameters={
                'pin': pin,
                'start_value': start_value,
                'end_value': end_value,
                'duration': duration,
                'steps': steps
            }
        )
        
        # Execute command
        response = await server.execute_command(command)
        
        # Return response
        return create_response(response.to_dict())
    
    except Exception as e:
        logger.error(f"Error handling pwm_ramp command: {e}", exc_info=True)
        return create_error_response(
            'EXECUTION_ERROR',
            str(e),
            status=500
        )
