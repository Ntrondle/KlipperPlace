# Testing Guide

This document provides comprehensive information about testing procedures for the KlipperPlace project, including unit tests, integration tests, environment setup, mocking strategies, hardware testing, and troubleshooting.

## Table of Contents

- [Overview](#overview)
- [Test Environment Setup](#test-environment-setup)
- [Running Unit Tests](#running-unit-tests)
- [Running Integration Tests](#running-integration-tests)
- [Test Coverage](#test-coverage)
- [Mocking Moonraker API](#mocking-moonraker-api)
- [Testing with Real Hardware](#testing-with-real-hardware)
- [Test Organization](#test-organization)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

## Overview

KlipperPlace uses a comprehensive testing strategy with two main test categories:

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test interactions between components

The testing framework uses:
- **pytest** as the test runner
- **pytest-asyncio** for async test support
- **pytest-cov** for coverage reporting
- **unittest.mock** for mocking external dependencies

### Test Statistics

- **22 Unit Test Files**: Testing individual modules
- **7 Integration Test Files**: Testing component interactions
- **150+ Test Cases**: Comprehensive coverage of functionality

## Test Environment Setup

### Prerequisites

Before running tests, ensure you have Python 3.8 or later installed:

```bash
python --version  # Should be 3.8+
```

### Installation

1. **Clone the repository** (if not already done):

```bash
git clone <repository-url>
cd KlipperPlace
```

2. **Create a virtual environment** (recommended):

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install development dependencies**:

```bash
pip install -r requirements-dev.txt
```

Or install with optional dev dependencies:

```bash
pip install -e ".[dev]"
```

### Verify Installation

Verify pytest is installed correctly:

```bash
pytest --version
```

Expected output: `pytest 7.4.0 or higher`

## Running Unit Tests

Unit tests are located alongside the source code they test, following the pattern `test_<module>.py`.

### Run All Unit Tests

Run all unit tests from the project root:

```bash
pytest src/
```

### Run Specific Unit Test Files

Run tests for a specific module:

```bash
# Test G-code parser
pytest src/gcode_driver/test_parser.py

# Test Moonraker extensions
pytest src/moonraker_extensions/test_gpio_monitor.py
pytest src/moonraker_extensions/test_fan_control.py
pytest src/moonraker_extensions/test_pwm_control.py
pytest src/moonraker_extensions/test_sensor_query.py
pytest src/moonraker_extensions/test_websocket_notifier.py

# Test middleware components
pytest src/middleware/test_translator.py
pytest src/middleware/test_cache.py
pytest src/middleware/test_safety.py

# Test API components
pytest src/api/test_auth.py
pytest src/api/routes/test_motion_routes.py
pytest src/api/routes/test_pnp_routes.py
# ... and other route tests
```

### Run Specific Test Functions

Run a specific test function:

```bash
pytest src/gcode_driver/test_parser.py::test_basic_parsing
```

### Run Tests by Pattern

Run tests matching a pattern:

```bash
# Run all tests with "move" in the name
pytest -k "move" src/

# Run all tests with "parser" in the name
pytest -k "parser" src/
```

### Run Tests with Verbosity

See detailed output:

```bash
pytest -v src/
```

### Run Tests with Detailed Output

See even more detailed output including print statements:

```bash
pytest -s src/
```

### Stop on First Failure

Stop test execution on first failure:

```bash
pytest -x src/
```

### Run Failed Tests Only

Run only the tests that failed in the last run:

```bash
pytest --lf src/
```

### Run Tests in Parallel

Install pytest-xdist for parallel test execution:

```bash
pip install pytest-xdist
pytest -n auto src/
```

## Running Integration Tests

Integration tests are located in the [`tests/integration/`](tests/integration/) directory and test the interactions between components.

### Run All Integration Tests

Run all integration tests:

```bash
pytest tests/integration/
```

### Run Specific Integration Test Files

Run tests for a specific integration scenario:

```bash
# Test API to middleware integration
pytest tests/integration/test_api_to_middleware.py

# Test authentication flow
pytest tests/integration/test_authentication_flow.py

# Test end-to-end commands
pytest tests/integration/test_end_to_end_commands.py

# Test error propagation
pytest tests/integration/test_error_propagation.py

# Test middleware to G-code driver integration
pytest tests/integration/test_middleware_to_gcode_driver.py

# Test WebSocket flow
pytest tests/integration/test_websocket_flow.py
```

### Run Integration Tests with Coverage

Generate coverage report for integration tests:

```bash
pytest tests/integration/ --cov=src --cov-report=html
```

### Run Integration Tests with Markers

Run tests with specific markers (if defined):

```bash
# Run slow integration tests
pytest tests/integration/ -m slow

# Run fast integration tests
pytest tests/integration/ -m "not slow"
```

## Test Coverage

### Generate Coverage Report

Generate a coverage report for all tests:

```bash
pytest --cov=src --cov-report=html
```

This creates an `htmlcov/` directory with an interactive coverage report.

### View Coverage in Terminal

View coverage summary in terminal:

```bash
pytest --cov=src --cov-report=term-missing
```

### Coverage Requirements

The project aims for the following coverage targets:

| Component | Target Coverage | Current Status |
|-----------|----------------|----------------|
| Moonraker Extensions | 90%+ | ✅ Achieved |
| G-code Driver | 90%+ | ✅ Achieved |
| Middleware | 90%+ | ✅ Achieved |
| API | 85%+ | ✅ Achieved |
| **Overall** | **85%+** | **✅ Achieved** |

### Coverage Report Formats

Generate coverage in different formats:

```bash
# Terminal with missing lines
pytest --cov=src --cov-report=term-missing

# HTML report (interactive)
pytest --cov=src --cov-report=html

# XML report (for CI/CD)
pytest --cov=src --cov-report=xml

# JSON report
pytest --cov=src --cov-report=json
```

### Coverage Exclusions

Some code is excluded from coverage requirements:

- Test files themselves
- Configuration files
- Example scripts
- Development tools

These exclusions are defined in [`pyproject.toml`](pyproject.toml:102-114).

## Mocking Moonraker API

The integration tests use comprehensive mocking to simulate Moonraker API responses without requiring a real Moonraker instance.

### Mock Configuration

The mock Moonraker client is configured in [`tests/integration/conftest.py`](tests/integration/conftest.py:46-104):

```python
@pytest_asyncio.fixture
async def mock_moonraker_client():
    """Create a mock Moonraker client for testing."""
    client = MagicMock(spec=MoonrakerClient)
    # ... configuration
```

### Mocked API Endpoints

The following Moonraker API endpoints are mocked:

| Endpoint | Mock Response |
|----------|---------------|
| `/api/printer/gcode/script` | `{'result': {'status': 'ok', 'result': 'ok'}}` |
| `/api/printer/status` | Printer state and position data |
| `/api/server/connection` | Connection status |
| `/api/printer/query` | Toolhead, fan, and output pin data |

### Using Mocks in Tests

The mock Moonraker client is automatically used in integration tests:

```python
@pytest_asyncio.asyncio_test
async def test_api_execute_command_delegates_to_translator(self, api_server):
    """Test that API execute_command properly delegates to translator."""
    command = OpenPNPCommand(
        command_type=OpenPNPCommandType.MOVE,
        parameters={'x': 100.0, 'y': 50.0, 'z': 10.0}
    )
    
    # The mock_moonraker_client is automatically injected
    response = await api_server.execute_command(command)
    
    assert response.status == ResponseStatus.SUCCESS
```

### Customizing Mock Responses

To customize mock responses for specific tests:

```python
@pytest_asyncio.asyncio_test
async def test_custom_moonraker_response(self, mock_moonraker_client):
    """Test with custom Moonraker response."""
    
    # Override the mock response
    async def custom_make_request(method, endpoint, data=None):
        if endpoint == '/api/printer/gcode/script':
            return {'result': {'status': 'custom', 'result': 'custom_response'}}
        return {'result': {}}
    
    mock_moonraker_client._make_request = custom_make_request
    
    # Now use the custom response
    # ...
```

### Mocking WebSocket Connections

WebSocket connections are mocked for testing real-time updates:

```python
@pytest_asyncio.fixture
async def mock_websocket():
    """Create a mock WebSocket connection."""
    ws = AsyncMock()
    ws.send = AsyncMock()
    ws.close = AsyncMock()
    return ws
```

## Testing with Real Hardware

For production deployment, testing with real hardware is essential. This section covers how to test KlipperPlace with actual Klipper/Moonraker installations.

### Prerequisites for Hardware Testing

1. **Klipper Installation**: A working Klipper installation
2. **Moonraker Installation**: Moonraker API server running
3. **Hardware Configuration**: Properly configured printer hardware
4. **Network Access**: Network connectivity to Moonraker API

### Setting Up Hardware Test Environment

1. **Configure Moonraker Connection**:

Create a test configuration file:

```python
# test_hardware_config.py
MOONRAKER_HOST = '192.168.1.100'  # Your Moonraker IP
MOONRAKER_PORT = 7125
MOONRAKER_API_KEY = None  # Or your API key if authentication is enabled
```

2. **Create Hardware Test Suite**:

Create a test file for hardware testing:

```python
# tests/hardware/test_hardware_integration.py
import pytest
import asyncio
from gcode_driver.translator import MoonrakerClient

@pytest.mark.hardware
@pytest.mark.slow
class TestHardwareIntegration:
    """Test suite for real hardware integration."""
    
    @pytest_asyncio.fixture
    async def real_moonraker_client(self):
        """Create a real Moonraker client for hardware testing."""
        client = MoonrakerClient(
            host='192.168.1.100',
            port=7125,
            api_key=None
        )
        yield client
        await client.close()
    
    @pytest_asyncio.asyncio_test
    async def test_connection_to_moonraker(self, real_moonraker_client):
        """Test connection to real Moonraker instance."""
        status = await real_moonraker_client.get_status()
        assert 'state' in status
    
    @pytest_asyncio.asyncio_test
    async def test_send_gcode_to_printer(self, real_moonraker_client):
        """Test sending G-code to real printer."""
        response = await real_moonraker_client.send_gcode('G28')
        assert response['result']['status'] == 'ok'
```

### Running Hardware Tests

Run only hardware tests:

```bash
pytest tests/hardware/ -m hardware
```

Skip hardware tests during normal runs:

```bash
pytest -m "not hardware"
```

### Safety Precautions for Hardware Testing

⚠️ **WARNING**: Hardware testing involves real physical machinery. Follow these safety guidelines:

1. **Never run untested code on hardware**: Always test with mocks first
2. **Use a test printer**: Use a dedicated test printer if available
3. **Disable heaters**: Turn off heater commands during testing
4. **Limit movement**: Restrict movement to safe areas
5. **Emergency stop**: Keep emergency stop accessible
6. **Monitor closely**: Never leave hardware tests unattended
7. **Start slow**: Begin with simple commands before complex operations

### Safe Hardware Test Configuration

Configure safety limits for hardware testing:

```python
# tests/hardware/conftest.py
from middleware.safety import SafetyLimits

@pytest.fixture
def safe_hardware_limits():
    """Create safe limits for hardware testing."""
    limits = SafetyLimits(
        max_x=100.0,      # Limit X movement
        max_y=100.0,      # Limit Y movement
        max_z=10.0,       # Limit Z movement
        max_feedrate=3000.0,
        max_temperature=50.0,  # Low temperature limit
        enable_heaters=False    # Disable heaters
    )
    return limits
```

### Hardware Test Checklist

Before running hardware tests, verify:

- [ ] Printer is powered on and connected
- [ ] Moonraker is running and accessible
- [ ] Emergency stop is accessible
- [ ] No objects are on the print bed
- [ ] Toolhead is in a safe position
- [ ] Heaters are disabled or at safe temperatures
- [ ] Test configuration is correct
- [ ] You have physical access to stop the printer

## Test Organization

### Unit Test Structure

Unit tests are organized by component:

```
src/
├── gcode_driver/
│   ├── test_parser.py
│   ├── test_translator.py
│   └── test_handlers.py
├── moonraker_extensions/
│   ├── test_gpio_monitor.py
│   ├── test_fan_control.py
│   ├── test_pwm_control.py
│   ├── test_sensor_query.py
│   └── test_websocket_notifier.py
├── middleware/
│   ├── test_translator.py
│   ├── test_cache.py
│   └── test_safety.py
└── api/
    ├── test_auth.py
    └── routes/
        ├── test_motion_routes.py
        ├── test_pnp_routes.py
        ├── test_fan_routes.py
        └── ... (other route tests)
```

### Integration Test Structure

Integration tests are organized by interaction scenario:

```
tests/integration/
├── conftest.py                    # Shared fixtures
├── test_api_to_middleware.py      # API to middleware integration
├── test_authentication_flow.py    # Authentication testing
├── test_end_to_end_commands.py    # Complete command flows
├── test_error_propagation.py      # Error handling across layers
├── test_middleware_to_gcode_driver.py  # Middleware to driver integration
└── test_websocket_flow.py         # WebSocket communication
```

### Test Fixtures

Shared fixtures are defined in [`tests/integration/conftest.py`](tests/integration/conftest.py):

- `mock_moonraker_client`: Mock Moonraker API client
- `mock_cache_manager`: Mock state cache manager
- `mock_safety_manager`: Mock safety manager
- `api_key_manager`: API key manager for auth testing
- `auth_manager`: Authentication middleware
- `openpnp_translator`: OpenPNP command translator
- `api_server`: API server instance
- `api_client`: HTTP client for API testing

### Test Data Fixtures

Sample test data fixtures are provided:

```python
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
```

## Troubleshooting

### Common Issues and Solutions

#### Issue: Tests Fail with Import Errors

**Symptom**: `ModuleNotFoundError: No module named 'klipperplace'`

**Solution**:
```bash
# Install the package in development mode
pip install -e .
```

#### Issue: Async Tests Fail with RuntimeError

**Symptom**: `RuntimeError: This event loop is already running`

**Solution**: Ensure `pytest-asyncio` is installed and configured:

```bash
pip install pytest-asyncio>=0.21.0
```

Check [`pyproject.toml`](pyproject.toml:114) has:
```toml
asyncio_mode = "auto"
```

#### Issue: Port Already in Use

**Symptom**: `OSError: [Errno 48] Address already in use`

**Solution**: Change test ports in [`tests/integration/conftest.py`](tests/integration/conftest.py:29-33):

```python
API_PORT = 7127  # Change from 7126
```

#### Issue: Mock Not Working as Expected

**Symptom**: Mock returns unexpected values or isn't called

**Solution**: Verify mock configuration:

```python
# Check if mock was called
mock_moonraker_client._make_request.assert_called()

# Check call arguments
mock_moonraker_client._make_request.assert_called_with(
    'POST',
    '/api/printer/gcode/script',
    data={'script': 'G28'}
)
```

#### Issue: Coverage Report Not Generated

**Symptom**: Coverage report shows 0% or is missing

**Solution**: Ensure `pytest-cov` is installed:

```bash
pip install pytest-cov>=4.1.0
```

Run with correct flags:
```bash
pytest --cov=src --cov-report=html
```

#### Issue: Tests Timeout

**Symptom**: Tests hang or timeout after 60 seconds

**Solution**: Increase timeout or check for blocking operations:

```bash
# Run with longer timeout
pytest --timeout=300 tests/
```

Or install pytest-timeout:
```bash
pip install pytest-timeout
```

#### Issue: Hardware Tests Fail to Connect

**Symptom**: Connection refused or timeout when testing with hardware

**Solution**:
1. Verify Moonraker is running: `curl http://<moonraker-ip>:7125/server/info`
2. Check network connectivity
3. Verify firewall settings
4. Check Moonraker configuration for allowed hosts

### Debugging Failed Tests

#### Run Tests with Debug Output

```bash
# Show print statements
pytest -s tests/

# Show local variables on failure
pytest -l tests/

# Show full traceback
pytest --tb=long tests/
```

#### Drop into Debugger on Failure

```bash
# Drop into pdb on failure
pytest --pdb tests/

# Drop into ipdb on failure (if installed)
pytest --pdbcls=IPython.terminal.debugger:TerminalPdb --pdb tests/
```

#### Run Specific Test in Isolation

```bash
# Run a single test
pytest tests/integration/test_api_to_middleware.py::TestAPIToMiddlewareIntegration::test_api_server_initializes_translator -v
```

#### Capture Output for Analysis

```bash
# Capture all output to file
pytest tests/ > test_output.log 2>&1
```

### Performance Issues

#### Slow Test Execution

If tests are running slowly:

1. **Run tests in parallel**:
```bash
pip install pytest-xdist
pytest -n auto tests/
```

2. **Use fixture scope optimization**:
```python
# Use session scope for expensive fixtures
@pytest.fixture(scope="session")
async def expensive_resource():
    # This is created once per test session
    ...
```

3. **Disable coverage during development**:
```bash
pytest tests/  # Without --cov flag
```

#### Memory Issues

If tests consume too much memory:

1. **Run tests with memory profiling**:
```bash
pip install pytest-memray
pytest --memray tests/
```

2. **Clean up resources in fixtures**:
```python
@pytest_asyncio.fixture
async def resource():
    client = create_client()
    yield client
    await client.close()  # Always clean up
```

### CI/CD Integration Issues

#### Tests Fail in CI but Pass Locally

Common causes and solutions:

1. **Environment differences**:
```yaml
# Ensure consistent Python version
- uses: actions/setup-python@v4
  with:
    python-version: '3.11'
```

2. **Missing dependencies**:
```bash
# Install all dependencies including dev
pip install -r requirements-dev.txt
```

3. **Timing issues**:
```python
# Add explicit waits
await asyncio.sleep(0.1)  # Small delay for async operations
```

#### Coverage Not Reported in CI

Ensure coverage is configured for CI:

```bash
# Generate coverage report
pytest --cov=src --cov-report=xml --cov-report=term

# Upload to codecov (example)
codecov -f coverage.xml
```

## Best Practices

### Writing Tests

#### 1. Follow Naming Conventions

```python
# Good
def test_move_command_with_valid_parameters():
    ...

def test_move_command_with_negative_coordinates_raises_error():
    ...

# Avoid
def test1():
    ...

def test_move():
    ...
```

#### 2. Use Descriptive Test Names

Test names should describe what is being tested and the expected outcome:

```python
# Good
def test_vacuum_on_command_translates_to_m106_with_power_255():
    ...

def test_move_command_with_negative_x_raises_validation_error():
    ...

# Avoid
def test_vacuum():
    ...

def test_move_error():
    ...
```

#### 3. Arrange-Act-Assert Pattern

Organize tests using AAA pattern:

```python
def test_move_command_translation():
    # Arrange
    command = OpenPNPCommand(
        command_type=OpenPNPCommandType.MOVE,
        parameters={'x': 100.0, 'y': 50.0}
    )
    
    # Act
    response = await translator.translate_and_execute(command)
    
    # Assert
    assert response.status == ResponseStatus.SUCCESS
    assert 'X100' in response.data['gcode']
    assert 'Y50' in response.data['gcode']
```

#### 4. Test One Thing per Test

Each test should verify a single behavior:

```python
# Good - tests one thing
def test_move_command_translates_correctly():
    command = create_move_command(x=100, y=50)
    response = await translator.translate(command)
    assert 'X100' in response.gcode
    assert 'Y50' in response.gcode

def test_move_command_validates_parameters():
    command = create_move_command(x=-9999)  # Invalid
    response = await translator.translate(command)
    assert response.status == ResponseStatus.ERROR

# Avoid - tests multiple things
def test_move_command():
    command = create_move_command()
    response = await translator.translate(command)
    assert response.status == ResponseStatus.SUCCESS  # Translation
    assert 'X100' in response.gcode  # Translation
    assert response.data['position'] == {'x': 100}  # State update
```

#### 5. Use Fixtures Effectively

```python
# Good - reusable fixture
@pytest.fixture
def sample_move_command():
    return OpenPNPCommand(
        command_type=OpenPNPCommandType.MOVE,
        parameters={'x': 100.0, 'y': 50.0}
    )

def test_translation(sample_move_command):
    response = await translator.translate(sample_move_command)
    assert response.status == ResponseStatus.SUCCESS

# Avoid - duplicated code
def test_translation():
    command = OpenPNPCommand(
        command_type=OpenPNPCommandType.MOVE,
        parameters={'x': 100.0, 'y': 50.0}
    )
    response = await translator.translate(command)
    assert response.status == ResponseStatus.SUCCESS
```

#### 6. Test Edge Cases

Don't forget to test edge cases and error conditions:

```python
def test_move_command_with_zero_coordinates():
    command = create_move_command(x=0, y=0, z=0)
    response = await translator.translate(command)
    assert response.status == ResponseStatus.SUCCESS

def test_move_command_with_negative_coordinates():
    command = create_move_command(x=-10, y=-20)
    response = await translator.translate(command)
    assert response.status == ResponseStatus.ERROR

def test_move_command_with_missing_parameters():
    command = OpenPNPCommand(
        command_type=OpenPNPCommandType.MOVE,
        parameters={}  # Missing required parameters
    )
    response = await translator.translate(command)
    assert response.status == ResponseStatus.ERROR
```

#### 7. Use Appropriate Assertions

```python
# Good - specific assertions
assert response.status == ResponseStatus.SUCCESS
assert 'X100' in response.data['gcode']
assert len(response.errors) == 0

# Avoid - vague assertions
assert response  # Always True for non-None
assert response.status  # Always True for non-zero values
```

### Test Maintenance

#### 1. Keep Tests Independent

Tests should not depend on each other:

```python
# Bad - tests depend on order
def test_first():
    global.state = 'modified'

def test_second():
    assert global.state == 'modified'  # Depends on test_first

# Good - each test is independent
def test_first():
    state = 'modified'
    assert state == 'modified'

def test_second():
    state = 'modified'
    assert state == 'modified'
```

#### 2. Clean Up Resources

Always clean up resources in tests:

```python
@pytest_asyncio.fixture
async def temp_file():
    file = create_temp_file()
    yield file
    delete_temp_file(file)  # Always clean up
```

#### 3. Update Tests When Code Changes

When modifying code, update affected tests:

1. Run tests to identify failures
2. Update tests to reflect new behavior
3. Add tests for new functionality
4. Verify all tests pass

#### 4. Document Complex Tests

Add comments for complex test logic:

```python
def test_batch_execution_with_mixed_success_and_failure():
    """
    Test batch execution where some commands succeed and others fail.
    
    This test verifies that:
    1. Successful commands execute correctly
    2. Failed commands return proper error responses
    3. Batch execution continues when stop_on_error=False
    4. All responses are returned in the correct order
    """
    commands = [
        create_move_command(),  # Success
        create_invalid_command(),  # Failure
        create_move_command(),  # Success
    ]
    
    responses = await translator.execute_batch(commands, stop_on_error=False)
    
    assert len(responses) == 3
    assert responses[0].status == ResponseStatus.SUCCESS
    assert responses[1].status == ResponseStatus.ERROR
    assert responses[2].status == ResponseStatus.SUCCESS
```

### Continuous Integration

#### 1. Run Tests on Every Commit

Configure CI to run tests automatically:

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements-dev.txt
      - run: pytest --cov=src --cov-report=xml
```

#### 2. Enforce Coverage Thresholds

Set minimum coverage requirements:

```bash
pytest --cov=src --cov-fail-under=85
```

#### 3. Run Tests in Parallel

Speed up CI by running tests in parallel:

```bash
pytest -n auto tests/
```

#### 4. Separate Unit and Integration Tests

Run unit tests first (faster), then integration tests:

```yaml
- name: Unit Tests
  run: pytest src/ -n auto

- name: Integration Tests
  run: pytest tests/integration/
```

## Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [Python unittest.mock Documentation](https://docs.python.org/3/library/unittest.mock.html)
- [Project README](../README.md)
- [API Documentation](API_Server.md)
- [Architecture Design](../plans/architecture-design.md)

## Support

For questions or issues related to testing:

1. Check this documentation first
2. Review existing test files for examples
3. Check pytest documentation
4. Open an issue on GitHub with:
   - Test output/error messages
   - Environment details (OS, Python version)
   - Steps to reproduce the issue
   - Expected vs actual behavior
