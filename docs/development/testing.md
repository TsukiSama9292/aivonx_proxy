# Testing

Comprehensive testing guide for Aivonx Proxy.

## Running Tests

The project includes unit tests with pytest configuration located in `src/*/tests/`.

### Django Test Runner

```bash
# Run all tests
python src/manage.py test proxy.tests account.tests logviewer.tests --verbosity 1 --keepdb
```