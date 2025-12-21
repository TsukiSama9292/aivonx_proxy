CLI launcher (`main.py`)

Usage

```bash
# Default: read .env / environment; if DJANGO_DEBUG=true enables --reload
python main.py --port 8000

# Pass extra uvicorn args
python main.py --args "--workers 2 --log-level debug"

# Force reload
python main.py --reload

# Disable reload even if DJANGO_DEBUG is set
python main.py --no-reload
```

Precedence
- CLI options have highest priority.
- Then environment variables (from system env or `.env` file loaded by python-dotenv).
- Then defaults: `port=8000`, `host=0.0.0.0`, `reload=False`.

Notes
- The script runs `uvicorn aivonx.asgi:application` with `cwd=src` so the package `aivonx` is importable.
- For production, prefer running a process manager (systemd, supervisor) or container entrypoint.
