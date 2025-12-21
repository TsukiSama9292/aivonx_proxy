# Ollama Proxy Docs

| File | Purpose | Summary |
|---|---|---|
| `overview.md` | Project overview | High-level goals, key concepts, and where to find core code files. |
| `architecture.md` | Architecture | Explains `HAProxyManager`, data flow for proxy requests, async/DB safety. |
| `modules.md` | Module guide | File-by-file guide for `proxy/`, `aivonx/` and testing locations. |
| `api_endpoints.md` | API reference | Lists public `/api/proxy/` endpoints: health, tags, generate, chat, embed, embeddings. |
| `testing.md` | Testing guide | How to run Django tests, mocking httpx, CI notes. |
| `ha.md` | HA & selection strategies | Pools, health checks, `least_active` and `lowest_latency`, model awareness. |
| `cli.md` | CLI launcher | Usage for `main.py`, argument precedence and examples. |
| `deployment.md` | Deployment notes | ASGI recommendations, uvicorn example, cache/backend suggestions. |
| `troubleshooting.md` | Troubleshooting | Common issues and quick fixes (startup, buffering, cache, tests). |
| `config.md` | Proxy configuration API | Read and update `ProxyConfig` (selection `strategy`). |

Use the files above to dive deeper into specific areas of the proxy implementation. For a quick start, see the repository `README.md` at the project root.

