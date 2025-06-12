# Development Guide

This guide covers development practices, tools, and workflows used in the RunAgent project.

## Development Tools

### Code Quality Tools

- **Black**: Code formatting
- **Ruff**: Code linting and import sorting
- **mypy**: Type checking
- **bandit**: Security linting

### Testing Tools

- **pytest**: Main testing framework
- **pytest-cov**: Coverage reporting
- **pytest-mock**: Mocking utilities
- **pytest-asyncio**: Async testing support
- **pytest-xdist**: Parallel test execution
- **pytest-benchmark**: Performance benchmarking
- **pytest-env**: Environment variable management
- **pytest-sugar**: Enhanced test output formatting

## Tool Configuration

### Black

```toml
[tool.black]
line-length = 88
target-version = ["py39"]
include = '\.pyi?$'
extend-exclude = '''
^/docs
'''
```

### Ruff

```toml
[tool.ruff]
line-length = 88
target-version = "py39"
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "C",   # flake8-comprehensions
    "B",   # flake8-bugbear
    "N",   # pep8-naming
    "UP",  # pyupgrade
    "ANN", # flake8-annotations
    "S",   # flake8-bandit
    "BLE", # flake8-blind-except
    "FBT", # flake8-boolean-trap
    "COM", # flake8-commas
    "DTZ", # flake8-datetimez
    "T20", # flake8-print
    "PT",  # flake8-pytest-style
    "RSE", # flake8-raise
    "RET", # flake8-return
    "SLF", # flake8-self
    "SIM", # flake8-simplify
    "TID", # flake8-tidy-imports
    "ARG", # flake8-unused-arguments
    "PIE", # flake8-pie
    "ERA", # eradicate
    "PD",  # pandas-vet
    "PGH", # pygrep-hooks
    "PL",  # pylint
    "TRY", # tryceratops
    "RUF", # Ruff-specific rules
]
```

### mypy

```toml
[tool.mypy]
python_version = "3.9"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
plugins = ["pydantic.mypy"]
```

### pytest

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-v --cov=runagent --cov-report=term-missing --cov-report=html"
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "e2e: End-to-end tests",
    "slow: Tests that take longer to run",
]
filterwarnings = [
    "ignore::DeprecationWarning",
    "ignore::UserWarning",
]
```

### Coverage

```toml
[tool.coverage.run]
branch = true
source = ["runagent"]
omit = [
    "tests/*",
    "setup.py",
    "docs/*",
    "**/__init__.py",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "pass",
    "raise ImportError",
    "except ImportError:",
    "def main",
    "if TYPE_CHECKING:",
]
show_missing = true
fail_under = 80
```

## Running Development Tools

### Code Quality Checks

```bash
# Format code with Black
black runagent tests

# Run Ruff linter
ruff check runagent tests

# Run Ruff formatter
ruff format runagent tests

# Run mypy type checking
mypy runagent tests

# Run security checks with bandit
bandit -r runagent
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=runagent

# Run specific test file
pytest tests/unit/test_client.py

# Run tests matching pattern
pytest -k "test_deploy"

# Run tests in parallel
pytest -n auto

# Run tests with detailed output
pytest -v

# Run tests with live log output
pytest --log-cli-level=INFO

# Run tests and generate HTML coverage report
pytest --cov=runagent --cov-report=html

# Run performance benchmarks
pytest --benchmark-only

# Run tests with environment variables
pytest --env-file=.env.test

# Run specific test categories
pytest -m unit      # Run unit tests
pytest -m integration  # Run integration tests
pytest -m e2e       # Run end-to-end tests
pytest -m slow      # Run slow tests
```

## Test Structure

```
tests/
├── conftest.py           # Shared fixtures
├── unit/                 # Unit tests
│   ├── test_client.py
│   ├── test_config.py
│   └── test_utils.py
├── integration/          # Integration tests
│   ├── test_deployment.py
│   └── test_agent.py
└── e2e/                  # End-to-end tests
    └── test_cli.py
```

## Writing Tests

### Basic Test Example

```python
def test_config_creation():
    """Test configuration creation."""
    config = Config.create_config(
        project_dir="test_project",
        config_content={"key": "value"}
    )
    assert Path(config).exists()
    assert Config.get_config("test_project")["key"] == "value"
```

### Using Fixtures

```python
@pytest.fixture
def mock_client():
    """Create a mock client for testing."""
    with patch("runagent.client.RunAgentClient") as mock:
        yield mock

def test_deploy_agent(mock_client):
    """Test agent deployment."""
    mock_client.deploy.return_value = {"deployment_id": "test-123"}
    result = mock_client.deploy("./test_agent")
    assert result["deployment_id"] == "test-123"
```

### Async Tests

```python
@pytest.mark.asyncio
async def test_async_operation():
    """Test async operations."""
    result = await async_function()
    assert result is not None
```

### Performance Tests

```python
def test_performance(benchmark):
    """Test performance of a function."""
    result = benchmark(lambda: expensive_operation())
    assert result is not None
```

### Environment Variable Tests

```python
def test_with_env(monkeypatch):
    """Test with environment variables."""
    monkeypatch.setenv("TEST_VAR", "test_value")
    result = function_using_env()
    assert result == "test_value"
```

## Best Practices

### Code Style

1. **Formatting**
   - Use Black for consistent formatting
   - Follow PEP 8 guidelines
   - Keep lines under 88 characters

2. **Imports**
   - Let Ruff handle import sorting
   - Group imports: standard library, third-party, local
   - Use absolute imports

3. **Type Hints**
   - Use type hints for all function parameters
   - Use type hints for return values
   - Use Optional for nullable values
   - Use Union for multiple types

4. **Documentation**
   - Use docstrings for all modules, classes, and functions
   - Follow Google style docstrings
   - Include type information in docstrings

### Testing

1. **Test Organization**
   - Group tests by functionality
   - Use descriptive test names
   - Keep tests focused and atomic
   - Use appropriate test markers (unit, integration, e2e, slow)

2. **Fixtures**
   - Use fixtures for common setup
   - Keep fixtures in `conftest.py`
   - Use appropriate fixture scope

3. **Assertions**
   - Use specific assertions
   - Test edge cases
   - Include error cases

4. **Mocking**
   - Mock external dependencies
   - Use appropriate mock levels
   - Verify mock interactions

5. **Coverage**
   - Maintain at least 80% code coverage
   - Focus on critical paths
   - Don't sacrifice quality for coverage
   - Use appropriate coverage exclusions

6. **Performance**
   - Use benchmarks for performance-critical code
   - Compare against baseline
   - Document performance requirements

7. **Environment**
   - Use pytest-env for environment variables
   - Keep test environment isolated
   - Document required variables

## Common Issues

### Code Quality

1. **Black**
   - Line Length: Black uses 88 characters by default
   - String Quotes: Black uses double quotes by default

2. **Ruff**
   - Import Groups: Standard library, third-party, local
   - Common Errors: E501, F401, F403, ANN

3. **mypy**
   - Type Checking: Use proper type hints
   - Optional Types: Handle nullable values
   - Union Types: Use for multiple types
   - TypeVar: Use for generic types

### Testing

1. **Test Isolation**
   - Ensure tests don't depend on each other
   - Clean up resources after tests
   - Use appropriate fixtures

2. **Async Testing**
   - Use `pytest.mark.asyncio`
   - Handle async fixtures properly
   - Clean up async resources

3. **Mocking**
   - Mock at the right level
   - Reset mocks between tests
   - Verify mock calls

4. **Performance**
   - Account for system load
   - Use appropriate benchmark settings
   - Document performance requirements

5. **Environment**
   - Handle missing environment variables
   - Use appropriate test environment
   - Document environment requirements

## Continuous Integration

Development tools are automatically run on:
- Every pull request
- Every push to main
- Nightly builds

## Resources

### Code Quality
- [Black Documentation](https://black.readthedocs.io/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [mypy Documentation](https://mypy.readthedocs.io/)
- [bandit Documentation](https://bandit.readthedocs.io/)

### Testing
- [pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [pytest-mock Documentation](https://pytest-mock.readthedocs.io/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [pytest-benchmark Documentation](https://pytest-benchmark.readthedocs.io/)
- [pytest-env Documentation](https://pytest-env.readthedocs.io/)
- [pytest-sugar Documentation](https://pytest-sugar.readthedocs.io/) 