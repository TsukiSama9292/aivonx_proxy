# Static files during development

If you run the application with an ASGI server such as `uvicorn` (for example via `python main.py`), static files are commonly served from the `STATIC_ROOT` directory. When using WhiteNoise or another static file middleware, you must run Django's `collectstatic` to copy app `static/` assets into `STATIC_ROOT` so the ASGI server can serve them.

To update CSS/JS/images when running with `uvicorn` or another ASGI server, run:

```bash
python src/manage.py collectstatic --noinput
```

Note: Django's `runserver` (development server) serves app `static/` directories directly when `DEBUG=True`, so `collectstatic` is not required for `runserver`-based development. However, if you prefer to run the ASGI server locally to test streaming or ASGI-specific behavior, remember to run `collectstatic` after changing static assets.

Related: see `STATIC_URL` and `STATIC_ROOT` in `src/aivonx/settings.py` and consider using WhiteNoise for ASGI static serving.
