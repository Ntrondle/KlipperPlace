#!/usr/bin/env python3
# Integration Test Configuration and Fixtures
# Shared fixtures for all integration tests

import pytest
import pytest_asyncio
import asyncio
import json
from typing import Dict, Any, Optional, List
from unittest.mock import AsyncMock, MagicMock, patch
from aiohttp import web, ClientSession
import aiohttp

# Import components to test
from api.server import APIServer
from middleware.translator import (
    OpenPNPTranslator,
    OpenPNPCommand,
    OpenPNPCommandType,
    OpenPNPResponse,
    ResponseStatus
)
from middleware.cache import StateCacheManager, CacheCategory
from middleware.safety import SafetyManager, SafetyLimits
from api.auth import APIKeyManager, AuthMiddleware, AuthLogger
from gcode_driver.translator import CommandTranslator, MoonrakerClient


# Test configuration
MOONRAKER_HOST = 'localhost'
MOONRAKER_PORT = 7125
API_HOST = 'localhost'
API_PORT = 7126
MOCK_API_KEY = 'test_api_key_12345678'


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def mock_moonraker_client():
    """Create a mock Moonraker client for testing."""
    client = MagicMock(spec=MoonrakerClient)
    client.host = MOONRAKER_HOST
    client.port = MOONRAKER_PORT
    client.base_url = f"http://{MOONRAKER_HOST}:{MOONRAKER_PORT}"
    client.api_key = None
    
    # Mock session
    mock_session = AsyncMock()
    client.session = mock_session
    
    # Mock _make_request method
    async def mock_make_request(method: str, endpoint: str, data: Optional[Dict] = None):
        """Mock Moonraker API requests."""
        if endpoint == '/api/printer/gcode/script':
            return {
                'result': {
                    'status': 'ok',
                    'result': 'ok'
                }
            }
        elif endpoint == '/api/printer/status':
            return {
                'result': {
                    'state': 'ready',
                    'print_stats': {'state': 'idle'},
                    'toolhead': {'position': [0.0, 0.0, 0.0]}
                }
            }
        elif endpoint == '/api/server/connection':
            return {
                'result': {
                    'state': 'ready'
                }
            }
        elif endpoint == '/api/printer/query':
            return {
                'result': {
                    'toolhead': {'position': [0.0, 0.0, 0.0]},
                    'fan': {'speed': 0.0},
                    'output_pin': {}
                }
            }
        return {'result': {}}
    
    client._make_request = mock_make_request
    
    # Mock async context manager
    async def mock_enter():
        return client
    
    async def mock_exit(*args):
        pass
    
    client.__aenter__ = mock_enter
    client.__aexit__ = mock_exit
    
    yield client


@pytest_asyncio.fixture
async def mock_cache_manager():
    """Create a mock cache manager for testing."""
    cache = MagicMock(spec=StateCacheManager)
    cache.moonraker_host = MOONRAKER_HOST
    cache.moonraker_port = MOONRAKER_PORT
    cache.moonraker_api_key = None
    
    # Mock cache methods
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    cache.invalidate = AsyncMock(return_value=True)
    cache.invalidate_category = AsyncMock(return_value=1)
    cache.start = AsyncMock()
    cache.stop = AsyncMock()
    cache.get_statistics = AsyncMock(return_value={
        'hits': 0,
        'misses': 0,
        'hit_rate': 0.0
    })
    
    yield cache


@pytest_asyncio.fixture
async def mock_safety_manager():
    """Create a mock safety manager for testing."""
    safety = MagicMock(spec=SafetyManager)
    safety.limits = SafetyLimits()
    
    # Mock safety methods
    safety.start = AsyncMock()
    safety.stop = AsyncMock()
    safety.validate_move_command = AsyncMock(return_value=(True, []))
    safety.validate_temperature_command = AsyncMock(return_value=(True, ""))
    safety.validate_fan_command = AsyncMock(return_value=(True, ""))
    safety.check_temperature_limits = AsyncMock(return_value=[])
    safety.check_position_limits = AsyncMock(return_value=[])
    safety.check_pwm_limits = AsyncMock(return_value=None)
    safety.emergency_stop = AsyncMock()
    safety.mark_axis_homed = AsyncMock()
    safety.get_statistics = AsyncMock(return_value={
        'total_events': 0,
        'emergency_stops': 0
    })
    
    yield safety


@pytest_asyncio.fixture
async def api_key_manager():
    """Create an API key manager for testing."""
    manager = APIKeyManager(storage_path=None)
    yield manager


@pytest_asyncio.fixture
async def auth_manager(api_key_manager):
    """Create an auth manager for testing."""
    auth_logger = AuthLogger()
    middleware = AuthMiddleware(
        key_manager=api_key_manager,
        auth_logger=auth_logger,
        require_auth=False  # Disable auth for testing
    )
    yield api_key_manager, middleware, auth_logger


@pytest_asyncio.fixture
async def openpnp_translator(mock_moonraker_client):
    """Create an OpenPNP translator for testing."""
    translator = OpenPNPTranslator(
        moonraker_host=MOONRAKER_HOST,
        moonraker_port=MOONRAKER_PORT,
        moonraker_api_key=None
    )
    
    # Mock the gcode_translator's moonraker client
    translator.gcode_translator._moonraker_client = mock_moonraker_client
    
    yield translator


@pytest_asyncio.fixture
async def api_server(auth_manager, mock_cache_manager, mock_safety_manager):
    """Create an API server for testing."""
    key_manager, auth_middleware, auth_logger = auth_manager
    
    server = APIServer(
        host=API_HOST,
        port=API_PORT,
        moonraker_host=MOONRAKER_HOST,
        moonraker_port=MOONRAKER_PORT,
        moonraker_api_key=None,
        api_key_enabled=False,  # Disable auth for testing
        enable_cors=True
    )
    
    # Replace middleware components with mocks
    server.cache_manager = mock_cache_manager
    server.safety_manager = mock_safety_manager
    
    # Start server
    await server.start()
    
    yield server
    
    # Cleanup
    await server.stop()


@pytest_asyncio.fixture
async def api_client(api_server):
    """Create an HTTP client for API testing."""
    base_url = f"http://{API_HOST}:{API_PORT}"
    
    async with ClientSession() as session:
        yield session, base_url


# Helper functions for tests

def create_openpnp_command(command_type: OpenPNPCommandType, 
                         parameters: Dict[str, Any] = None) -> OpenPNPCommand:
    """Create an OpenPNP command for testing."""
    return OpenPNPCommand(
        command_type=command_type,
        parameters=parameters or {}
    )


def create_mock_moonraker_response(success: bool = True, 
                                 data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Create a mock Moonraker API response."""
    response = {'success': success}
    if data:
        response.update(data)
    return response


def assert_response_success(response: OpenPNPResponse, 
                         command_type: str = None) -> None:
    """Assert that an OpenPNP response is successful."""
    assert response.status == ResponseStatus.SUCCESS, \
        f"Expected success, got {response.status}: {response.error_message}"
    if command_type:
        assert response.command == command_type, \
            f"Expected command {command_type}, got {response.command}"
    assert response.data is not None, "Response data should not be None"


def assert_response_error(response: OpenPNPResponse,
                      expected_error_code: str = None) -> None:
    """Assert that an OpenPNP response is an error."""
    assert response.status == ResponseStatus.ERROR, \
        f"Expected error, got {response.status}"
    assert response.error_message is not None, "Error message should not be None"
    if expected_error_code:
        assert response.error_code == expected_error_code, \
            f"Expected error code {expected_error_code}, got {response.error_code}"


async def make_api_request(client: ClientSession, 
                         base_url: str,
                         method: str,
                         endpoint: str,
                         data: Dict[str, Any] = None,
                         headers: Dict[str, str] = None) -> Dict[str, Any]:
    """Helper function to make API requests."""
    url = f"{base_url}{endpoint}"
    request_headers = {'Content-Type': 'application/json'}
    if headers:
        request_headers.update(headers)
    
    async with client.request(
        method,
        url,
        json=data,
        headers=request_headers
    ) as response:
        return {
            'status': response.status,
            'data': await response.json()
        }


# Test data fixtures

@pytest.fixture
def sample_move_command():
    """Sample move command for testing."""
    return {
        'command': 'move',
        'parameters': {
            'x': 100.0,
            'y': 50.0,
            'z': 10.0,
            'feedrate': 1500.0
        }
    }


@pytest.fixture
def sample_pick_command():
    """Sample pick command for testing."""
    return {
        'command': 'pick',
        'parameters': {
            'x': 100.0,
            'y': 50.0,
            'z': 0.0,
            'vacuum_power': 255,
            'travel_height': 5.0
        }
    }


@pytest.fixture
def sample_place_command():
    """Sample place command for testing."""
    return {
        'command': 'place',
        'parameters': {
            'x': 200.0,
            'y': 100.0,
            'z': 0.0,
            'travel_height': 5.0
        }
    }


@pytest.fixture
def sample_fan_command():
    """Sample fan command for testing."""
    return {
        'command': 'fan_set',
        'parameters': {
            'speed': 0.5,
            'fan': 'fan'
        }
    }


@pytest.fixture
def sample_gpio_command():
    """Sample GPIO command for testing."""
    return {
        'command': 'gpio_read',
        'parameters': {
            'pin': 'PA1'
        }
    }


@pytest.fixture
def sample_sensor_command():
    """Sample sensor command for testing."""
    return {
        'command': 'sensor_read',
        'parameters': {
            'sensor': 'temperature_sensor'
        }
    }


@pytest.fixture
def sample_batch_commands():
    """Sample batch commands for testing."""
    return [
        {'command': 'home', 'parameters': {}},
        {'command': 'move', 'parameters': {'x': 100.0, 'y': 50.0, 'z': 10.0}},
        {'command': 'pick', 'parameters': {'z': 0.0, 'vacuum_power': 255}},
        {'command': 'move', 'parameters': {'x': 200.0, 'y': 100.0}},
        {'command': 'place', 'parameters': {'z': 0.0}},
    ]


# Async test configuration
pytest_plugins = ('pytest_asyncio',)
