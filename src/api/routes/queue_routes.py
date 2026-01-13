#!/usr/bin/env python3
# Queue Command Routes
# Handlers for queue commands (ADD, BATCH, STATUS, CLEAR, CANCEL)

from aiohttp import web
import logging
import uuid
import time

from middleware.translator import OpenPNPCommand, OpenPNPCommandType
from . import create_response, create_error_response

logger = logging.getLogger(__name__)


def setup(app: web.Application) -> None:
    """Setup queue command routes.
    
    Args:
        app: aiohttp application
    """
    app.router.add_post('/api/v1/queue/add', handle_queue_add)
    app.router.add_post('/api/v1/queue/batch', handle_queue_batch)
    app.router.add_get('/api/v1/queue/status', handle_queue_status)
    app.router.add_delete('/api/v1/queue/clear', handle_queue_clear)
    app.router.add_delete('/api/v1/queue/cancel', handle_queue_cancel)


async def handle_queue_add(request: web.Request) -> web.Response:
    """Handle QUEUE_ADD command.
    
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
        command = data.get('command')
        parameters = data.get('parameters', {})
        priority = data.get('priority', 0)
        
        # Validate required parameters
        if not command:
            return create_error_response(
                'MISSING_PARAMETER',
                'Command parameter is required'
            )
        
        # Create command
        openpnp_command = OpenPNPCommand(
            command_type=OpenPNPCommandType.QUEUE_COMMAND,
            parameters={
                'command': command,
                'parameters': parameters,
                'priority': priority
            },
            priority=priority
        )
        
        # Enqueue command
        queue_id = await server.translator.enqueue_command(openpnp_command, priority)
        
        # Get queue status
        queue_info = await server.translator.get_queue_info()
        
        # Return response
        return create_response({
            'status': 'success',
            'command': 'queue_add',
            'command_id': str(int(time.time() * 1000)),
            'data': {
                'queue_id': queue_id,
                'queue_position': queue_info.get('queue_size', 0),
                'queue_size': queue_info.get('queue_size', 0)
            },
            'timestamp': time.time()
        })
    
    except Exception as e:
        logger.error(f"Error handling queue_add command: {e}", exc_info=True)
        return create_error_response(
            'EXECUTION_ERROR',
            str(e),
            status=500
        )


async def handle_queue_batch(request: web.Request) -> web.Response:
    """Handle QUEUE_BATCH command.
    
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
        commands = data.get('commands', [])
        stop_on_error = data.get('stop_on_error', True)
        
        # Validate required parameters
        if not commands or not isinstance(commands, list):
            return create_error_response(
                'MISSING_PARAMETER',
                'Commands parameter is required and must be an array'
            )
        
        # Enqueue all commands
        queue_ids = []
        for cmd_data in commands:
            command = cmd_data.get('command')
            parameters = cmd_data.get('parameters', {})
            priority = cmd_data.get('priority', 0)
            
            if command:
                openpnp_command = OpenPNPCommand(
                    command_type=OpenPNPCommandType.QUEUE_COMMAND,
                    parameters={
                        'command': command,
                        'parameters': parameters
                    },
                    priority=priority
                )
                queue_id = await server.translator.enqueue_command(openpnp_command, priority)
                queue_ids.append(queue_id)
        
        # Get queue status
        queue_info = await server.translator.get_queue_info()
        
        # Return response
        return create_response({
            'status': 'success',
            'command': 'queue_batch',
            'command_id': str(int(time.time() * 1000)),
            'data': {
                'queue_ids': queue_ids,
                'queue_size': queue_info.get('queue_size', 0)
            },
            'timestamp': time.time()
        })
    
    except Exception as e:
        logger.error(f"Error handling queue_batch command: {e}", exc_info=True)
        return create_error_response(
            'EXECUTION_ERROR',
            str(e),
            status=500
        )


async def handle_queue_status(request: web.Request) -> web.Response:
    """Handle QUEUE_STATUS command.
    
    Args:
        request: aiohttp request
        
    Returns:
        aiohttp response
    """
    try:
        # Get server instance
        server = request.app['server']
        
        # Get queue status
        queue_info = await server.translator.get_queue_info()
        
        # Return response
        return create_response({
            'status': 'success',
            'command': 'queue_status',
            'command_id': str(int(time.time() * 1000)),
            'data': queue_info,
            'timestamp': time.time()
        })
    
    except Exception as e:
        logger.error(f"Error handling queue_status command: {e}", exc_info=True)
        return create_error_response(
            'EXECUTION_ERROR',
            str(e),
            status=500
        )


async def handle_queue_clear(request: web.Request) -> web.Response:
    """Handle QUEUE_CLEAR command.
    
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
            command_type=OpenPNPCommandType.QUEUE_CLEAR,
            parameters={}
        )
        
        # Execute command
        response = await server.execute_command(command)
        
        # Return response
        return create_response(response.to_dict())
    
    except Exception as e:
        logger.error(f"Error handling queue_clear command: {e}", exc_info=True)
        return create_error_response(
            'EXECUTION_ERROR',
            str(e),
            status=500
        )


async def handle_queue_cancel(request: web.Request) -> web.Response:
    """Handle QUEUE_CANCEL command.
    
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
        queue_id = data.get('queue_id')
        
        # Validate required parameters
        if not queue_id:
            return create_error_response(
                'MISSING_PARAMETER',
                'Queue ID parameter is required'
            )
        
        # Create cancel command
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.CANCEL,
            parameters={'queue_id': queue_id}
        )
        
        # Execute command
        response = await server.execute_command(command)
        
        # Return response
        return create_response(response.to_dict())
    
    except Exception as e:
        logger.error(f"Error handling queue_cancel command: {e}", exc_info=True)
        return create_error_response(
            'EXECUTION_ERROR',
            str(e),
            status=500
        )
