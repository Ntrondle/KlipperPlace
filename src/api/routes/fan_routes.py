#!/usr/bin/env python3
# Fan Command Routes
# Handlers for fan commands (ON, OFF, SET)

from aiohttp import web
import logging

from middleware.translator import OpenPNPCommand, OpenPNPCommandType
from . import create_response, create_error_response

logger = logging.getLogger(__name__)


def setup(app: web.Application) -> None:
    """Setup fan command routes.
    
    Args:
        app: aiohttp application
    """
    app.router.add_post('/api/v1/fan/on', handle_fan_on)
    app.router.add_post('/api/v1/fan/off', handle_fan_off)
    app.router.add_post('/api/v1/fan/set', handle_fan_set)


async def handle_fan_on(request: web.Request) -> web.Response:
    """Handle FAN_ON command.
    
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
        fan = data.get('fan', 'fan')
        speed = data.get('speed', 1.0)
        
        # Validate speed range
        if not isinstance(speed, (int, float)) or speed < 0.0 or speed > 1.0:
            return create_error_response(
                'INVALID_PARAMETER',
                'Speed must be a float between 0.0 and 1.0'
            )
        
        # Validate with safety manager
        if server.safety_manager:
            is_valid, error = await server.safety_manager.validate_fan_command(fan, speed)
            if not is_valid:
                return create_error_response(
                    'BOUNDS_VIOLATION',
                    error,
                    details={'fan': fan, 'speed': speed}
                )
        
        # Create command
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.FAN_ON,
            parameters={'fan': fan, 'speed': speed}
        )
        
        # Execute command
        response = await server.execute_command(command)
        
        # Return response
        return create_response(response.to_dict())
    
    except Exception as e:
        logger.error(f"Error handling fan_on command: {e}", exc_info=True)
        return create_error_response(
            'EXECUTION_ERROR',
            str(e),
            status=500
        )


async def handle_fan_off(request: web.Request) -> web.Response:
    """Handle FAN_OFF command.
    
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
        fan = data.get('fan', 'fan')
        
        # Create command
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.FAN_OFF,
            parameters={'fan': fan}
        )
        
        # Execute command
        response = await server.execute_command(command)
        
        # Return response
        return create_response(response.to_dict())
    
    except Exception as e:
        logger.error(f"Error handling fan_off command: {e}", exc_info=True)
        return create_error_response(
            'EXECUTION_ERROR',
            str(e),
            status=500
        )


async def handle_fan_set(request: web.Request) -> web.Response:
    """Handle FAN_SET command.
    
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
        fan = data.get('fan', 'fan')
        speed = data.get('speed')
        
        # Validate required parameters
        if speed is None:
            return create_error_response(
                'MISSING_PARAMETER',
                'Speed parameter is required'
            )
        
        # Validate speed range
        if not isinstance(speed, (int, float)) or speed < 0.0 or speed > 1.0:
            return create_error_response(
                'INVALID_PARAMETER',
                'Speed must be a float between 0.0 and 1.0'
            )
        
        # Validate with safety manager
        if server.safety_manager:
            is_valid, error = await server.safety_manager.validate_fan_command(fan, speed)
            if not is_valid:
                return create_error_response(
                    'BOUNDS_VIOLATION',
                    error,
                    details={'fan': fan, 'speed': speed}
                )
        
        # Create command
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.FAN_SET,
            parameters={'fan': fan, 'speed': speed}
        )
        
        # Execute command
        response = await server.execute_command(command)
        
        # Return response
        return create_response(response.to_dict())
    
    except Exception as e:
        logger.error(f"Error handling fan_set command: {e}", exc_info=True)
        return create_error_response(
            'EXECUTION_ERROR',
            str(e),
            status=500
        )
