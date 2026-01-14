# Contributing to KlipperPlace

Thank you for your interest in contributing to KlipperPlace! We welcome contributions from the community and appreciate your help in making this project better.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing Requirements](#testing-requirements)
- [Documentation Requirements](#documentation-requirements)
- [Commit Message Guidelines](#commit-message-guidelines)
- [Issue Reporting](#issue-reporting)
- [Feature Requests](#feature-requests)
- [Development Tools](#development-tools)
- [Project Structure](#project-structure)
- [Common Tasks](#common-tasks)

---

## Code of Conduct

### Our Pledge

We are committed to making participation in our project a harassment-free experience for everyone, regardless of level of experience, gender, gender identity and expression, sexual orientation, disability, personal appearance, body size, race, ethnicity, age, religion, or nationality.

### Our Standards

Examples of behavior that contributes to a positive environment:

- Using welcoming and inclusive language
- Being respectful of differing viewpoints and experiences
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

Examples of unacceptable behavior:

- The use of sexualized language or imagery
- Personal attacks or political commentary
- Public or private harassment
- Publishing others' private information without explicit permission
- Other unethical or unprofessional conduct

### Our Responsibilities

Project maintainers are responsible for clarifying the standards of acceptable behavior and are expected to take appropriate and fair corrective action in response to any instances of unacceptable behavior.

### Scope

This Code of Conduct applies both within project spaces and in public spaces when an individual is representing the project or its community.

### Enforcement

Instances of abusive, harassing, or otherwise unacceptable behavior may be reported by contacting the project team through our GitHub issue tracker. All complaints will be reviewed and investigated and will result in a response that is deemed necessary and appropriate to the circumstances.

---

## Getting Started

### Prerequisites

Before contributing, ensure you have:

- Python 3.8 or higher
- Git installed and configured
- A GitHub account
- Familiarity with Python and async/await patterns
- Basic understanding of REST APIs and WebSockets

### Setting Up Development Environment

1. **Fork the Repository**

   ```bash
   # Fork the repository on GitHub
   # Then clone your fork
   git clone https://github.com/YOUR_USERNAME/KlipperPlace.git
   cd KlipperPlace
   ```

2. **Add Upstream Remote**

   ```bash
   git remote add upstream https://github.com/klipperplace/KlipperPlace.git
   ```

3. **Create Virtual Environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. **Install Development Dependencies**

   ```bash
   pip install -e ".[dev]"
   ```

5. **Verify Installation**

   ```bash
   # Run tests to verify setup
   pytest

   # Check code formatting
   black --check src/ tests/
   ```

### Development Workflow

1. **Keep Your Fork Updated**

   ```bash
   git fetch upstream
   git checkout main
   git merge upstream/main
   ```

2. **Create a Feature Branch**

   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

3. **Make Your Changes**

   - Write code following our [Coding Standards](#coding-standards)
   - Add tests for your changes
   - Update documentation as needed
   - Ensure all tests pass

4. **Commit Your Changes**

   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

5. **Push to Your Fork**

   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create Pull Request**

   - Go to the KlipperPlace repository on GitHub
   - Click "New Pull Request"
   - Select your feature branch
   - Fill out the pull request template
   - Submit your pull request

---

## Pull Request Process

### Before Submitting

1. **Check Existing Issues**

   - Search for existing issues or pull requests that address your change
   - Comment on existing issues if your PR is related

2. **Write Tests**

   - Add unit tests for new functionality
   - Add integration tests if appropriate
   - Ensure all existing tests pass

3. **Update Documentation**

   - Update relevant documentation files
   - Add docstrings to new functions and classes
   - Update API reference if adding new endpoints

4. **Run Quality Checks**

   ```bash
   # Format code
   black src/ tests/

   # Lint code
   ruff check src/ tests/

   # Type check
   mypy src/

   # Run tests
   pytest --cov=src --cov-report=html
   ```

### Pull Request Template

When creating a pull request, please include:

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] All tests pass

## Documentation
- [ ] Code documentation updated
- [ ] API documentation updated
- [ ] User documentation updated

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] No new warnings generated
- [ ] Tests added/updated
- [ ] All tests passing
```

### Pull Request Review Process

1. **Automated Checks**

   - All tests must pass
   - Code coverage must not decrease
   - Code formatting must pass
   - Linting must pass
   - Type checking must pass

2. **Manual Review**

   - At least one maintainer must review the PR
   - Address all review comments
   - Make requested changes

3. **Approval and Merge**

   - PR must be approved by at least one maintainer
   - All CI checks must pass
   - PR will be merged by maintainers

---

## Coding Standards

### Python Style Guide

We follow PEP 8 style guidelines with some modifications:

#### Formatting

- Use **Black** for code formatting
- Maximum line length: 100 characters
- Use 4 spaces for indentation
- Use double quotes for strings

```python
# Good
def my_function(param1: str, param2: int) -> bool:
    """This is a function."""
    return True

# Bad
def my_function(param1,param2):
    return True
```

#### Type Hints

- Use type hints for all function signatures
- Use type hints for class attributes when appropriate
- Import types from `typing` module

```python
from typing import Optional, List, Dict

def process_data(
    data: List[Dict[str, any]],
    config: Optional[Dict[str, any]] = None
) -> bool:
    """Process data with optional configuration."""
    return True
```

#### Docstrings

- Use Google-style docstrings
- Include description, parameters, returns, and raises sections
- Document all public functions and classes

```python
def calculate_position(
    x: float,
    y: float,
    z: float,
    feedrate: float = 3000.0
) -> Dict[str, float]:
    """Calculate the position for a move command.

    Args:
        x: X coordinate in millimeters
        y: Y coordinate in millimeters
        z: Z coordinate in millimeters
        feedrate: Feedrate in mm/min (default: 3000.0)

    Returns:
        Dictionary containing position and feedrate

    Raises:
        ValueError: If coordinates are out of bounds
    """
    return {"x": x, "y": y, "z": z, "feedrate": feedrate}
```

#### Naming Conventions

- **Functions/Methods**: `snake_case`
- **Variables**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`
- **Classes**: `PascalCase`
- **Private members**: `_leading_underscore`

```python
# Good
class ApiServer:
    def __init__(self):
        self._client = None
        self.MAX_CONNECTIONS = 100

    def handle_request(self, request: Request) -> Response:
        pass

# Bad
class apiServer:
    def __init__(self):
        self.Client = None
```

#### Async/Await

- Use `async` and `await` for I/O operations
- Use `aiohttp` for HTTP requests
- Use `asyncio` for concurrent operations

```python
import aiohttp
import asyncio

async def fetch_data(url: str) -> Dict[str, any]:
    """Fetch data from a URL asynchronously."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

async def main():
    """Main async function."""
    data = await fetch_data("https://api.example.com/data")
    print(data)

if __name__ == "__main__":
    asyncio.run(main())
```

#### Error Handling

- Use specific exception types
- Provide meaningful error messages
- Log errors appropriately
- Clean up resources in finally blocks

```python
import logging

logger = logging.getLogger(__name__)

async def process_command(command: str) -> Dict[str, any]:
    """Process a command with proper error handling."""
    try:
        result = await execute_command(command)
        return result
    except ValueError as e:
        logger.error(f"Invalid command: {e}")
        raise
    except ConnectionError as e:
        logger.error(f"Connection failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise
```

#### Imports

- Group imports in this order: standard library, third-party, local
- Use absolute imports for local modules
- Remove unused imports

```python
# Standard library
import asyncio
import logging
from typing import Dict, List, Optional

# Third-party
import aiohttp
from pydantic import BaseModel

# Local
from klipperplace.api.server import ApiServer
from klipperplace.middleware.cache import CacheManager
```

#### Logging

- Use the `logging` module
- Use appropriate log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Include context in log messages

```python
import logging

logger = logging.getLogger(__name__)

class ApiHandler:
    def __init__(self):
        logger.info("Initializing API handler")

    async def handle_request(self, request: Request) -> Response:
        """Handle incoming request."""
        logger.debug(f"Processing request: {request.method} {request.path}")
        try:
            result = await self._process(request)
            logger.info(f"Request processed successfully")
            return result
        except Exception as e:
            logger.error(f"Request failed: {e}", exc_info=True)
            raise
```

---

## Testing Requirements

### Unit Tests

- Write unit tests for all new functions and classes
- Use `pytest` as the test framework
- Use `unittest.mock` for mocking external dependencies
- Aim for 90%+ code coverage for new code

```python
import pytest
from unittest.mock import AsyncMock, patch
from klipperplace.api.server import ApiServer

@pytest.mark.asyncio
async def test_handle_request_success():
    """Test successful request handling."""
    server = ApiServer()
    request = AsyncMock()
    request.method = "GET"
    request.path = "/api/v1/status"
    
    response = await server.handle_request(request)
    
    assert response.status == 200
    assert "status" in response.json()
```

### Integration Tests

- Write integration tests for component interactions
- Test the full request/response cycle
- Use test fixtures for common setup

```python
import pytest
from tests.integration.conftest import api_client, moonraker_client

@pytest.mark.asyncio
async def test_api_to_middleware_integration(api_client, moonraker_client):
    """Test API to middleware integration."""
    response = await api_client.get("/api/v1/status")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
```

### Test Organization

- Place unit tests alongside source code: `src/module/test_module.py`
- Place integration tests in: `tests/integration/`
- Use descriptive test names
- Group related tests with `@pytest.mark`

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/integration/test_api_to_middleware.py

# Run specific test
pytest tests/integration/test_api_to_middleware.py::test_api_to_middleware_integration

# Run with verbose output
pytest -v

# Run only failed tests
pytest --lf
```

### Test Coverage

- Aim for 85%+ overall coverage
- Aim for 90%+ coverage for critical components
- Review coverage reports before submitting PR

---

## Documentation Requirements

### Code Documentation

- Add docstrings to all public functions and classes
- Use Google-style docstrings
- Include type hints in function signatures
- Document complex algorithms

### API Documentation

- Update [API Reference](docs/API_REFERENCE.md) for new endpoints
- Include request/response examples
- Document error codes
- Provide cURL, Python, JavaScript, and C# examples

### User Documentation

- Update [Configuration Guide](docs/CONFIGURATION.md) for new configuration options
- Update [Setup Instructions](docs/SETUP.md) for setup changes
- Update [Testing Guide](docs/TESTING.md) for testing procedures
- Update [Hardware Testing Guide](docs/HARDWARE_TESTING.md) for hardware changes

### Documentation Style

- Use clear, concise language
- Include code examples
- Use consistent formatting
- Add diagrams for complex concepts
- Keep documentation up to date with code changes

---

## Commit Message Guidelines

### Format

Follow the Conventional Commits specification:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks
- `perf`: Performance improvements

### Examples

```bash
# Feature
git commit -m "feat(api): add batch command execution endpoint"

# Bug fix
git commit -m "fix(cache): resolve cache invalidation race condition"

# Documentation
git commit -m "docs(api): update WebSocket documentation with new events"

# Refactoring
git commit -m "refactor(middleware): simplify translation logic"

# Tests
git commit -m "test(api): add integration tests for queue management"
```

### Subject Line

- Use present tense ("add" not "added")
- Use imperative mood ("move" not "moves")
- Don't capitalize first letter
- Don't end with a period
- Limit to 72 characters

### Body

- Explain what and why, not how
- Wrap at 72 characters
- Reference issue numbers

```bash
git commit -m "feat(api): add batch command execution endpoint

This allows users to execute multiple commands in a single HTTP request,
reducing network overhead and improving performance for complex operations.

Closes #123"
```

---

## Issue Reporting

### Before Reporting

1. **Search Existing Issues**

   - Check if the issue has already been reported
   - Add to existing issues if appropriate

2. **Check Documentation**

   - Review relevant documentation
   - Check for common solutions

### Bug Report Template

```markdown
## Description
Clear and concise description of the bug

## Steps to Reproduce
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

## Expected Behavior
What you expected to happen

## Actual Behavior
What actually happened

## Environment
- KlipperPlace version:
- Klipper version:
- Moonraker version:
- OpenPNP version:
- Operating system:
- Python version:

## Logs
Relevant log output

## Additional Context
Any other relevant information
```

### Feature Request Template

```markdown
## Description
Clear and concise description of the feature

## Problem Statement
What problem does this feature solve?

## Proposed Solution
How would you like this feature to work?

## Alternatives
What alternatives have you considered?

## Additional Context
Any other relevant information
```

---

## Feature Requests

We welcome feature requests! Please:

1. **Check Existing Requests**

   - Search for existing feature requests
   - Add comments to existing requests

2. **Provide Context**

   - Explain the problem you're trying to solve
   - Describe the proposed solution
   - Consider alternative approaches

3. **Be Specific**

   - Provide detailed requirements
   - Include use cases
   - Consider edge cases

---

## Development Tools

### Code Formatting

```bash
# Format code
black src/ tests/

# Check formatting without making changes
black --check src/ tests/

# Format specific file
black src/api/server.py
```

### Linting

```bash
# Lint code
ruff check src/ tests/

# Fix linting issues
ruff check --fix src/ tests/

# Lint specific file
ruff check src/api/server.py
```

### Type Checking

```bash
# Type check
mypy src/

# Type check specific file
mypy src/api/server.py

# Generate type stubs
mypy --stub-packages src/
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test
pytest tests/integration/test_api_to_middleware.py::test_api_to_middleware_integration

# Run with verbose output
pytest -v

# Run only failed tests
pytest --lf

# Run until first failure
pytest -x
```

### Makefile Commands

```bash
# Install dependencies
make install

# Install development dependencies
make install-dev

# Run tests
make test

# Run tests with coverage
make test-coverage

# Format code
make format

# Lint code
make lint

# Type check
make type-check

# Run all quality checks
make check

# Clean build artifacts
make clean
```

---

## Project Structure

Understanding the project structure will help you navigate and contribute effectively:

```
klipperplace/
├── src/                          # Source code
│   ├── moonraker_extensions/      # Moonraker API extensions
│   ├── middleware/                # Middleware components
│   ├── gcode_driver/              # G-code driver implementation
│   ├── api/                       # API endpoints
│   │   ├── routes/                # REST endpoints
│   └── tests/                     # Test suite
├── config/                        # Configuration files
├── docs/                          # Documentation
├── external_repos/                # External dependencies
└── tests/                         # Integration tests
```

### Component Responsibilities

- **Moonraker Extensions**: Hardware control (GPIO, fans, PWM, sensors)
- **Middleware**: Translation, caching, safety
- **G-code Driver**: G-code parsing, translation, execution
- **API**: REST endpoints, WebSocket, authentication

---

## Common Tasks

### Adding a New API Endpoint

1. Create route file in `src/api/routes/`
2. Implement endpoint handler
3. Add tests in `src/api/test_routes.py`
4. Update API documentation
5. Update API schema

### Adding a New Moonraker Extension

1. Create extension file in `src/moonraker_extensions/`
2. Implement extension class
3. Add tests
4. Update documentation
5. Add configuration options

### Adding a New Sensor Type

1. Update sensor query extension
2. Add sensor type to supported list
3. Add tests
4. Update documentation

### Adding a New Configuration Option

1. Update configuration schema
2. Add validation
3. Update documentation
4. Add example configuration

---

## Getting Help

If you need help with contributing:

- **GitHub Discussions**: https://github.com/klipperplace/KlipperPlace/discussions
- **GitHub Issues**: https://github.com/klipperplace/KlipperPlace/issues
- **Documentation**: [docs/](docs/)

---

## Recognition

Contributors will be recognized in:

- Project README
- Release notes
- Contributors list

Thank you for contributing to KlipperPlace!

---

**Last Updated**: 2024-01-14
