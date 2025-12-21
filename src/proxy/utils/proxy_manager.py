import asyncio
import time
from typing import List, Optional

import httpx
from apscheduler.schedulers.background import BackgroundScheduler
from loguru import logger
from django.core.cache import cache
from asgiref.sync import sync_to_async

class HAProxyManager:
    """High-availability manager for Ollama nodes.

    Stores simple state in Django cache (LocMemCache). Provides:
    - periodic health checks (async)
    - pools: active / standby
    - selection strategies: least_active, lowest_latency
    """

    ACTIVE_POOL_KEY = "ha_active_pool"
    STANDBY_POOL_KEY = "ha_standby_pool"
    ACTIVE_COUNT_KEY_PREFIX = "ha_active_count:"  # + address
    LATENCY_KEY_PREFIX = "ha_latency:"  # + address
    NODE_ID_MAP_KEY = "ha_node_id_map"  # stores {str(id): address}
    MODELS_KEY_PREFIX = "ha_models:"  # + address -> list of model names

    def __init__(self, nodes: Optional[List[str]] = None, health_path: str = "/api/health") -> None:
        # nodes may be a list of base addresses (e.g. http://host:port)
        # if None, manager will attempt to load nodes from DB via `refresh_from_db()`
        self.nodes = nodes or []
        self.health_path = health_path
        # initialize pools
        if cache.get(self.ACTIVE_POOL_KEY) is None:
            cache.set(self.ACTIVE_POOL_KEY, list(self.nodes))
        if cache.get(self.STANDBY_POOL_KEY) is None:
            cache.set(self.STANDBY_POOL_KEY, [])
        self._client = httpx.AsyncClient(timeout=5.0)
        self._scheduler: Optional[BackgroundScheduler] = None

        # if no explicit nodes were provided, try to populate from DB
        if not nodes:
            try:
                self.refresh_from_db()
            except Exception:
                # DB may not be ready at import/initialization time; ignore
                pass

    async def ping_node(self, addr: str) -> tuple[bool, float]:
        url = addr.rstrip("/") + self.health_path
        t0 = time.perf_counter()
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(url)
            latency = time.perf_counter() - t0
            # consider node healthy for any non-5xx response (some upstreams return 404 for /api/health)
            ok = 0 <= getattr(r, 'status_code', 500) < 500
            return ok, latency
        except Exception as e:
            logger.debug("ping failed for {}: {}", addr, e)
            return False, float("inf")

    async def _refresh_from_db_async(self) -> None:
        """Async version of refresh_from_db that wraps ORM calls with sync_to_async."""
        try:
            from proxy.models import node as NodeModel

            @sync_to_async
            def get_nodes():
                qs = NodeModel.objects.filter(active=True)
                nodes_list = []
                id_map = {}
                for n in qs:
                    addr = (n.address or "").strip()
                    if n.port:
                        if ":" not in addr.split("/")[-1]:
                            addr = f"{addr}:{n.port}"
                    if addr and not addr.startswith("http"):
                        addr = "http://" + addr
                    if addr:
                        nodes_list.append(addr)
                        id_map[str(n.id)] = addr
                return nodes_list, id_map

            nodes, id_map = await get_nodes()
            self.nodes = nodes
            cache.set(self.ACTIVE_POOL_KEY, list(nodes))
            cache.set(self.NODE_ID_MAP_KEY, id_map)
            cache.set(self.STANDBY_POOL_KEY, [])
            logger.info("HA manager refreshed nodes from DB (async): {}", nodes)
            logger.debug("refresh_from_db_async: set ACTIVE_POOL_KEY=%s, NODE_ID_MAP_KEY=%s", nodes, id_map)
        except Exception as e:
            logger.debug("refresh_from_db_async failed: {}", e)

    def refresh_from_db(self) -> None:
        """Load nodes from DB into the manager and cache.

        Loads all active `node` entries from the DB into the active pool.
        """
        try:
            # Import models here to avoid import-time DB access when module is imported
            from proxy.models import node as NodeModel

            # Check if we're in async context and need to defer to async version
            try:
                loop = asyncio.get_running_loop()
                # We're in async context; schedule async version
                asyncio.create_task(self._refresh_from_db_async())
                return
            except RuntimeError:
                # No running loop, proceed synchronously
                pass

            qs = NodeModel.objects.filter(active=True)

            nodes: List[str] = []
            id_map: dict[str, str] = {}
            for n in qs:
                addr = (n.address or "").strip()
                if n.port:
                    # ensure no duplicate port portion
                    if ":" not in addr.split("/")[-1]:
                        addr = f"{addr}:{n.port}"
                if addr and not addr.startswith("http"):
                    addr = "http://" + addr
                if addr:
                    nodes.append(addr)
                    id_map[str(n.id)] = addr

            # update internal list and set cache active pool
            self.nodes = nodes
            cache.set(self.ACTIVE_POOL_KEY, list(nodes))
            cache.set(self.NODE_ID_MAP_KEY, id_map)
            # clear standby when refreshing from DB
            cache.set(self.STANDBY_POOL_KEY, [])
            logger.info("HA manager refreshed nodes from DB: {}", nodes)
            logger.debug("refresh_from_db: set ACTIVE_POOL_KEY=%s, NODE_ID_MAP_KEY=%s", nodes, id_map)
        except Exception as e:
            logger.debug("refresh_from_db skipped (DB may be unavailable): {}", e)

    async def health_check_all(self) -> None:
        active = cache.get(self.ACTIVE_POOL_KEY, [])
        standby = cache.get(self.STANDBY_POOL_KEY, [])
        all_nodes = list({*active, *standby, *self.nodes})

        tasks = {addr: asyncio.create_task(self.ping_node(addr)) for addr in all_nodes}
        for addr, task in tasks.items():
            ok, latency = await task
            cache.set(self.LATENCY_KEY_PREFIX + addr, latency)
            if ok:
                # if previously standby, move to active
                if addr in standby:
                    standby = [a for a in standby if a != addr]
                    if addr not in active:
                        active.append(addr)
                        cache.set(self.ACTIVE_POOL_KEY, active)
                        cache.set(self.STANDBY_POOL_KEY, standby)
                        logger.info("Node restored -> active: {}", addr)
                else:
                    # ensure it's in active
                    if addr not in active:
                        active.append(addr)
                        cache.set(self.ACTIVE_POOL_KEY, active)
            else:
                # move to standby
                if addr in active:
                    active = [a for a in active if a != addr]
                    if addr not in standby:
                        standby.append(addr)
                    cache.set(self.ACTIVE_POOL_KEY, active)
                    cache.set(self.STANDBY_POOL_KEY, standby)
                    logger.warning("Node moved to standby: {}", addr)

    async def refresh_models_all(self) -> None:
        """Query each known node's `/api/tags` and store available model names.

        Stores list under cache key `ha_models:{addr}` and updates DB `node.models`.
        """
        active = cache.get(self.ACTIVE_POOL_KEY, [])
        standby = cache.get(self.STANDBY_POOL_KEY, [])
        all_nodes = list({*active, *standby, *self.nodes})

        # import model here to avoid import-time DB access
        try:
            from proxy.models import node as NodeModel
        except Exception:
            NodeModel = None

        # query each node with a small retry/backoff
        for addr in all_nodes:
            models_list = []
            url = addr.rstrip("/") + "/api/tags"
            resp = None
            for attempt in range(2):
                try:
                    import httpx
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        resp = await client.get(url)
                    break
                except Exception as e:
                    logger.debug("attempt %d failed for %s: %s", attempt + 1, addr, e)
                    try:
                        await asyncio.sleep(0.2 * (attempt + 1))
                    except Exception:
                        pass

            if resp is not None and resp.status_code == 200:
                try:
                    data = resp.json()
                    models = data.get("models") if isinstance(data, dict) else None
                    if isinstance(models, list):
                        for m in models:
                            if isinstance(m, dict) and m.get("name"):
                                models_list.append(m.get("name"))
                except Exception:
                    logger.debug("failed to parse /api/tags from %s", addr)
            else:
                logger.debug("no /api/tags response from %s (status=%s)", addr, getattr(resp, 'status_code', None))

            # update cache and DB
            cache.set(self.MODELS_KEY_PREFIX + addr, models_list)
            if NodeModel is not None:
                try:
                    @sync_to_async
                    def update_node_models():
                        qs = NodeModel.objects.filter(active=True)
                        for n in qs:
                            a = (n.address or "").strip()
                            if n.port and ":" not in a.split("/")[-1]:
                                a = f"{a}:{n.port}"
                            if a and not a.startswith("http"):
                                a = "http://" + a
                            if a == addr:
                                # use queryset update to avoid instance-level side-effects
                                NodeModel.objects.filter(pk=n.pk).update(available_models=models_list)
                                break
                    
                    await update_node_models()
                except Exception as e:
                    logger.debug("failed to update node.available_models for %s: %s", addr, e)

        logger.info("model refresh complete")

    def choose_node(self, model_name: Optional[str] = None, strategy: Optional[str] = None) -> Optional[str]:
        """Choose a node automatically for a given model_name.

        If strategy is None, the method will read ProxyConfig from DB.
        Returns the chosen node address (and increments active count), or None.
        """
        try:
            if strategy is None:
                from proxy.models import ProxyConfig
                # Check if in async context
                try:
                    asyncio.get_running_loop()
                    # In async context, skip DB query and use default
                    strategy = "least_active"
                except RuntimeError:
                    # Sync context, safe to query DB
                    cfg = ProxyConfig.objects.order_by("-updated_at").first()
                    if cfg:
                        strategy = cfg.strategy
        except Exception:
            strategy = strategy or "least_active"

        active = cache.get(self.ACTIVE_POOL_KEY, [])
        if not active:
            return None

        # filter candidates by model availability
        if model_name:
            candidates = [a for a in active if model_name in cache.get(self.MODELS_KEY_PREFIX + a, [])]
        else:
            candidates = list(active)

        if not candidates:
            return None

        chosen = None
        if strategy == "lowest_latency":
            best_lat = float("inf")
            for a in candidates:
                lat = cache.get(self.LATENCY_KEY_PREFIX + a, float("inf"))
                if lat < best_lat:
                    best_lat = lat
                    chosen = a
        else:
            best_cnt = None
            for a in candidates:
                cnt = cache.get(self._active_count_key(a), 0)
                if best_cnt is None or cnt < best_cnt:
                    best_cnt = cnt
                    chosen = a

        if chosen:
            key = self._active_count_key(chosen)
            cache.set(key, cache.get(key, 0) + 1)
        return chosen

    def _active_count_key(self, addr: str) -> str:
        return self.ACTIVE_COUNT_KEY_PREFIX + addr

    def acquire_node(self, strategy: str = "least_active") -> Optional[str]:
        active = cache.get(self.ACTIVE_POOL_KEY, [])
        if not active:
            return None

        if strategy == "lowest_latency":
            best = None
            best_lat = float("inf")
            for a in active:
                lat = cache.get(self.LATENCY_KEY_PREFIX + a, float("inf"))
                if lat < best_lat:
                    best = a
                    best_lat = lat
            chosen = best
        else:  # least_active
            chosen = None
            best_cnt = None
            for a in active:
                cnt = cache.get(self._active_count_key(a), 0)
                if best_cnt is None or cnt < best_cnt:
                    best_cnt = cnt
                    chosen = a

        if chosen:
            # increment active count
            key = self._active_count_key(chosen)
            cache.set(key, cache.get(key, 0) + 1)
        return chosen

    def get_address_for_node_id(self, node_id: int) -> Optional[str]:
        """Return the configured address for a node id, or None if not found."""
        id_map = cache.get(self.NODE_ID_MAP_KEY)
        if isinstance(id_map, dict):
            return id_map.get(str(node_id))
        # fallback: try DB lookup (only in sync context)
        try:
            # Check if in async context
            try:
                asyncio.get_running_loop()
                # In async context, cannot do DB lookup
                return None
            except RuntimeError:
                # Sync context, safe to query DB
                from proxy.models import node as NodeModel

                n = NodeModel.objects.filter(pk=node_id, active=True).first()
                if not n:
                    return None
                addr = (n.address or "").strip()
                if n.port and ":" not in addr.split("/")[-1]:
                    addr = f"{addr}:{n.port}"
                if addr and not addr.startswith("http"):
                    addr = "http://" + addr
                return addr
        except Exception:
            return None

    def acquire_node_by_id(self, node_id: int) -> Optional[str]:
        """Reserve a specific node by id (increments active count) and return its address.

        Returns None if the node is not known or not active/healthy.
        """
        addr = self.get_address_for_node_id(node_id)
        if not addr:
            return None
        # ensure it's in active pool
        active = cache.get(self.ACTIVE_POOL_KEY, [])
        if addr not in active:
            return None
        key = self._active_count_key(addr)
        cache.set(key, cache.get(key, 0) + 1)
        return addr

    def release_node(self, addr: str) -> None:
        key = self._active_count_key(addr)
        cnt = cache.get(key, 0)
        cnt = max(0, cnt - 1)
        cache.set(key, cnt)

    def start_scheduler(self, interval_minutes: int = 10) -> None:
        if self._scheduler is not None:
            return

        def _sync_job():
            try:
                # run the async health check in a fresh event loop
                import asyncio

                asyncio.run(self.health_check_all())
            except Exception as e:
                logger.debug("scheduler job error: {}", e)

        sched = BackgroundScheduler()
        sched.add_job(_sync_job, "interval", minutes=interval_minutes)
        # schedule model refresh every 1 minute
        def _sync_models_job():
            try:
                import asyncio

                asyncio.run(self.refresh_models_all())
            except Exception as e:
                logger.debug("models refresh job error: {}", e)

        sched.add_job(_sync_models_job, "interval", minutes=1)
        sched.start()
        self._scheduler = sched
        logger.info("HAProxyManager scheduler started ({} min)", interval_minutes)

    async def close(self) -> None:
        await self._client.aclose()
        if self._scheduler:
            try:
                self._scheduler.shutdown(wait=False)
            except Exception:
                pass


_global_manager: HAProxyManager | None = None


def init_global_manager(nodes: List[str], health_path: str = "/health") -> HAProxyManager:
    global _global_manager
    if _global_manager is None:
        _global_manager = HAProxyManager(nodes=nodes, health_path=health_path)
        try:
            # attach to AppConfig for direct access from views
            from django.apps import apps as _django_apps

            try:
                _django_apps.get_app_config("proxy").proxy_manager = _global_manager
            except Exception:
                pass
        except Exception:
            pass
    return _global_manager


def init_global_manager_from_db(health_path: str = "/api/health") -> HAProxyManager:
    """Initialize global manager by loading nodes from DB."""
    global _global_manager
    if _global_manager is None:
        logger.info("init_global_manager_from_db: initializing manager in process")
        mgr = HAProxyManager(nodes=None, health_path=health_path)
        try:
            mgr.refresh_from_db()
        except Exception:
            # DB might be unavailable during migrations/startup
            pass
        def _run_coro(coro):
            # Run or schedule a coroutine depending on whether an event loop is running.
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                # schedule and return immediately
                try:
                    loop.create_task(coro)
                except Exception:
                    # fallback to ensure_future
                    asyncio.ensure_future(coro)
            else:
                try:
                    asyncio.run(coro)
                except Exception:
                    # best-effort; ignore failures here
                    pass

        try:
            # perform an initial models refresh so caches/DB `available_models` are populated
            logger.debug("init_global_manager_from_db: scheduling initial model refresh and health check")
            _run_coro(mgr.refresh_models_all())
            # perform an immediate health check to populate active/standby pools
            _run_coro(mgr.health_check_all())
            # start periodic health and model refresh jobs
            mgr.start_scheduler()
            logger.debug("init_global_manager_from_db: scheduled refresh/health and started scheduler")
        except Exception as e:
            logger.exception("init_global_manager_from_db: failed to schedule startup jobs: {}", e)
        _global_manager = mgr
        try:
            # attach to AppConfig so views using AppConfig.proxy_manager see it
            from django.apps import apps as _django_apps

            try:
                _django_apps.get_app_config("proxy").proxy_manager = _global_manager
                logger.debug("init_global_manager_from_db: attached manager to AppConfig.proxy_manager")
            except Exception:
                logger.debug("init_global_manager_from_db: failed to attach to AppConfig")
        except Exception:
            logger.debug("init_global_manager_from_db: attach to AppConfig skipped")
    return _global_manager


def get_global_manager() -> Optional[HAProxyManager]:
    global _global_manager
    if _global_manager is None:
        try:
            # Try to initialize from DB on-demand (covers WSGI processes)
            return init_global_manager_from_db()
        except Exception:
            return None
    return _global_manager
