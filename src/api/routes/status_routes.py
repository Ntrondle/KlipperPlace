#!/usr/bin/env python3
# Status Command Routes
# Handlers for status commands (STATUS, POSITION, PRINTER_STATE)

from aiohttp import web
import logging
import time

from middleware.translator import OpenPNPCommand, OpenPNPCommandType
from middleware.cache import CacheCategory
from . import create_response, create_error_response

logger = logging.getLogger(__name__)


def setup(app: web.Application) -> None:
    """Setup status command routes.
    
    Args:
        app: aiohttp application
    """
    app.router.add_get('/api/v1/status', handle_status)
    app.router.add_get('/api/v1/position', handle_position)
    app.router.add_get('/api/v1/printer/state', handle_printer_state)


async def handle_status(request: web.Request) -> web.Response:
    """Handle GET_STATUS command.
    
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
            command_type=OpenPNPCommandType.GET_STATUS,
            parameters={}
        )
        
        # Execute command
        response = await server.execute_command(command)
        
        # Add queue info if available
        if response.data and server.translator:
            queue_info = await server.translator.get_queue_info()
            response.data['queue'] = queue_info
        
        # Return response
        return create_response(response.to_dict())
    
    except Exception as e:
        logger.error(f"Error handling get_status command: {e}", exc_info=True)
        return create_error_response(
            'EXECUTION_ERROR',
            str(e),
            status=500
        )


async def handle_position(request: web.Request) -> web.Response:
    """Handle GET_POSITION command.
    
    Args:
        request: aiohttp request
        
    Returns:
        aiohttp response
    """
    try:
        # Get server instance
        server = request.app['server']
        
        # Try to get from cache first
        cache_key = 'position'
        if server.cache_manager:
            cached_data = await server.cache_manager.get(
                cache_key,
                category=CacheCategory.POSITION
            )
            if cached_data and cached_data.get('success'):
                position_data = cached_data.get('position', {})
                return create_response({
                    'status': 'success',
                    'command': 'get_position',
                    'command_id': str(int(time.time() * 1000)),
                    'data': {
                        'position': position_data,
                        'positioning_mode': 'absolute',
                        'units': 'mm'
                    },
                    'timestamp': time.time()
                })
        
        # Create command
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.GET_POSITION,
            parameters={}
        )
        
        # Execute command
        response = await server.execute_command(command)
        
        # Return response
        return create_response(response.to_dict())
    
    except Exception as e:
        logger.error(f"Error handling get_position command: {e}", exc_info=True)
        return create_error_response(
            'EXECUTION_ERROR',
            str(e),
            status=500
        )


async def handle_printer_state(request: web.Request) -> web.Response:
    """Handle GET_PRINTER_STATE command.
    
    Args:
        request: aiohttp request
        
    Returns:
        aiohttp response
    """
    try:
        # Get server instance
        server = request.app['server']
        
        # Try to get from cache first
        cache_key = 'printer_state'
        if server.cache_manager:
            cached_data = await server.cache_manager.get(
                cache_key,
                category=CacheCategory.PRINTER_STATE
            )
            if cached_data and cached_data.get('success'):
                return create_response({
                    'status': 'success',
                    'command': 'get_printer_state',
                    'command_id': str(int(time.time() * 1000)),
                    'data': cached_data,
                    'timestamp': time.time()
                })
        
        # Create command
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.GET_PRINTER_STATE,
            parameters={}
        )
        
        # Execute command
        response = await server.execute_command(command)
        
        # Return response
        return create_response(response.to_dict())
    
    except Exception as e:
        logger.error(f"Error handling get_printer_state command: {e}", exc_info=True)
        return create_error_response(
            'EXECUTION_ERROR',
            str(e),
            status=500
        )
