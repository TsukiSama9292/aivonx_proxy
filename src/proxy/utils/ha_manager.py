import asyncio
import time
from typing import List, Optional

import httpx
from apscheduler.schedulers.background import BackgroundScheduler
from loguru import logger
from django.core.cache import cache


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

    def __init__(self, nodes: Optional[List[str]] = None, health_path: str = "/health") -> None:
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
            r = await self._client.get(url)
            latency = time.perf_counter() - t0
            ok = r.status_code == 200
            return ok, latency
        except Exception as e:
            logger.debug("ping failed for {}: {}", addr, e)
            return False, float("inf")

    def refresh_from_db(self, group_name: Optional[str] = None) -> None:
        """Load nodes from DB into the manager and cache.

        If `group_name` is provided, only nodes in that `node_group` are loaded.
        This uses the `node` and `node_group` models in the `proxy` app.
        """
        try:
            # Import models here to avoid import-time DB access when module is imported
            from proxy.models import node as NodeModel, node_group as NodeGroupModel

            qs = NodeModel.objects.filter(active=True)
            if group_name:
                try:
                    grp = NodeGroupModel.objects.get(name=group_name)
                    qs = grp.nodes.filter(active=True)
                except NodeGroupModel.DoesNotExist:
                    qs = NodeModel.objects.none()

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
        # fallback: try DB lookup
        try:
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
    return _global_manager


def init_global_manager_from_db(group_name: Optional[str] = None, health_path: str = "/health") -> HAProxyManager:
    """Initialize global manager by loading nodes from DB (optionally filtered by group name)."""
    global _global_manager
    if _global_manager is None:
        mgr = HAProxyManager(nodes=None, health_path=health_path)
        try:
            mgr.refresh_from_db(group_name=group_name)
        except Exception:
            # DB might be unavailable during migrations/startup
            pass
        _global_manager = mgr
    return _global_manager


def get_global_manager() -> Optional[HAProxyManager]:
    return _global_manager
