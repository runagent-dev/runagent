# Contributing to RunAgent

Thank you for your interest in contributing to RunAgent! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## How Can I Contribute?

### Reporting Bugs

- Check if the bug has already been reported in the [Issues](https://github.com/runagent-dev/runagent/issues)
- Use the bug report template when creating a new issue
- Include detailed steps to reproduce the bug
- Include system information and environment details
- Include any relevant logs or error messages

### Suggesting Enhancements

- Check if the enhancement has already been suggested
- Use the feature request template when creating a new issue
- Provide a clear description of the enhancement
- Explain why this enhancement would be useful
- Include any relevant examples or use cases

### Pull Requests

1. Fork the repository
2. Create a new branch for your feature/fix
3. Make your changes
4. Run tests and ensure they pass
5. Update documentation if needed
6. Submit a pull request

## Development Setup

### Prerequisites

- Python 3.9+ (project requires Python 3.9 or higher)
- Git
- pip
- virtualenv (recommended)

### Project Structure

```
runagent/
├── runagent/          # Main package directory
├── tests/             # Test files
├── docs/              # Documentation
├── pyproject.toml     # Project configuration and dependencies
├── README.md          # Project overview
└── CONTRIBUTING.md    # This file
```

### Setup Steps

1. Fork and clone the repository:
   
```bash
git clone https://github.com/runagent-dev/runagent.git
cd runagent
```

2. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate  # Windows
```

3. Install development dependencies:
   
```bash
# Using pip
pip install -e ".[dev]"

# Or using Hatch (recommended)
hatch env create
hatch shell
```

### Development Workflow

1. Create a new branch for your feature/fix:
```bash
git checkout -b feature/your-feature-name
```

2. Make your changes and run the development tools:

```bash
# Format code
black runagent tests

# Sort imports
isort runagent tests

# Run linter (Ruff)
ruff check runagent tests

# Run type checker
mypy runagent tests

# Run tests
pytest
```

3. Install pre-commit hooks to automatically run checks:
```bash
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=runagent

# Run specific test file
pytest tests/test_specific.py

# Run tests in parallel
pytest -n auto

# Run specific test categories
pytest -m unit      # Run unit tests
pytest -m integration  # Run integration tests
pytest -m e2e       # Run end-to-end tests
```

### Code Quality Tools

We use several tools to maintain code quality:

1. **Black** for code formatting:
```bash
black runagent tests
```

2. **isort** for import sorting:
```bash
isort runagent tests
```

3. **Ruff** for linting (replaces flake8):
```bash
ruff check runagent tests
ruff format runagent tests  # Format code
```

4. **mypy** for type checking:
```bash
mypy runagent tests
```

### Using Hatch

Hatch is our build backend and can be used for various development tasks:

```bash
# Create a new development environment
hatch env create

# Activate the environment
hatch shell

# Run tests
hatch run test

# Build the package
hatch build

# Clean build artifacts
hatch clean
```

## Documentation

### Building Documentation

```bash
cd docs
make html
```

### Documentation Guidelines

- Use clear and concise language
- Include code examples where appropriate
- Keep documentation up to date with code changes
- Follow the existing documentation style

## Pull Request Process

1. Update the README.md with details of changes if needed
2. Update the documentation if needed
3. Ensure all tests pass
4. Ensure code meets style guidelines
5. Update the CHANGELOG.md with your changes
6. The PR will be merged once you have the sign-off of at least one maintainer

## Release Process

1. Update version in `__version__.py`
2. Update CHANGELOG.md
3. Create a new release on GitHub
4. Build and publish to PyPI

## Questions?

Feel free to:
- Open an issue
- Join our [Discord community](https://discord.gg/runagent)
- Email us at support@runagent.live

Thank you for contributing to RunAgent! 🚀 