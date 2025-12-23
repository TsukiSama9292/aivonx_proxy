API Reference — /api/proxy/

Health
- GET `/api/proxy/` — returns 200 and message when at least one node is available; 404 when none available.

State / Diagnostics
- GET `/api/proxy/state` — (authenticated) returns manager cache contents: active nodes, standby nodes, model lists, latencies, active counts.

Models
- GET `/api/tags` — returns aggregated `models` from nodes. Uses manager cached `ha_models:{addr}` values.

Proxy endpoints (forwarding)
- POST `/api/proxy/chat` — forwards Chat requests to a chosen node. Supports `stream: true` for streaming responses.
- POST `/api/proxy/generate` — forwards Generate requests. Supports streaming.
- POST `/api/proxy/embed` — single input embedding endpoint.
- POST `/api/proxy/embeddings` — batch embeddings endpoint.

Notes
- Requests must include `model` where applicable; manager will route only to nodes that advertise that model.
- The public API rejects explicit `node_id` to enforce manager-controlled routing.
- Streaming endpoints require ASGI for best real-time behavior.
