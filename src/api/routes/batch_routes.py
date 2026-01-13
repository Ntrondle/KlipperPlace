#!/usr/bin/env python3
# Batch Operation Routes
# Handlers for batch operations (EXECUTE)

from aiohttp import web
import logging
import time

from . import create_response, create_error_response

logger = logging.getLogger(__name__)


def setup(app: web.Application) -> None:
    """Setup batch operation routes.
    
    Args:
        app: aiohttp application
    """
    app.router.add_post('/api/v1/batch/execute', handle_batch_execute)


async def handle_batch_execute(request: web.Request) -> web.Response:
    """Handle BATCH_EXECUTE command.
    
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
        parallel = data.get('parallel', False)
        
        # Validate required parameters
        if not commands or not isinstance(commands, list):
            return create_error_response(
                'MISSING_PARAMETER',
                'Commands parameter is required and must be an array'
            )
        
        # Execute batch
        results = await server.execute_batch(commands, stop_on_error)
        
        # Calculate statistics
        success_count = sum(1 for r in results if r.get('status') == 'success')
        error_count = sum(1 for r in results if r.get('status') == 'error')
        total_execution_time = sum(r.get('execution_time', 0) for r in results)
        
        # Determine overall status
        if error_count == 0:
            overall_status = 'success'
        elif success_count > 0:
            overall_status = 'partial'
        else:
            overall_status = 'error'
        
        # Return response
        return create_response({
            'status': overall_status,
            'command': 'batch_execute',
            'command_id': str(int(time.time() * 1000)),
            'data': {
                'results': results,
                'total_execution_time': total_execution_time,
                'success_count': success_count,
                'error_count': error_count
            },
            'timestamp': time.time()
        })
    
    except Exception as e:
        logger.error(f"Error handling batch_execute command: {e}", exc_info=True)
        return create_error_response(
            'EXECUTION_ERROR',
            str(e),
            status=500
        )
