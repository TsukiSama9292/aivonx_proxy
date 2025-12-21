# ProxyConfig API

This document describes the `ProxyConfig` API that allows reading and updating
the global configuration used by the proxy's node selection logic.

## Endpoint

- `GET /api/proxy/config` — return the current proxy configuration
- `PUT /api/proxy/config` — replace the configuration (full update)
- `PATCH /api/proxy/config` — partial update

Requests and responses use JSON and the following fields are supported:

- `id` (integer) — read-only primary key
- `strategy` (string) — selection strategy; allowed values:
  - `least_active` (default) — load-balancing strategy that prefers less-burdened nodes
  - `lowest_latency` — choose node with lowest measured latency
- `updated_at` (string, ISO timestamp) — read-only last update time
- `updated_at` (string, ISO timestamp) — read-only last update time

## Examples

Get config

```bash
curl -sS http://localhost:8000/api/proxy/config
```

Response

```json
{
  "id": 1,
  "strategy": "least_active",
  "updated_at": "2025-12-21T12:34:56.789012Z"
}
```

Patch config (set lowest-latency strategy)

```bash
curl -X PATCH http://localhost:8000/api/proxy/config \
  -H 'Content-Type: application/json' \
  -d '{"strategy": "lowest_latency"}'
```

Response

```json
{
  "id": 1,
  "strategy": "lowest_latency",
  "updated_at": "2025-12-21T12:45:00.123456Z"
}
```

## Permissions

By default the endpoint uses the project-wide DRF permission configuration.
If your deployment requires that only administrators may change the config,
restrict write access (PUT/PATCH) via `@permission_classes` or DRF settings.

## Notes

- The proxy uses this configuration during node selection; changes take effect
  immediately for new requests.
- Only one `ProxyConfig` row is used; the view will create a default row if
  none exists.