# Testing

Comprehensive testing guide for Aivonx Proxy.

## Running Tests

The project includes unit tests with pytest configuration located in `src/*/tests/`.

### Django Test Runner

```bash
# Run all tests
python src/manage.py test

# Run specific app
python src/manage.py test proxy

# Run with parallel execution
python src/manage.py test --parallel
```

### pytest (Alternative)

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html
```

## Test Configuration

Tests use settings from `src/aivonx/settings.py`. For CI environments, use an isolated test database and Redis instance.

### Test Settings

During testing, logging is configured to show only ERROR level and above to speed up test execution.

## Test Structure

Tests are organized by application:

```
src/
├── proxy/tests/          # Proxy tests
│   ├── conftest.py      # pytest fixtures
│   └── test_*.py        # Test modules
├── account/tests.py      # Account tests
└── logviewer/tests.py    # Logviewer tests
```

## Best Practices

- Write tests for new features
- Ensure existing tests pass before committing
- Use fixtures for common test data
- Mock external services
- Test edge cases and error conditions

## Coverage

```bash
# Generate coverage report
coverage run --source='src' src/manage.py test
coverage report
coverage html
```
