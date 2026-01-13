#!/usr/bin/env python3
# Sensor Command Routes
# Handlers for sensor commands (READ, READ_ALL, READ_BY_TYPE)

from aiohttp import web
import logging
import time

from middleware.translator import OpenPNPCommand, OpenPNPCommandType
from middleware.cache import CacheCategory
from . import create_response, create_error_response

logger = logging.getLogger(__name__)


def setup(app: web.Application) -> None:
    """Setup sensor command routes.
    
    Args:
        app: aiohttp application
    """
    app.router.add_get('/api/v1/sensor/read', handle_sensor_read)
    app.router.add_get('/api/v1/sensor/read_all', handle_sensor_read_all)
    app.router.add_get('/api/v1/sensor/read_by_type', handle_sensor_read_by_type)


async def handle_sensor_read(request: web.Request) -> web.Response:
    """Handle SENSOR_READ command.
    
    Args:
        request: aiohttp request
        
    Returns:
        aiohttp response
    """
    try:
        # Get server instance
        server = request.app['server']
        
        # Get query parameters
        sensor = request.query.get('sensor')
        
        # Validate required parameters
        if not sensor:
            return create_error_response(
                'MISSING_PARAMETER',
                'Sensor parameter is required'
            )
        
        # Try to get from cache first
        cache_key = f'sensor:{sensor}'
        if server.cache_manager:
            cached_data = await server.cache_manager.get(
                cache_key,
                category=CacheCategory.SENSOR
            )
            if cached_data and cached_data.get('success'):
                return create_response({
                    'status': 'success',
                    'command': 'sensor_read',
                    'command_id': str(int(time.time() * 1000)),
                    'data': cached_data,
                    'timestamp': time.time()
                })
        
        # Create command
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.SENSOR_READ,
            parameters={'sensor': sensor}
        )
        
        # Execute command
        response = await server.execute_command(command)
        
        # Return response
        return create_response(response.to_dict())
    
    except Exception as e:
        logger.error(f"Error handling sensor_read command: {e}", exc_info=True)
        return create_error_response(
            'EXECUTION_ERROR',
            str(e),
            status=500
        )


async def handle_sensor_read_all(request: web.Request) -> web.Response:
    """Handle SENSOR_READ_ALL command.
    
    Args:
        request: aiohttp request
        
    Returns:
        aiohttp response
    """
    try:
        # Get server instance
        server = request.app['server']
        
        # Try to get from cache first
        cache_key = 'sensor:all'
        if server.cache_manager:
            cached_data = await server.cache_manager.get(
                cache_key,
                category=CacheCategory.SENSOR
            )
            if cached_data and cached_data.get('success'):
                return create_response({
                    'status': 'success',
                    'command': 'sensor_read_all',
                    'command_id': str(int(time.time() * 1000)),
                    'data': cached_data,
                    'timestamp': time.time()
                })
        
        # Create command
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.SENSOR_READ_ALL,
            parameters={}
        )
        
        # Execute command
        response = await server.execute_command(command)
        
        # Return response
        return create_response(response.to_dict())
    
    except Exception as e:
        logger.error(f"Error handling sensor_read_all command: {e}", exc_info=True)
        return create_error_response(
            'EXECUTION_ERROR',
            str(e),
            status=500
        )


async def handle_sensor_read_by_type(request: web.Request) -> web.Response:
    """Handle SENSOR_READ_BY_TYPE command.
    
    Args:
        request: aiohttp request
        
    Returns:
        aiohttp response
    """
    try:
        # Get server instance
        server = request.app['server']
        
        # Get query parameters
        sensor_type = request.query.get('type')
        
        # Validate required parameters
        if not sensor_type:
            return create_error_response(
                'MISSING_PARAMETER',
                'Type parameter is required'
            )
        
        # Try to get from cache first
        cache_key = f'sensor:type:{sensor_type}'
        if server.cache_manager:
            cached_data = await server.cache_manager.get(
                cache_key,
                category=CacheCategory.SENSOR
            )
            if cached_data and cached_data.get('success'):
                return create_response({
                    'status': 'success',
                    'command': 'sensor_read_by_type',
                    'command_id': str(int(time.time() * 1000)),
                    'data': cached_data,
                    'timestamp': time.time()
                })
        
        # Create command
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.SENSOR_READ,
            parameters={'type': sensor_type}
        )
        
        # Execute command
        response = await server.execute_command(command)
        
        # Return response
        return create_response(response.to_dict())
    
    except Exception as e:
        logger.error(f"Error handling sensor_read_by_type command: {e}", exc_info=True)
        return create_error_response(
            'EXECUTION_ERROR',
            str(e),
            status=500
        )
