#!/usr/bin/env python3
# GPIO Command Routes
# Handlers for GPIO commands (READ, WRITE, READ_ALL)

from aiohttp import web
import logging
import time

from middleware.translator import OpenPNPCommand, OpenPNPCommandType
from middleware.cache import CacheCategory
from . import create_response, create_error_response

logger = logging.getLogger(__name__)


def setup(app: web.Application) -> None:
    """Setup GPIO command routes.
    
    Args:
        app: aiohttp application
    """
    app.router.add_get('/api/v1/gpio/read', handle_gpio_read)
    app.router.add_post('/api/v1/gpio/write', handle_gpio_write)
    app.router.add_get('/api/v1/gpio/read_all', handle_gpio_read_all)


async def handle_gpio_read(request: web.Request) -> web.Response:
    """Handle GPIO_READ command.
    
    Args:
        request: aiohttp request
        
    Returns:
        aiohttp response
    """
    try:
        # Get server instance
        server = request.app['server']
        
        # Get query parameters
        pin = request.query.get('pin')
        
        # Validate required parameters
        if not pin:
            return create_error_response(
                'MISSING_PARAMETER',
                'Pin parameter is required'
            )
        
        # Try to get from cache first
        cache_key = f'gpio:{pin}'
        if server.cache_manager:
            cached_data = await server.cache_manager.get(
                cache_key,
                category=CacheCategory.GPIO
            )
            if cached_data and cached_data.get('success'):
                return create_response({
                    'status': 'success',
                    'command': 'gpio_read',
                    'command_id': str(int(time.time() * 1000)),
                    'data': cached_data,
                    'timestamp': time.time()
                })
        
        # Create command
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.GPIO_READ,
            parameters={'pin': pin}
        )
        
        # Execute command
        response = await server.execute_command(command)
        
        # Return response
        return create_response(response.to_dict())
    
    except Exception as e:
        logger.error(f"Error handling gpio_read command: {e}", exc_info=True)
        return create_error_response(
            'EXECUTION_ERROR',
            str(e),
            status=500
        )


async def handle_gpio_write(request: web.Request) -> web.Response:
    """Handle GPIO_WRITE command.
    
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
        
        # Validate required parameters
        if pin is None:
            return create_error_response(
                'MISSING_PARAMETER',
                'Pin parameter is required'
            )
        
        if value is None:
            return create_error_response(
                'MISSING_PARAMETER',
                'Value parameter is required'
            )
        
        # Validate value
        if value not in [0, 1]:
            return create_error_response(
                'INVALID_PARAMETER',
                'Value must be 0 or 1'
            )
        
        # Create command
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.GPIO_WRITE,
            parameters={'pin': pin, 'value': value}
        )
        
        # Execute command
        response = await server.execute_command(command)
        
        # Invalidate cache after write
        if server.cache_manager:
            await server.cache_manager.invalidate(f'gpio:{pin}')
        
        # Return response
        return create_response(response.to_dict())
    
    except Exception as e:
        logger.error(f"Error handling gpio_write command: {e}", exc_info=True)
        return create_error_response(
            'EXECUTION_ERROR',
            str(e),
            status=500
        )


async def handle_gpio_read_all(request: web.Request) -> web.Response:
    """Handle GPIO_READ_ALL command.
    
    Args:
        request: aiohttp request
        
    Returns:
        aiohttp response
    """
    try:
        # Get server instance
        server = request.app['server']
        
        # Try to get from cache first
        cache_key = 'gpio:all'
        if server.cache_manager:
            cached_data = await server.cache_manager.get(
                cache_key,
                category=CacheCategory.GPIO
            )
            if cached_data and cached_data.get('success'):
                return create_response({
                    'status': 'success',
                    'command': 'gpio_read_all',
                    'command_id': str(int(time.time() * 1000)),
                    'data': cached_data,
                    'timestamp': time.time()
                })
        
        # Create command
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.GPIO_READ,
            parameters={'pin': 'all'}
        )
        
        # Execute command
        response = await server.execute_command(command)
        
        # Return response
        return create_response(response.to_dict())
    
    except Exception as e:
        logger.error(f"Error handling gpio_read_all command: {e}", exc_info=True)
        return create_error_response(
            'EXECUTION_ERROR',
            str(e),
            status=500
        )
