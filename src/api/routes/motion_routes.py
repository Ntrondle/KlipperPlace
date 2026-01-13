#!/usr/bin/env python3
# Motion Command Routes
# Handlers for motion commands (MOVE, HOME)

from aiohttp import web
import logging
from typing import Optional

from middleware.translator import OpenPNPCommand, OpenPNPCommandType
from . import create_response, create_error_response

logger = logging.getLogger(__name__)


def setup(app: web.Application) -> None:
    """Setup motion command routes.
    
    Args:
        app: aiohttp application
    """
    app.router.add_post('/api/v1/motion/move', handle_move)
    app.router.add_post('/api/v1/motion/home', handle_home)


async def handle_move(request: web.Request) -> web.Response:
    """Handle MOVE command.
    
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
        x = data.get('x')
        y = data.get('y')
        z = data.get('z')
        feedrate = data.get('feedrate')
        relative = data.get('relative', False)
        
        # Validate parameters
        if x is None and y is None and z is None:
            return create_error_response(
                'MISSING_PARAMETER',
                'At least one of x, y, or z must be specified'
            )
        
        # Validate with safety manager
        if server.safety_manager:
            is_valid, errors = await server.safety_manager.validate_move_command(
                x=x, y=y, z=z, feedrate=feedrate
            )
            if not is_valid:
                return create_error_response(
                    'BOUNDS_VIOLATION',
                    'Move command validation failed',
                    details={'errors': errors}
                )
        
        # Create command
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.MOVE,
            parameters={
                'x': x,
                'y': y,
                'z': z,
                'feedrate': feedrate,
                'relative': relative
            }
        )
        
        # Execute command
        response = await server.execute_command(command)
        
        # Return response
        return create_response(response.to_dict())
    
    except Exception as e:
        logger.error(f"Error handling move command: {e}", exc_info=True)
        return create_error_response(
            'EXECUTION_ERROR',
            str(e),
            status=500
        )


async def handle_home(request: web.Request) -> web.Response:
    """Handle HOME command.
    
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
        axes = data.get('axes', 'all')
        
        # Create command
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.HOME,
            parameters={'axes': axes}
        )
        
        # Execute command
        response = await server.execute_command(command)
        
        # Mark axes as homed on success
        if response.status.value == 'success':
            if axes == 'all':
                await server.safety_manager.mark_axis_homed('x')
                await server.safety_manager.mark_axis_homed('y')
                await server.safety_manager.mark_axis_homed('z')
            elif isinstance(axes, list):
                for axis in axes:
                    await server.safety_manager.mark_axis_homed(axis)
        
        # Return response
        return create_response(response.to_dict())
    
    except Exception as e:
        logger.error(f"Error handling home command: {e}", exc_info=True)
        return create_error_response(
            'EXECUTION_ERROR',
            str(e),
            status=500
        )
