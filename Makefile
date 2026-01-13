# KlipperPlace Makefile
# Common tasks for development and testing

.PHONY: help install install-dev test lint format type-check clean build docs

help: ## Show this help message
	@echo "KlipperPlace - Available commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install the package
	pip install -e .

install-dev: ## Install the package with development dependencies
	pip install -e .[dev]

test: ## Run tests
	pytest

test-cov: ## Run tests with coverage
	pytest --cov=src --cov-report=html --cov-report=term

lint: ## Run linting
	ruff check src/ tests/

format: ## Format code with black
	black src/ tests/

format-check: ## Check code formatting
	black --check src/ tests/

type-check: ## Run type checking with mypy
	mypy src/

check-all: lint format-check type-check test ## Run all checks (lint, format, type-check, test)

clean: ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete

build: ## Build the package
	python -m build

docs: ## Generate documentation
	@echo "Documentation generation not yet implemented"

# Development helpers
dev-setup: install-dev ## Set up development environment
	@echo "Development environment setup complete!"
	@echo "Run 'make test' to verify installation."

watch: ## Watch for file changes and run tests (requires pytest-watch)
	pytest-watch

# External repository management
update-external: ## Update external repositories
	@echo "Updating external repositories..."
	cd external_repos/moonraker && git pull
	cd external_repos/klipper && git pull
	cd external_repos/openpnp-main && git pull

# Docker support (optional)
docker-build: ## Build Docker image
	docker build -t klipperplace:latest .

docker-run: ## Run Docker container
	docker run -it --rm klipperplace:latest
