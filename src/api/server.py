#!/usr/bin/env python3
# KlipperPlace REST API Server
# Main API server for OpenPNP integration using aiohttp

import logging
import time
import uuid
from typing import Optional, Dict, Any
import aiohttp
from aiohttp import web
import asyncio

# Import middleware components
from middleware.translator import (
    OpenPNPTranslator,
    OpenPNPCommand,
    OpenPNPCommandType,
    OpenPNPResponse,
    ResponseStatus
)
from middleware.cache import StateCacheManager, CacheCategory
from middleware.safety import SafetyManager, SafetyLimits

# Import authentication
from .auth import create_auth_manager, APIKeyManager, AuthLogger

# Import routes
from .routes import setup_routes

# Component logging
logger = logging.getLogger(__name__)


class APIServer:
    """Main API server for KlipperPlace OpenPNP integration."""
    
    def __init__(self,
                 host: str = 'localhost',
                 port: int = 7125,
                 moonraker_host: str = 'localhost',
                 moonraker_port: int = 7125,
                 moonraker_api_key: Optional[str] = None,
                 api_key_enabled: bool = False,
                 api_key: Optional[str] = None,
                 enable_cors: bool = True,
                 auth_config: Optional[Dict[str, Any]] = None):
        """Initialize API server.
        
        Args:
            host: API server host address
            port: API server port
            moonraker_host: Moonraker host address
            moonraker_port: Moonraker port
            moonraker_api_key: Optional Moonraker API key
            api_key_enabled: Enable API key authentication
            api_key: API key for authentication (legacy, for backward compatibility)
            enable_cors: Enable CORS support
            auth_config: Authentication configuration dictionary
        """
        self.host = host
        self.port = port
        self.moonraker_host = moonraker_host
        self.moonraker_port = moonraker_port
        self.moonraker_api_key = moonraker_api_key
        self.api_key_enabled = api_key_enabled
        self.api_key = api_key
        self.enable_cors = enable_cors
        
        # Initialize authentication components
        if auth_config is None:
            auth_config = {}
        
        # Add legacy api_key to config if provided
        if api_key and not auth_config.get('api_key'):
            auth_config['api_key'] = api_key
        
        auth_config['api_key_enabled'] = api_key_enabled
        auth_config['api_key_storage_path'] = auth_config.get('api_key_storage_path', 'config/api_keys.json')
        
        self.key_manager, self.auth_middleware, self.auth_logger = create_auth_manager(auth_config)
        
        # Initialize middleware components
        self.translator = OpenPNPTranslator(
            moonraker_host=moonraker_host,
            moonraker_port=moonraker_port,
            moonraker_api_key=moonraker_api_key
        )
        
        self.cache_manager = StateCacheManager(
            moonraker_host=moonraker_host,
            moonraker_port=moonraker_port,
            moonraker_api_key=moonraker_api_key
        )
        
        self.safety_manager = SafetyManager(
            moonraker_host=moonraker_host,
            moonraker_port=moonraker_port,
            moonraker_api_key=moonraker_api_key,
            cache_manager=self.cache_manager
        )
        
        # Aiohttp app
        self.app: Optional[web.Application] = None
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        
        # Server state
        self._running = False
        
        logger.info(f"API server initialized on {host}:{port}")
    
    async def start(self) -> None:
        """Start the API server."""
        if self._running:
            logger.warning("API server is already running")
            return
        
        logger.info("Starting API server...")
        
        # Start middleware components
        await self.cache_manager.start()
        await self.safety_manager.start()
        
        # Create aiohttp application
        self.app = web.Application()
        
        # Store server instance in app for route access
        self.app['server'] = self
        
        # Setup CORS middleware if enabled
        if self.enable_cors:
            self._setup_cors()
        
        # Setup authentication middleware
        self.app.middlewares.append(self.auth_middleware.middleware)
        
        # Setup routes
        setup_routes(self.app)
        
        # Create runner and site
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, self.host, self.port)
        
        # Start server
        await self.site.start()
        self._running = True
        
        logger.info(f"API server started on http://{self.host}:{self.port}")
    
    async def stop(self) -> None:
        """Stop the API server."""
        if not self._running:
            return
        
        logger.info("Stopping API server...")
        self._running = False
        
        # Stop middleware components
        await self.safety_manager.stop()
        await self.cache_manager.stop()
        
        # Stop server
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        
        logger.info("API server stopped")
    
    def _setup_cors(self) -> None:
        """Setup CORS middleware."""
        @web.middleware
        async def cors_middleware(request: web.Request, handler):
            """CORS middleware handler."""
            # Handle preflight requests
            if request.method == 'OPTIONS':
                response = web.Response()
                response.headers['Access-Control-Allow-Origin'] = '*'
                response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-API-Key'
                response.headers['Access-Control-Max-Age'] = '86400'
                return response
            
            # Handle regular requests
            response = await handler(request)
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-API-Key'
            return response
        
        self.app.middlewares.append(cors_middleware)
        logger.info("CORS middleware enabled")
    
    @web.middleware
    async def error_middleware(request: web.Request, handler):
        """Error handling middleware."""
        try:
            return await handler(request)
        except web.HTTPException as e:
            logger.error(f"HTTP error: {e}")
            return web.json_response(
                {
                    'status': 'error',
                    'error_code': 'HTTP_ERROR',
                    'error_message': str(e)
                },
                status=e.status
            )
        except Exception as e:
            logger.error(f"Unhandled error: {e}", exc_info=True)
            return web.json_response(
                {
                    'status': 'error',
                    'error_code': 'INTERNAL_ERROR',
                    'error_message': 'Internal server error'
                },
                status=500
            )
    
    @web.middleware
    async def logging_middleware(request: web.Request, handler):
        """Request logging middleware."""
        start_time = time.time()
        
        # Log request
        logger.info(f"{request.method} {request.path} from {request.remote}")
        
        # Process request
        response = await handler(request)
        
        # Log response
        duration = time.time() - start_time
        logger.info(f"{request.method} {request.path} -> {response.status} ({duration:.3f}s)")
        
        # Add timing header
        response.headers['X-Response-Time'] = f'{duration:.3f}'
        
        return response
    
    async def execute_command(self, command: OpenPNPCommand) -> OpenPNPResponse:
        """Execute an OpenPNP command through the translator.
        
        Args:
            command: OpenPNP command to execute
            
        Returns:
            OpenPNPResponse object
        """
        return await self.translator.translate_and_execute(command)
    
    async def execute_batch(self, commands: list, stop_on_error: bool = True) -> list:
        """Execute a batch of commands.
        
        Args:
            commands: List of command dictionaries
            stop_on_error: Stop on first error
            
        Returns:
            List of OpenPNPResponse objects
        """
        return await self.translator.execute_batch(commands, stop_on_error)
    
    def is_running(self) -> bool:
        """Check if server is running.
        
        Returns:
            True if server is running
        """
        return self._running


def create_app(config: Optional[Dict[str, Any]] = None) -> web.Application:
    """Factory function to create and configure API application.
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        Configured aiohttp application
    """
    if config is None:
        config = {}
    
    # Extract configuration
    host = config.get('host', 'localhost')
    port = config.get('port', 7125)
    moonraker_host = config.get('moonraker_host', 'localhost')
    moonraker_port = config.get('moonraker_port', 7125)
    moonraker_api_key = config.get('moonraker_api_key')
    api_key_enabled = config.get('api_key_enabled', False)
    api_key = config.get('api_key')
    enable_cors = config.get('enable_cors', True)
    
    # Create server instance
    server = APIServer(
        host=host,
        port=port,
        moonraker_host=moonraker_host,
        moonraker_port=moonraker_port,
        moonraker_api_key=moonraker_api_key,
        api_key_enabled=api_key_enabled,
        api_key=api_key,
        enable_cors=enable_cors,
        auth_config=config
    )
    
    # Create application
    app = web.Application()
    app['server'] = server
    app['config'] = config
    
    # Setup middleware
    if enable_cors:
        server._setup_cors()
    
    app.middlewares.append(server.auth_middleware.middleware)
    app.middlewares.append(server.error_middleware)
    app.middlewares.append(server.logging_middleware)
    
    # Setup routes
    setup_routes(app)
    
    return app


async def run_server(config: Optional[Dict[str, Any]] = None) -> APIServer:
    """Run the API server.
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        Running APIServer instance
    """
    if config is None:
        config = {}
    
    server = APIServer(
        host=config.get('host', 'localhost'),
        port=config.get('port', 7125),
        moonraker_host=config.get('moonraker_host', 'localhost'),
        moonraker_port=config.get('moonraker_port', 7125),
        moonraker_api_key=config.get('moonraker_api_key'),
        api_key_enabled=config.get('api_key_enabled', False),
        api_key=config.get('api_key'),
        enable_cors=config.get('enable_cors', True),
        auth_config=config
    )
    
    await server.start()
    return server
