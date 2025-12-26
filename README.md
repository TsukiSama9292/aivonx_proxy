## aivonx_proxy — Ollama Reverse Proxy

Lightweight reverse proxy and HA manager for Ollama model-serving nodes. The project provides a unified API gateway, node management, model discovery, and streaming proxy support.

**Key features**
- Node management: create, update and remove Ollama nodes and manage active/standby pools.
- Proxy API: route requests under `/api/proxy` to nodes that expose the requested model, with streaming support.
- Model discovery: list models available on nodes (`GET /api/tags`).
- HA / load strategies: `least_active` (default) and `lowest_latency`.
- Health check: `GET /api/proxy` (returns healthy when any node is available).

## Quick Start

Run commands from the project root (this repo includes `docker-compose.yml` for an all-in-one environment). Docker Compose is the recommended quick-start method.

1. Start services using Docker Compose:

```bash
docker compose up -d
```

2. Open the web UI and API docs in your browser:

- Web UI: http://localhost:8000
- Interactive API docs: http://localhost:8000/swagger or http://localhost:8000/redoc

3. Default administrative credentials (change immediately in production):

- Username: `root`
- Password: `changeme`

To override the initial `root` password during deployment, set `ROOT_PASSWORD` in a `.env` file placed at the project root (same level as `src/`):

```env
ROOT_PASSWORD=your_secure_password_here
```

### Using `uv` to run Python tasks (required)

This project uses the `uv` helper for consistent runtime and environment management. Use `uv run` for Python entrypoints:

```bash
# Install / sync the development environment
uv sync

# Run database migrations
uv run src/manage.py migrate

# Collect static files after changing static assets
uv run src/manage.py collectstatic --noinput

# Run tests
uv run src/manage.py test proxy.tests

# Development (ASGI, recommended for streaming endpoints)
uv run main.py --reload --port 8000
```

Note: streaming endpoints work best under an ASGI server (for example `uvicorn`) to avoid WSGI buffering issues.

## Deployment and environment variables

Supported deployment options:
- Docker Compose (development / simple deployment)
- Kubernetes (production, use managed DB and Redis)
- ASGI (recommended for streaming) or WSGI (synchronous workloads)

Important environment variables (see `src/aivonx/settings.py` for full list):

- `DJANGO_SECRET_KEY` — required in production
- `DJANGO_DEBUG` — set to `False` in production
- `DJANGO_ALLOWED_HOSTS` — comma-separated allowed hosts
- `ROOT_PASSWORD` — default admin password
- Database: `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`
- Cache: `REDIS_URL`

Production checklist (summary):
- Set a strong `DJANGO_SECRET_KEY`
- Disable debug (`DJANGO_DEBUG=false`)
- Configure `ALLOWED_HOSTS`
- Use production-grade PostgreSQL and Redis
- Configure SSL/TLS, logging and backups
- Change the default `root` password

## API and core endpoints (summary)

After starting the app, interactive API docs are available at `/swagger` and `/redoc`. Common endpoints include:

- Health: `GET /api/health`
- List models: `GET /api/tags`
- Proxy generate: `POST /api/generate`, `POST /api/chat`
- Embeddings: `POST /api/embed`, `POST /api/embeddings`
- Proxy state: `GET /api/proxy/state`
- Node management: `/api/proxy/nodes` (CRUD)

See the API docs for full details and request/response schemas.

## For developers

- Source code root: `src/`
- Proxy implementation: `src/proxy/`
- Settings: `src/aivonx/settings.py`

Recommended development workflow:

```bash
# Sync environment
uv sync

# Apply migrations
uv run src/manage.py migrate

# Run tests
uv run src/manage.py test
```

Refer to the project's Contributing guide in `docs/` for contribution steps, code style and PR guidelines.