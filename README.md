# KlipperPlace

**Interface layer connecting Klipper firmware with OpenPNP pick-and-place software**

## Overview

KlipperPlace is an interface layer that bridges Klipper firmware with OpenPNP pick-and-place software. It enables precise multi-axis motion control and seamless integration between these two powerful systems.

## Project Structure

```
klipperplace/
├── src/                          # Source code
│   ├── moonraker_extensions/      # Moonraker API extensions
│   ├── klipper_modules/           # Klipper firmware modules
│   ├── middleware/                # Middleware components
│   ├── gcode_driver/              # G-code driver implementation
│   └── api/                       # API endpoints
├── config/                        # Configuration files
│   ├── examples/                  # Example configurations
│   └── schemas/                   # JSON schemas for validation
├── tests/                         # Test suite
├── docs/                          # Documentation
├── external_repos/                # External dependencies
│   ├── moonraker/                 # Moonraker repository
│   ├── klipper/                   # Klipper repository
│   └── openpnp-main/              # OpenPNP repository
├── pyproject.toml                 # Project metadata and build config
├── setup.py                       # Package installation script
├── requirements.txt               # Core dependencies
├── requirements-dev.txt           # Development dependencies
└── Makefile                       # Common tasks
```

## Installation

### Prerequisites

- Python 3.8 or higher
- Klipper firmware installed
- Moonraker installed
- OpenPNP installed

### Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/KlipperPlace.git
cd KlipperPlace
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. For development, install development dependencies:
```bash
pip install -r requirements-dev.txt
```

4. Install the package in editable mode:
```bash
pip install -e .
```

## Configuration

See [`config/examples/`](config/examples/) for example configuration files.

## Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black src/ tests/
```

### Linting

```bash
ruff check src/ tests/
```

### Type Checking

```bash
mypy src/
```

## Architecture

For detailed architecture information, see [`plans/architecture-design.md`](plans/architecture-design.md).

## License

KlipperPlace is licensed under the GNU General Public License v3.0 or later. See the [`COPYING`](COPYING) file for details.

## Acknowledgements

KlipperPlace builds upon:
- [Klipper](https://www.klipper3d.org/) - 3D printer firmware
- [Moonraker](https://github.com/Arksine/moonraker) - Klipper API server
- [OpenPNP](https://openpnp.org/) - Open source pick-and-place software

## Contributing

Contributions are welcome! Please read our contributing guidelines and submit pull requests to our repository.

## Support

For issues, questions, or contributions, please visit our GitHub repository.
