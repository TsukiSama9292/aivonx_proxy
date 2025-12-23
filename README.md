## aivonx_proxy — Ollama Reverse Proxy

Lightweight reverse-proxy and HA manager for Ollama model-serving nodes.

<p align="center">
  <img
    src="./asstes/images/AIVONX_PROXY.png"
    alt="AIVONX Proxy"
    width="200"
    height="200"
  />
</p>

<p align="center">
  <a href="https://github.com/TsukiSama9292/aivonx_proxy/commits/main">
    <img src="https://img.shields.io/github/last-commit/TsukiSama9292/aivonx_proxy" alt="Last Commit">
  </a>
  <a href="https://github.com/TsukiSama9292/aivonx_proxy/actions/workflows/tests.yml">
    <img src="https://github.com/TsukiSama9292/aivonx_proxy/actions/workflows/tests.yml/badge.svg" alt="CI Status">
  </a>
</p>

## Purpose

- Provide a unified API under `/api/proxy` that forwards requests to one or
  more Ollama nodes, selecting the best node automatically based on configured
  HA/load-balancing strategies.
- Make endpoints model-aware (only route requests to nodes exposing the
  requested model) and support streaming responses for real-time proxies.

## Core features
- Support Ollama API: add url `https://your-domain` for your tools
- Ollama reverse proxy: configure your tools to use the proxy as the Ollama
  API endpoint (for example `http://localhost:8000`).
- CRUD management for Ollama nodes (`/api/proxy/nodes`)
- Health endpoint: `GET /api/proxy` — returns 200 when any node is available
- Model discovery: `GET /api/tags` — lists models available on nodes
- Proxy endpoints: `POST /api/proxy/chat`, `/generate`, `/embed`, `/embeddings`
  that forward requests to appropriate nodes and support streaming
- HA/Load strategies: `least_active` (default, load-balancing) and `lowest_latency`
  - Periodic background tasks: health checks and model refresh (default: 1 minute)

## Quick Start

This project now prioritizes the Web UI as the primary user interface for managing nodes, models and proxy configuration. The Web UI provides full CRUD for the proxy APIs and is the recommended entry point for most users.

### 1. Using the Web UI (recommended)

1. Start the app with Docker Compose:

```bash
docker compose up -d
```

2. Open your browser at http://localhost:8000 — the management UI provides pages to create, update, list, and delete Ollama nodes, proxy settings, and more.

3. Default administrative credentials:

- Username: `root`
- Password: `changeme`

To change the default `root` password, set `ROOT_PASSWORD` in the repository `.env` file at the project root (one level above `src`), for example:

```env
ROOT_PASSWORD=your_secure_password_here
```

### 2. Docker / CLI (advanced)

If you prefer running the app outside Docker or need to run management tasks, use the included `uv` CLI. The CLI is useful for development, running migrations, or launching with hot-reload.

Install runtime helpers:

```bash
uv sync
```

Run database migrations:

```bash
cd src
uv run manage.py migrate
```

Development (ASGI — recommended for streaming endpoints):

```bash
# from repository root
uv run main.py --reload --port 8000
```

Static assets note (development)
--------------------------------

If you run the app locally with an ASGI server (for example via `uv run main.py` or `python main.py`) and you are using WhiteNoise or another static middleware, static files will be served from `STATIC_ROOT`. You need to collect static assets after making changes so the ASGI server can serve the updated files:

```bash
python src/manage.py collectstatic --noinput
```

If you are using Django's `runserver` during development (`python src/manage.py runserver`) and `DEBUG=True`, `collectstatic` is not required because `runserver` serves app `static/` directories directly.

Run tests:

```bash
cd src
uv run manage.py test proxy.tests
```

## Configuration Parameters

This section documents common environment variables and parameters you may set when running the app (Docker, `.env`, or host environment). Defaults shown are what the repository uses for development; adjust for production.

- `PORT` — Host port mapping for Docker Compose. Default: `8000`. (Docker Compose `ports: "${PORT:-8000}:${PORT:-8000}"`.)
- `DJANGO_PORT` — Application port used by some scripts; default `8000` when present in `.env`.
- `DJANGO_DEBUG` — Enable Django debug mode. Values: `True`/`False` (case-insensitive). Default: `True` in development.
- `DJANGO_SECRET_KEY` — Django secret key. In production **must** be set in environment; if not set while `DEBUG=False` the app will raise an error. A development default exists in `src/aivonx/settings.py` (replace it for production).
- `ROOT_PASSWORD` — Initial admin password for the Web UI (development convenience). Set this in the repository `.env` (one level above `src`) to override the default `changeme`.
- `DJANGO_ALLOWED_HOSTS` — Comma-separated list of allowed hosts. Use with `DJANGO_ALLOWED_HOSTS=host1,host2`.
- `DJANGO_CORS_ALLOWED_ORIGINS` / `DJANGO_CSRF_TRUSTED_ORIGINS` — Comma-separated origins; scheme is normalized by the app.

## Notes

- Streaming endpoints behave best under an ASGI server (uvicorn) to avoid WSGI
  buffering issues.
- The HA manager stores runtime state in Django cache. On startup the manager
  populates state from the database and schedules periodic refreshes (default
  every minute).

## Docs

See [Documents](./docs/aivonx_proxy/README.md) for architecture, API reference, testing and
deployment instructions.