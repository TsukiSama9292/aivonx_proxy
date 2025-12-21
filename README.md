# aivonx_proxy — Ollama Reverse Proxy

Lightweight reverse-proxy and HA manager for Ollama model-serving nodes.

Purpose
- Provide a unified API under `/api/proxy/` that forwards requests to one
  or more Ollama nodes, selecting the best node automatically based on
  configured HA/load-balancing strategies.
- Make endpoints model-aware (only route requests to nodes exposing the
  requested model) and support streaming responses for real-time proxies.

Core features
- CRUD management for Ollama nodes (`/api/proxy/nodes`)
- Health endpoint: `GET /api/proxy/` — returns 200 when any node is available
- Model discovery: `GET /api/proxy/tags` — aggregates models from nodes
- Proxy endpoints: `POST /api/proxy/chat`, `/generate`, `/embed`, `/embeddings`
  that forward requests to appropriate nodes and support streaming
- HA/Load strategies: `least_active` (default) and `lowest_latency`
- Periodic background tasks: health checks and model refresh (default 1m)

Quick start
1. Install dependencies:

   pip install -e .

2. Run migrations and start development server:

   cd src
   python manage.py migrate
   uvicorn aivonx.asgi:application --reload --port 8000

3. Run tests:

   cd src
   python manage.py test proxy.tests

Notes
- Streaming endpoints behave best under an ASGI server (uvicorn) to avoid
  WSGI buffering.
- The project maintains an in-memory cache for manager state. On startup the
  manager populates state from the database and schedules periodic refreshes.

See `docs/aivonx_proxy/` for architecture, API reference, testing and
deployment instructions.