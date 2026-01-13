#!/usr/bin/env python3
# Pick and Place Command Routes
# Handlers for pick and place commands (PICK, PLACE, PICK_AND_PLACE)

from aiohttp import web
import logging

from middleware.translator import OpenPNPCommand, OpenPNPCommandType
from . import create_response, create_error_response

logger = logging.getLogger(__name__)


def setup(app: web.Application) -> None:
    """Setup pick and place command routes.
    
    Args:
        app: aiohttp application
    """
    app.router.add_post('/api/v1/pnp/pick', handle_pick)
    app.router.add_post('/api/v1/pnp/place', handle_place)
    app.router.add_post('/api/v1/pnp/pick_and_place', handle_pick_and_place)


async def handle_pick(request: web.Request) -> web.Response:
    """Handle PICK command.
    
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
        z = data.get('z', 0.0)
        feedrate = data.get('feedrate')
        vacuum_power = data.get('vacuum_power', 255)
        travel_height = data.get('travel_height', 5.0)
        
        # Create command
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.PICK,
            parameters={
                'z': z,
                'feedrate': feedrate,
                'vacuum_power': vacuum_power,
                'travel_height': travel_height
            }
        )
        
        # Execute command
        response = await server.execute_command(command)
        
        # Return response
        return create_response(response.to_dict())
    
    except Exception as e:
        logger.error(f"Error handling pick command: {e}", exc_info=True)
        return create_error_response(
            'EXECUTION_ERROR',
            str(e),
            status=500
        )


async def handle_place(request: web.Request) -> web.Response:
    """Handle PLACE command.
    
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
        z = data.get('z', 0.0)
        feedrate = data.get('feedrate')
        travel_height = data.get('travel_height', 5.0)
        
        # Create command
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.PLACE,
            parameters={
                'z': z,
                'feedrate': feedrate,
                'travel_height': travel_height
            }
        )
        
        # Execute command
        response = await server.execute_command(command)
        
        # Return response
        return create_response(response.to_dict())
    
    except Exception as e:
        logger.error(f"Error handling place command: {e}", exc_info=True)
        return create_error_response(
            'EXECUTION_ERROR',
            str(e),
            status=500
        )


async def handle_pick_and_place(request: web.Request) -> web.Response:
    """Handle PICK_AND_PLACE command.
    
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
        place_x = data.get('place_x')
        place_y = data.get('place_y')
        pick_height = data.get('pick_height', 0.0)
        place_height = data.get('place_height', 0.0)
        safe_height = data.get('safe_height', 10.0)
        feedrate = data.get('feedrate')
        vacuum_power = data.get('vacuum_power', 255)
        
        # Validate required parameters
        if x is None or y is None or place_x is None or place_y is None:
            return create_error_response(
                'MISSING_PARAMETER',
                'Required parameters: x, y, place_x, place_y'
            )
        
        # Validate move parameters with safety manager
        if server.safety_manager:
            is_valid, errors = await server.safety_manager.validate_move_command(
                x=x, y=y, feedrate=feedrate
            )
            if not is_valid:
                return create_error_response(
                    'BOUNDS_VIOLATION',
                    'Pick position validation failed',
                    details={'errors': errors}
                )
            
            is_valid, errors = await server.safety_manager.validate_move_command(
                x=place_x, y=place_y, feedrate=feedrate
            )
            if not is_valid:
                return create_error_response(
                    'BOUNDS_VIOLATION',
                    'Place position validation failed',
                    details={'errors': errors}
                )
        
        # Create command
        command = OpenPNPCommand(
            command_type=OpenPNPCommandType.PICK_AND_PLACE,
            parameters={
                'x': x,
                'y': y,
                'place_x': place_x,
                'place_y': place_y,
                'pick_height': pick_height,
                'place_height': place_height,
                'safe_height': safe_height,
                'feedrate': feedrate,
                'vacuum_power': vacuum_power
            }
        )
        
        # Execute command
        response = await server.execute_command(command)
        
        # Return response
        return create_response(response.to_dict())
    
    except Exception as e:
        logger.error(f"Error handling pick_and_place command: {e}", exc_info=True)
        return create_error_response(
            'EXECUTION_ERROR',
            str(e),
            status=500
        )
