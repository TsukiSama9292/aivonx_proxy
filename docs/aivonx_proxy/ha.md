High-availability and selection strategies

Pools
- Active: nodes currently considered healthy and eligible for requests.
- Standby: nodes that failed health checks and are excluded until they recover.

Health checks
- Manager performs health probes to `/api/health` on each node. Healthy responses (non-5xx) keep node in active pool.
- Unhealthy nodes move to standby and are rechecked periodically (default model refresh job runs every 1 minute).

Selection strategies
- least_active (default): choose node with lowest current active count; increments the count while request is active.
- lowest_latency: choose node with lowest recent measured latency.

Model awareness
- Manager periodically queries `/api/tags` for each node and caches the `models` list under `ha_models:{addr}`.
- When `model_name` is provided for routing, only nodes advertising that model are considered.

Tuning
- Background job interval can be changed where manager is started.
- For production, consider a robust cache backend (Redis) instead of in-process LocMemCache if running multiple processes.
