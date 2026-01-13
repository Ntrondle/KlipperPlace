#!/usr/bin/env python3
# Feeder Command Routes
# Handlers for feeder commands (ADVANCE, RETRACT)

from aiohttp import web
import logging

from middleware.translator import OpenPNPCommand, OpenPNPCommandType
from . import create_response, create_error_response

logger = logging.getLogger(__name__)


def setup(app: web.Application) -> None:
    """Setup feeder command routes.
    
    Args:
        app: aiohttp application
    """
    app.router.add_post('/api/v1/feeder/advance', handle_feeder_advance)
    app.router.add_post('/api/v1/feeder/retract', handle_feeder_retract)


async def handle_feeder_advance(request: web.Request) -> web.Response:
    """Handle FEEDER_ADVANCE command.
    
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
        feeder = data.get('feeder', 'feeder')
        distance = data.get('distance')
        feedrate = data.get('feedrate', 100.0)
        
        # Validate required parameters
        if distance is None:
            return create_error_response(
                'MISSING_PARAMETER',
                'Distance parameter is required'
            )
        
        # Validate distance
        if not isinstance(distance, (int, float)) or distance <= 0:
            return create_error_response(
                'INVALID_PARAMETER',
                'Distance must be a positive number'
            )
        
        # Validate feedrate
        if not isinstance(feedrate, (int, float)) or feedrate <= 0:
            return create_error_response(
                'INVALID_PARAMETER',
                'Feedrate must be a positive number'
            )
        
        # Create command
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.FEEDER_ADVANCE,
            parameters={
                'feeder': feeder,
                'distance': distance,
                'feedrate': feedrate
            }
        )
        
        # Execute command
        response = await server.execute_command(command)
        
        # Return response
        return create_response(response.to_dict())
    
    except Exception as e:
        logger.error(f"Error handling feeder_advance command: {e}", exc_info=True)
        return create_error_response(
            'EXECUTION_ERROR',
            str(e),
            status=500
        )


async def handle_feeder_retract(request: web.Request) -> web.Response:
    """Handle FEEDER_RETRACT command.
    
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
        feeder = data.get('feeder', 'feeder')
        distance = data.get('distance')
        feedrate = data.get('feedrate', 100.0)
        
        # Validate required parameters
        if distance is None:
            return create_error_response(
                'MISSING_PARAMETER',
                'Distance parameter is required'
            )
        
        # Validate distance
        if not isinstance(distance, (int, float)) or distance <= 0:
            return create_error_response(
                'INVALID_PARAMETER',
                'Distance must be a positive number'
            )
        
        # Validate feedrate
        if not isinstance(feedrate, (int, float)) or feedrate <= 0:
            return create_error_response(
                'INVALID_PARAMETER',
                'Feedrate must be a positive number'
            )
        
        # Create command
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.FEEDER_RETRACT,
            parameters={
                'feeder': feeder,
                'distance': distance,
                'feedrate': feedrate
            }
        )
        
        # Execute command
        response = await server.execute_command(command)
        
        # Return response
        return create_response(response.to_dict())
    
    except Exception as e:
        logger.error(f"Error handling feeder_retract command: {e}", exc_info=True)
        return create_error_response(
            'EXECUTION_ERROR',
            str(e),
            status=500
        )
