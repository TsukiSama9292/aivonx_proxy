# 006 — collectstatic (when to run)

Purpose
- Explain when and why to run `collectstatic` during development or local ASGI testing.

When you run Django with the built-in development server (`python src/manage.py runserver`) and `DEBUG=True`, Django will serve static files directly from each app's `static/` directory. This behavior is convenient for fast iteration and you do not need to run `collectstatic`.

However, when running the application with an ASGI server such as `uvicorn` (for example via `python main.py`), static file serving is typically handled by a middleware (e.g., WhiteNoise) or an external web server (e.g., nginx). In those cases static files must be collected into the `STATIC_ROOT` directory before the ASGI server can serve them.

Commands

```bash
# Collect static assets from all apps into the configured STATIC_ROOT
python src/manage.py collectstatic --noinput
```

Tips
- If you use WhiteNoise, ensure `whitenoise.middleware.WhiteNoiseMiddleware` is present in `MIDDLEWARE` and consider setting `STATICFILES_STORAGE` accordingly.
- While developing with `runserver` you can skip `collectstatic`. If you switch to `uvicorn` locally to test streaming endpoints, run `collectstatic` after changing static assets.
- The project's `src/aivonx/settings.py` should set a leading-slash `STATIC_URL = '/static/'` and a filesystem `STATIC_ROOT` (for example `BASE_DIR / 'staticfiles'`).
