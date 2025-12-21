Module guide

proxy/
- `models.py` — `node` model and `ProxyConfig`.
- `viewsets.py` — Node CRUD (DRF ModelViewSet).
- `serializers.py` — serializers for nodes (supports `?fields=` param).
- `utils/proxy_manager.py` — `HAProxyManager` implementation (health, models, selection, scheduler).
- `handlers.py` — proxy endpoints: health, tags, generate, chat, embed, embeddings.
- `streaming.py` — utilities that stream upstream bytes through Django responses.

aivonx/
- `asgi.py` — wires manager initialization during ASGI lifespan.
- `settings.py` — Django settings, including cache backend used for in-process state.

Testing
- Tests live in `src/proxy/tests/` and use Django `TestCase`/`TransactionTestCase`.
- Use `python manage.py test proxy.tests` to run the proxy test suite.

Where to look for behavior
- Manager logic and caching: `src/proxy/utils/proxy_manager.py`.
- Streaming details: `src/proxy/streaming.py` and handlers where responses are proxied.
