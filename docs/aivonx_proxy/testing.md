Testing

Run tests

```bash
cd src
python manage.py test proxy.tests
```

Test structure
- `conftest.py` contains base test classes and helpers.
- Use `TestCase` for most unit tests, `TransactionTestCase` when DB transaction behavior is needed.

Mocking external HTTP
- Use `unittest.mock.patch` to mock `httpx.AsyncClient` in manager/handler tests so tests do not call the network.

CI
- Run `python manage.py test proxy.tests` as part of CI. Use `--keepdb` to speed up repeated runs.
