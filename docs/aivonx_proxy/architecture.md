Architecture

High level
- Django + Django REST Framework provides the API and CRUD for nodes.
- `HAProxyManager` keeps runtime state in Django's cache and runs periodic
  background jobs for health checks and model discovery via `httpx`.
- Proxy handlers accept incoming requests and forward them to chosen nodes.

HAProxyManager responsibilities
- Maintain `active` and `standby` pools (cache keys `ha_active_pool`, `ha_standby_pool`).
- Track per-node active request counts (`ha_active_count:`) and recent latencies (`ha_latency:`).
- Periodically call `/api/health` on nodes and `/api/tags` for model discovery.
- Choose nodes via `choose_node(model_name, strategy)` and reserve/release via `acquire_node`/`release_node`.

Data flow for a proxy request
1. Handler validates input (rejects explicit `node_id` parameter).
2. Calls manager.choose_node(model_name) to pick a suitable address.
3. For streaming endpoints, the handler proxies the upstream async iterator into a Django `StreamingHttpResponse`.
4. On completion or error, the node's active count is decremented.

Async and DB safety
- Manager uses `asgiref.sync.sync_to_async` for ORM access in async contexts.
- Initialization runs safely in ASGI lifespan or on-demand in sync contexts.
