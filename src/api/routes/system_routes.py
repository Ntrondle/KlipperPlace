#!/usr/bin/env python3
# System Command Routes
# Handlers for system commands (EMERGENCY_STOP, PAUSE, RESUME, RESET)

from aiohttp import web
import logging
import time

from middleware.translator import OpenPNPCommand, OpenPNPCommandType
from . import create_response, create_error_response

logger = logging.getLogger(__name__)


def setup(app: web.Application) -> None:
    """Setup system command routes.
    
    Args:
        app: aiohttp application
    """
    app.router.add_post('/api/v1/system/emergency_stop', handle_emergency_stop)
    app.router.add_post('/api/v1/system/pause', handle_pause)
    app.router.add_post('/api/v1/system/resume', handle_resume)
    app.router.add_post('/api/v1/system/reset', handle_reset)


async def handle_emergency_stop(request: web.Request) -> web.Response:
    """Handle EMERGENCY_STOP command.
    
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
        reason = data.get('reason', 'Manual emergency stop')
        
        # Execute emergency stop
        if server.safety_manager:
            event = await server.safety_manager.emergency_stop(reason)
            
            # Return response
            return create_response({
                'status': 'success',
                'command': 'emergency_stop',
                'command_id': str(int(time.time() * 1000)),
                'data': {
                    'emergency_stop_active': True,
                    'reason': reason,
                    'gcode_sent': 'M112'
                },
                'timestamp': time.time()
            })
        
        # Fallback if no safety manager
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.CANCEL,
            parameters={'reason': reason}
        )
        
        response = await server.execute_command(command)
        return create_response(response.to_dict())
    
    except Exception as e:
        logger.error(f"Error handling emergency_stop command: {e}", exc_info=True)
        return create_error_response(
            'EXECUTION_ERROR',
            str(e),
            status=500
        )


async def handle_pause(request: web.Request) -> web.Response:
    """Handle PAUSE command.
    
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
            command_type=OpenPNPCommandType.PAUSE,
            parameters={}
        )
        
        # Execute command
        response = await server.execute_command(command)
        
        # Return response
        return create_response(response.to_dict())
    
    except Exception as e:
        logger.error(f"Error handling pause command: {e}", exc_info=True)
        return create_error_response(
            'EXECUTION_ERROR',
            str(e),
            status=500
        )


async def handle_resume(request: web.Request) -> web.Response:
    """Handle RESUME command.
    
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
            command_type=OpenPNPCommandType.RESUME,
            parameters={}
        )
        
        # Execute command
        response = await server.execute_command(command)
        
        # Return response
        return create_response(response.to_dict())
    
    except Exception as e:
        logger.error(f"Error handling resume command: {e}", exc_info=True)
        return create_error_response(
            'EXECUTION_ERROR',
            str(e),
            status=500
        )


async def handle_reset(request: web.Request) -> web.Response:
    """Handle RESET command.
    
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
            command_type=OpenPNPCommandType.RESET,
            parameters={}
        )
        
        # Execute command
        response = await server.execute_command(command)
        
        # Clear emergency stop state
        if server.safety_manager:
            server.safety_manager.clear_emergency_stop()
        
        # Return response
        return create_response(response.to_dict())
    
    except Exception as e:
        logger.error(f"Error handling reset command: {e}", exc_info=True)
        return create_error_response(
            'EXECUTION_ERROR',
            str(e),
            status=500
        )
