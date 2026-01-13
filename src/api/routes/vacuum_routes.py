#!/usr/bin/env python3
# Vacuum Command Routes
# Handlers for vacuum commands (ON, OFF, SET)

from aiohttp import web
import logging

from middleware.translator import OpenPNPCommand, OpenPNPCommandType
from . import create_response, create_error_response

logger = logging.getLogger(__name__)


def setup(app: web.Application) -> None:
    """Setup vacuum command routes.
    
    Args:
        app: aiohttp application
    """
    app.router.add_post('/api/v1/vacuum/on', handle_vacuum_on)
    app.router.add_post('/api/v1/vacuum/off', handle_vacuum_off)
    app.router.add_post('/api/v1/vacuum/set', handle_vacuum_set)


async def handle_vacuum_on(request: web.Request) -> web.Response:
    """Handle VACUUM_ON command.
    
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
        power = data.get('power', 255)
        
        # Validate power range
        if not isinstance(power, int) or power < 0 or power > 255:
            return create_error_response(
                'INVALID_PARAMETER',
                'Power must be an integer between 0 and 255'
            )
        
        # Create command
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.VACUUM_ON,
            parameters={'power': power}
        )
        
        # Execute command
        response = await server.execute_command(command)
        
        # Return response
        return create_response(response.to_dict())
    
    except Exception as e:
        logger.error(f"Error handling vacuum_on command: {e}", exc_info=True)
        return create_error_response(
            'EXECUTION_ERROR',
            str(e),
            status=500
        )


async def handle_vacuum_off(request: web.Request) -> web.Response:
    """Handle VACUUM_OFF command.
    
    Args:
        request: aiohttp request
        
    Returns:
        aiohttp response
    """
    try:
        # Get server instance
        server = request.app['server']
        
        # Create command
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.VACUUM_OFF,
            parameters={}
        )
        
        # Execute command
        response = await server.execute_command(command)
        
        # Return response
        return create_response(response.to_dict())
    
    except Exception as e:
        logger.error(f"Error handling vacuum_off command: {e}", exc_info=True)
        return create_error_response(
            'EXECUTION_ERROR',
            str(e),
            status=500
        )


async def handle_vacuum_set(request: web.Request) -> web.Response:
    """Handle VACUUM_SET command.
    
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
        power = data.get('power')
        
        # Validate required parameters
        if power is None:
            return create_error_response(
                'MISSING_PARAMETER',
                'Power parameter is required'
            )
        
        # Validate power range
        if not isinstance(power, int) or power < 0 or power > 255:
            return create_error_response(
                'INVALID_PARAMETER',
                'Power must be an integer between 0 and 255'
            )
        
        # Create command
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.VACUUM_SET,
            parameters={'power': power}
        )
        
        # Execute command
        response = await server.execute_command(command)
        
        # Return response
        return create_response(response.to_dict())
    
    except Exception as e:
        logger.error(f"Error handling vacuum_set command: {e}", exc_info=True)
        return create_error_response(
            'EXECUTION_ERROR',
            str(e),
            status=500
        )
