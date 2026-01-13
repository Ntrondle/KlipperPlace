#!/usr/bin/env python3
# Actuator Command Routes
# Handlers for actuator commands (ACTUATE, ON, OFF)

from aiohttp import web
import logging

from middleware.translator import OpenPNPCommand, OpenPNPCommandType
from . import create_response, create_error_response

logger = logging.getLogger(__name__)


def setup(app: web.Application) -> None:
    """Setup actuator command routes.
    
    Args:
        app: aiohttp application
    """
    app.router.add_post('/api/v1/actuators/actuate', handle_actuate)
    app.router.add_post('/api/v1/actuators/on', handle_actuator_on)
    app.router.add_post('/api/v1/actuators/off', handle_actuator_off)


async def handle_actuate(request: web.Request) -> web.Response:
    """Handle ACTUATE command.
    
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
        value = data.get('value', 1)
        
        # Validate required parameters
        if not pin:
            return create_error_response(
                'MISSING_PARAMETER',
                'Pin name is required'
            )
        
        # Create command
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.ACTUATE,
            parameters={'pin': pin, 'value': value}
        )
        
        # Execute command
        response = await server.execute_command(command)
        
        # Return response
        return create_response(response.to_dict())
    
    except Exception as e:
        logger.error(f"Error handling actuate command: {e}", exc_info=True)
        return create_error_response(
            'EXECUTION_ERROR',
            str(e),
            status=500
        )


async def handle_actuator_on(request: web.Request) -> web.Response:
    """Handle ACTUATOR_ON command.
    
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
        
        # Validate required parameters
        if not pin:
            return create_error_response(
                'MISSING_PARAMETER',
                'Pin name is required'
            )
        
        # Create command
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.ACTUATE_ON,
            parameters={'pin': pin}
        )
        
        # Execute command
        response = await server.execute_command(command)
        
        # Return response
        return create_response(response.to_dict())
    
    except Exception as e:
        logger.error(f"Error handling actuator_on command: {e}", exc_info=True)
        return create_error_response(
            'EXECUTION_ERROR',
            str(e),
            status=500
        )


async def handle_actuator_off(request: web.Request) -> web.Response:
    """Handle ACTUATOR_OFF command.
    
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
        
        # Validate required parameters
        if not pin:
            return create_error_response(
                'MISSING_PARAMETER',
                'Pin name is required'
            )
        
        # Create command
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.ACTUATE_OFF,
            parameters={'pin': pin}
        )
        
        # Execute command
        response = await server.execute_command(command)
        
        # Return response
        return create_response(response.to_dict())
    
    except Exception as e:
        logger.error(f"Error handling actuator_off command: {e}", exc_info=True)
        return create_error_response(
            'EXECUTION_ERROR',
            str(e),
            status=500
        )
