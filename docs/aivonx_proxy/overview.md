Project overview

This repository provides a reverse proxy and high-availability manager for Ollama model-serving nodes. It exposes a small set of proxy endpoints under `/api/proxy/` and a CRUD API to manage Ollama nodes.

Goals
- Route requests to nodes that actually serve the requested model.
- Automatically pick healthy nodes using configurable strategies.
- Provide real-time streaming where supported by upstream Ollama nodes.
- Make the proxy easy to test and operate via Django's management commands.

Key concepts
- Node: a configured Ollama server (address + port) persisted in DB.
- Active / Standby pools: manager maintains which nodes are healthy (active) and which are temporarily standby.
- Model discovery: nodes expose `/api/tags`; manager periodically refreshes and caches models.
- Strategies: `least_active` (default) and `lowest_latency`.

Files of interest
- `src/proxy/utils/proxy_manager.py` — HAProxyManager implementation
- `src/proxy/handlers.py` — HTTP handlers for proxy endpoints
- `src/proxy/streaming.py` — streaming helpers
- `src/proxy/viewsets.py`, `src/proxy/serializers.py`, `src/proxy/models.py` — node CRUD
- `src/aivonx/asgi.py` — ASGI startup integration for manager

Operational note
- For unbuffered streaming, run with an ASGI server (uvicorn) and not via WSGI.
