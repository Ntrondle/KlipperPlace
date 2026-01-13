#!/usr/bin/env python3
# Version Route
# Handler for version endpoint (GET)

from aiohttp import web
import logging

from . import create_response

logger = logging.getLogger(__name__)


def setup(app: web.Application) -> None:
    """Setup version route.
    
    Args:
        app: aiohttp application
    """
    app.router.add_get('/api/v1/version', handle_version)


async def handle_version(request: web.Request) -> web.Response:
    """Handle GET version command.
    
    Args:
        request: aiohttp request
        
    Returns:
        aiohttp response
    """
    try:
        # Get server instance
        server = request.app['server']
        
        # Get API version from package
        from .. import __version__
        
        # Return version info
        return create_response({
            'status': 'success',
            'command': 'get_version',
            'data': {
                'api_version': __version__,
                'server_version': __version__,
                'supported_versions': ['v1'],
                'latest_version': 'v1',
                'deprecation_notices': []
            }
        })
    
    except Exception as e:
        logger.error(f"Error handling version command: {e}", exc_info=True)
        return create_error_response(
            'EXECUTION_ERROR',
            str(e),
            status=500
        )
