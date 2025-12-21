Deployment notes

- Use an ASGI server (uvicorn / gunicorn + uvicorn workers) for production, especially if you rely on streaming endpoints.

Example with `uvicorn`:

```bash
cd src
uvicorn aivonx.asgi:application --workers 2 --host 0.0.0.0 --port 8000
```

- Use a shared cache backend (Redis) for multi-process deployments. Update `CACHES` in `src/aivonx/settings.py` accordingly.
- Ensure `HAProxyManager` runs only once per process; manager state is per-process when using LocMemCache.
- Configure proper process supervision and graceful shutdown so background scheduler stops cleanly.
