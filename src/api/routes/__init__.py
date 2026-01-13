#!/usr/bin/env python3
# API Routes Package
# Route handlers for KlipperPlace REST API

from aiohttp import web
import logging

logger = logging.getLogger(__name__)


def setup_routes(app: web.Application) -> None:
    """Setup all API routes.
    
    Args:
        app: aiohttp application
    """
    # Import route modules
    from . import (
        motion_routes,
        pnp_routes,
        actuator_routes,
        vacuum_routes,
        fan_routes,
        pwm_routes,
        gpio_routes,
        sensor_routes,
        feeder_routes,
        status_routes,
        queue_routes,
        system_routes,
        batch_routes,
        version_routes,
        auth_routes
    )
    
    # Setup routes
    motion_routes.setup(app)
    pnp_routes.setup(app)
    actuator_routes.setup(app)
    vacuum_routes.setup(app)
    fan_routes.setup(app)
    pwm_routes.setup(app)
    gpio_routes.setup(app)
    sensor_routes.setup(app)
    feeder_routes.setup(app)
    status_routes.setup(app)
    queue_routes.setup(app)
    system_routes.setup(app)
    batch_routes.setup(app)
    version_routes.setup(app)
    auth_routes.setup(app)
    
    logger.info("All API routes registered")


def create_response(data: dict, status: int = 200) -> web.Response:
    """Create a JSON response.
    
    Args:
        data: Response data dictionary
        status: HTTP status code
        
    Returns:
        aiohttp web response
    """
    return web.json_response(data, status=status)


def create_error_response(error_code: str, error_message: str, 
                       details: dict = None, status: int = 400) -> web.Response:
    """Create an error response.
    
    Args:
        error_code: Error code
        error_message: Error message
        details: Optional error details
        status: HTTP status code
        
    Returns:
        aiohttp web response
    """
    response = {
        'status': 'error',
        'error_code': error_code,
        'error_message': error_message
    }
    
    if details:
        response['details'] = details
    
    return web.json_response(response, status=status)
