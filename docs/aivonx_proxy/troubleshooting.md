Troubleshooting

Common issues

1) "Coroutine was never awaited" during ASGI startup
- Ensure async DB calls are wrapped using `sync_to_async` when invoked from an async context. The manager implements async-safe refresh.

2) Streaming appears buffered
- Use an ASGI server (uvicorn) and ensure middleware or proxies (nginx) are not buffering responses.

3) Missing tests discovered
- Django requires test packages to be importable (package `src/proxy/tests/__init__.py`). See `src/proxy/tests/`.

4) Multi-process cache inconsistencies
- LocMemCache is process-local. Use Redis for shared state across worker processes.
