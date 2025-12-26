import asyncio
import time
from typing import List, Optional

import httpx
from apscheduler.schedulers.background import BackgroundScheduler
import logging
logger = logging.getLogger('proxy')
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
        # flag set for the process that acquires the leader lock — only that process
        # should perform CRUD operations against Redis (writes). Other workers
        # should only read from cache/Redis.
        self._is_leader = False
        self._leader_owner = None

    def _can_write_cache(self) -> bool:
        """Return True if this manager instance is allowed to perform cache writes.

        Preference order:
        - explicit `_is_leader` flag set when this process acquired the lock
        - verify Redis `ha_manager_leader` owner matches this process' owner id
        - fallback to truthiness of `cache.get('ha_manager_leader')` (best-effort)
        """
        # Only the process that explicitly holds the leader flag or whose
        # owner id matches the raw Redis owner may write cache. Avoid
        # fallbacks that rely on cache.get truthiness (LocMem or intermittent
        # connection issues can give false-positives).
        try:
            if getattr(self, "_is_leader", False):
                return True
            owner = getattr(self, '_leader_owner', None)
            try:
                from django_redis import get_redis_connection
                conn = get_redis_connection('default')
                val = conn.get('ha_manager_leader')
                if val is None:
                    return False
                if isinstance(val, (bytes, bytearray)):
                    val = val.decode()
                if owner:
                    return val == owner
                return False
            except Exception as e:
                # If we can't reach Redis, conservatively deny write privileges.
                logger.debug("_can_write_cache: redis check failed: %s", e)
                return False
        except Exception:
            return False

        # if no explicit nodes were provided, try to populate from DB
        if not nodes:
            try:
                self.refresh_from_db()
            except Exception as e:
                # DB may not be ready at import/initialization time; log and continue
                logger.debug("init nodes from DB failed during init: %s", e)

    async def ping_node(self, addr: str) -> tuple[bool, float]:
        # Ollama exposes a base-url health response (e.g. GET http://host:port
        # -> "ollama is running"). If `health_path` is empty or '/', call the
        # node root; otherwise append the configured path.
        if not self.health_path or self.health_path == "/":
            url = addr.rstrip("/")
        else:
            url = addr.rstrip("/") + (self.health_path if self.health_path.startswith("/") else "/" + self.health_path)
        t0 = time.perf_counter()
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(url)
            latency = time.perf_counter() - t0
            # consider node healthy for any non-5xx response (some upstreams return 404 for /api/health)
            ok = 0 <= getattr(r, 'status_code', 500) < 500
            logger.debug("ping %s: status=%s latency=%.3fs ok=%s", addr, getattr(r, 'status_code', 'N/A'), latency, ok)
            return ok, latency
        except Exception as e:
            logger.warning("ping failed for %s: %s", addr, e)
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
                
                # Also load inactive nodes for standby pool
                standby_list = []
                qs_inactive = NodeModel.objects.filter(active=False)
                for n in qs_inactive:
                    addr = (n.address or "").strip()
                    if n.port:
                        if ":" not in addr.split("/")[-1]:
                            addr = f"{addr}:{n.port}"
                    if addr and not addr.startswith("http"):
                        addr = "http://" + addr
                    if addr:
                        standby_list.append(addr)
                        id_map[str(n.id)] = addr  # include in id_map
                
                return nodes_list, standby_list, id_map

            nodes, standby_nodes, id_map = await get_nodes()
            self.nodes = nodes
            # only the leader should perform cache writes
            if self._can_write_cache():
                cache.set(self.ACTIVE_POOL_KEY, list(nodes))
                cache.set(self.STANDBY_POOL_KEY, standby_nodes)
                cache.set(self.NODE_ID_MAP_KEY, id_map)
            logger.info("HA manager refreshed nodes from DB (async): active=%s, standby=%s", nodes, standby_nodes)
            logger.debug("refresh_from_db_async: set ACTIVE_POOL_KEY=%s, STANDBY_POOL_KEY=%s, NODE_ID_MAP_KEY=%s", nodes, standby_nodes, id_map)
        except Exception as e:
            logger.debug("refresh_from_db_async failed: %s", e)

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

            # Also load inactive nodes into standby pool
            standby_nodes: List[str] = []
            qs_inactive = NodeModel.objects.filter(active=False)
            for n in qs_inactive:
                addr = (n.address or "").strip()
                if n.port:
                    if ":" not in addr.split("/")[-1]:
                        addr = f"{addr}:{n.port}"
                if addr and not addr.startswith("http"):
                    addr = "http://" + addr
                if addr:
                    standby_nodes.append(addr)
                    id_map[str(n.id)] = addr  # include in id_map

            # update internal list and set cache active pool (leader only)
            self.nodes = nodes
            if self._can_write_cache():
                cache.set(self.ACTIVE_POOL_KEY, list(nodes))
                cache.set(self.NODE_ID_MAP_KEY, id_map)
                # Set standby pool from DB inactive nodes
                cache.set(self.STANDBY_POOL_KEY, standby_nodes)
            logger.info("HA manager refreshed nodes from DB: active=%s, standby=%s", nodes, standby_nodes)
            logger.debug("refresh_from_db: set ACTIVE_POOL_KEY=%s, STANDBY_POOL_KEY=%s, NODE_ID_MAP_KEY=%s", nodes, standby_nodes, id_map)
        except Exception as e:
            logger.debug("refresh_from_db skipped (DB may be unavailable): %s", e)

    async def health_check_all(self) -> None:
        active = cache.get(self.ACTIVE_POOL_KEY, [])
        standby = cache.get(self.STANDBY_POOL_KEY, [])
        all_nodes = list({*active, *standby, *self.nodes})
        logger.info("health_check_all: checking %d nodes (active=%d, standby=%d)", len(all_nodes), len(active), len(standby))

        # import model here so we can persist active state changes
        try:
            from proxy.models import node as NodeModel
        except Exception:
            NodeModel = None

        tasks = {addr: asyncio.create_task(self.ping_node(addr)) for addr in all_nodes}
        for addr, task in tasks.items():
            ok, latency = await task
            # latency is a per-node metric; only the leader should persist it
            if self._can_write_cache():
                cache.set(self.LATENCY_KEY_PREFIX + addr, latency)
            
            # Helper to update DB active field (called for both healthy and unhealthy nodes)
            async def _sync_db_active_state(target_addr: str, should_be_active: bool):
                """Update DB node.active to match cache pool state."""
                if NodeModel is None or not self._can_write_cache():
                    return
                try:
                    @sync_to_async
                    def _update_db():
                        qs = NodeModel.objects.all()
                        for n in qs:
                            a = (n.address or "").strip()
                            if n.port and ":" not in a.split("/")[-1]:
                                a = f"{a}:{n.port}"
                            if a and not a.startswith("http"):
                                a = "http://" + a
                            if a == target_addr:
                                # Only update if the current DB value differs
                                if n.active != should_be_active:
                                    NodeModel.objects.filter(pk=n.pk).update(active=should_be_active)
                                    logger.info("DB sync: node %s active=%s (addr=%s)", n.id, should_be_active, target_addr)
                                break
                    await _update_db()
                except Exception as e:
                    logger.debug("failed to sync DB active=%s for %s: %s", should_be_active, target_addr, e)
            
            if ok:
                # Node is healthy: ensure it's in active pool
                was_in_standby = addr in standby
                if was_in_standby:
                    standby = [a for a in standby if a != addr]
                if addr not in active:
                    active.append(addr)
                    if self._can_write_cache():
                        cache.set(self.ACTIVE_POOL_KEY, active)
                        cache.set(self.STANDBY_POOL_KEY, standby)
                    if was_in_standby:
                        logger.info("Node restored -> active: %s", addr)
                # Always sync DB active=True for healthy nodes (ensure consistency)
                await _sync_db_active_state(addr, True)
            else:
                # Node is unhealthy: ensure it's in standby pool
                was_in_active = addr in active
                if was_in_active:
                    active = [a for a in active if a != addr]
                if addr not in standby:
                    standby.append(addr)
                if self._can_write_cache():
                    cache.set(self.ACTIVE_POOL_KEY, active)
                    cache.set(self.STANDBY_POOL_KEY, standby)
                if was_in_active:
                    logger.warning("Node moved to standby: %s", addr)
                # Always sync DB active=False for unhealthy nodes (ensure consistency)
                await _sync_db_active_state(addr, False)

    async def refresh_models_all(self) -> None:
        """Query each known node's `/api/tags` and store available model names.

        Stores list under cache key `ha_models:{addr}` and updates DB `node.models`.
        If a node fails to respond, immediately mark it as unhealthy.
        """
        active = cache.get(self.ACTIVE_POOL_KEY, [])
        standby = cache.get(self.STANDBY_POOL_KEY, [])
        all_nodes = list({*active, *standby, *self.nodes})

        # import model here to avoid import-time DB access
        try:
            from proxy.models import node as NodeModel
        except Exception:
            NodeModel = None

        # track nodes that failed during model refresh
        failed_nodes = []

        # query each node with a small retry/backoff
        for addr in all_nodes:
            models_list = []
            url = addr.rstrip("/") + "/api/tags"
            resp = None
            node_failed = False
            for attempt in range(2):
                try:
                    import httpx
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        resp = await client.get(url)
                    break
                except Exception as e:
                    logger.debug("attempt %d failed for %s: %s", attempt + 1, addr, e)
                    if attempt == 1:  # last attempt failed
                        node_failed = True
                    try:
                        await asyncio.sleep(0.2 * (attempt + 1))
                    except Exception as e:
                        logger.debug("sleep between attempts failed: %s", e)

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
                logger.warning("no /api/tags response from %s (status=%s) - marking as failed", addr, getattr(resp, 'status_code', None))
                node_failed = True

            # If node failed after retries, track it for immediate health status update
            if node_failed and addr in active:
                failed_nodes.append(addr)
                logger.warning("node %s failed during model refresh - will mark as inactive immediately", addr)

            # update cache and DB (cache writes only by leader)
            if self._can_write_cache():
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

        logger.info("model refresh complete (found %d failed nodes)", len(failed_nodes))

        # Immediately move failed nodes to standby and update DB active=False
        if failed_nodes:
            can_write = self._can_write_cache()
            logger.info("attempting to move %d failed nodes to standby (can_write=%s, is_leader=%s)", 
                       len(failed_nodes), can_write, getattr(self, '_is_leader', False))
            if not can_write:
                logger.warning("cannot write cache - skipping immediate standby move for failed nodes")
            else:
                logger.info("immediately moving %d failed nodes to standby", len(failed_nodes))
                active = cache.get(self.ACTIVE_POOL_KEY, [])
                standby = cache.get(self.STANDBY_POOL_KEY, [])
                
                for addr in failed_nodes:
                    if addr in active:
                        active = [a for a in active if a != addr]
                        if addr not in standby:
                            standby.append(addr)
                        logger.warning("Node moved to standby (model refresh failure): %s", addr)
                        
                        # Update DB active=False immediately
                        if NodeModel is not None:
                            try:
                                @sync_to_async
                                def _mark_inactive():
                                    qs = NodeModel.objects.all()
                                    for n in qs:
                                        a = (n.address or "").strip()
                                        if n.port and ":" not in a.split("/")[-1]:
                                            a = f"{a}:{n.port}"
                                        if a and not a.startswith("http"):
                                            a = "http://" + a
                                        if a == addr:
                                            if n.active:  # only update if currently active
                                                NodeModel.objects.filter(pk=n.pk).update(active=False)
                                                logger.info("DB sync: node %s active=False (addr=%s) due to model refresh failure", n.id, addr)
                                            break
                                await _mark_inactive()
                            except Exception as e:
                                logger.debug("failed to mark node inactive in DB for %s: %s", addr, e)
                
                # Update cache pools
                cache.set(self.ACTIVE_POOL_KEY, active)
                cache.set(self.STANDBY_POOL_KEY, standby)
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
            logger.warning("choose_node: no active nodes available")
            return None

        logger.debug("choose_node: active pool has %d nodes: %s", len(active), active)

        # filter candidates by model availability
        if model_name:
            candidates = []
            for a in active:
                models = cache.get(self.MODELS_KEY_PREFIX + a, [])
                logger.debug("choose_node: node %s has models: %s", a, models)
                if model_name in models:
                    candidates.append(a)
            logger.info("choose_node: filtered to %d candidates with model '%s' from %d active nodes", 
                       len(candidates), model_name, len(active))
        else:
            candidates = list(active)
            logger.debug("choose_node: no model filter, using all %d active nodes", len(candidates))

        if not candidates:
            logger.warning("choose_node: no candidates available for model '%s'", model_name)
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
            # Use Redis Lua script for atomic "read all counts, choose min, increment"
            # This prevents race condition where multiple requests choose the same node
            try:
                from django_redis import get_redis_connection
                conn = get_redis_connection('default')
                
                # Build list of keys for all candidate nodes
                keys = [self._active_count_key(a) for a in candidates]
                
                # Debug: log current counts before selection
                current_counts = {}
                for a in candidates:
                    try:
                        val = conn.get(self._active_count_key(a))
                        if val is not None:
                            current_counts[a] = int(val) if isinstance(val, (bytes, str)) else val
                        else:
                            current_counts[a] = 0
                    except Exception:
                        current_counts[a] = 0
                logger.info("choose_node: current counts before selection: %s", current_counts)
                
                # Lua script: get all counts, find index of minimum, increment that key
                # KEYS: array of count keys
                # Returns: {chosen_index (1-based), new_count, chosen_addr}
                lua_script = """
                local min_count = nil
                local min_idx = 1
                for i, key in ipairs(KEYS) do
                    local count = redis.call('GET', key)
                    if count == false then
                        count = 0
                    else
                        count = tonumber(count)
                    end
                    if min_count == nil or count < min_count then
                        min_count = count
                        min_idx = i
                    end
                end
                local chosen_key = KEYS[min_idx]
                local new_count = redis.call('INCR', chosen_key)
                return {min_idx, new_count}
                """
                
                result = conn.eval(lua_script, len(keys), *keys)
                chosen_idx = int(result[0]) - 1  # Lua is 1-based, Python is 0-based
                new_count = int(result[1])
                chosen = candidates[chosen_idx]
                logger.info("choose_node: atomically chose %s with new count %s (had %d candidates)", 
                           chosen, new_count, len(candidates))
            except Exception as e:
                logger.warning("choose_node: Redis Lua script failed (%s), falling back to non-atomic", e)
                # Fallback to non-atomic operation
                best_cnt = None
                for a in candidates:
                    try:
                        from django_redis import get_redis_connection
                        conn = get_redis_connection('default')
                        val = conn.get(self._active_count_key(a))
                        if val is not None:
                            cnt = int(val) if isinstance(val, (bytes, str)) else val
                        else:
                            cnt = 0
                    except Exception:
                        cnt = cache.get(self._active_count_key(a), 0)
                    
                    if best_cnt is None or cnt < best_cnt:
                        best_cnt = cnt
                        chosen = a
                
                # Increment after choosing (non-atomic fallback)
                if chosen:
                    key = self._active_count_key(chosen)
                    try:
                        from django_redis import get_redis_connection
                        conn = get_redis_connection('default')
                        new_val = conn.incr(key)
                        logger.info("choose_node: incremented %s to %s (addr=%s) [fallback]", key, new_val, chosen)
                    except Exception as e2:
                        logger.warning("choose_node: Redis INCR failed (%s), falling back to cache", e2)
                        if self._can_write_cache():
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
            # Use Redis Lua script for atomic "read all counts, choose min, increment"
            try:
                from django_redis import get_redis_connection
                conn = get_redis_connection('default')
                
                keys = [self._active_count_key(a) for a in active]
                
                lua_script = """
                local min_count = nil
                local min_idx = 1
                for i, key in ipairs(KEYS) do
                    local count = redis.call('GET', key)
                    if count == false then
                        count = 0
                    else
                        count = tonumber(count)
                    end
                    if min_count == nil or count < min_count then
                        min_count = count
                        min_idx = i
                    end
                end
                local chosen_key = KEYS[min_idx]
                local new_count = redis.call('INCR', chosen_key)
                return {min_idx, new_count}
                """
                
                result = conn.eval(lua_script, len(keys), *keys)
                chosen_idx = int(result[0]) - 1
                new_count = int(result[1])
                chosen = active[chosen_idx]
                logger.info("acquire_node: atomically chose %s with new count %s (had %d nodes)", 
                           chosen, new_count, len(active))
            except Exception as e:
                logger.warning("acquire_node: Redis Lua script failed (%s), falling back", e)
                # Fallback to non-atomic
                chosen = None
                best_cnt = None
                for a in active:
                    try:
                        from django_redis import get_redis_connection
                        conn = get_redis_connection('default')
                        val = conn.get(self._active_count_key(a))
                        if val is not None:
                            cnt = int(val) if isinstance(val, (bytes, str)) else val
                        else:
                            cnt = 0
                    except Exception:
                        cnt = cache.get(self._active_count_key(a), 0)
                    
                    if best_cnt is None or cnt < best_cnt:
                        best_cnt = cnt
                        chosen = a
                
                if chosen:
                    key = self._active_count_key(chosen)
                    try:
                        from django_redis import get_redis_connection
                        conn = get_redis_connection('default')
                        new_val = conn.incr(key)
                        logger.info("acquire_node: incremented %s to %s (addr=%s) [fallback]", key, new_val, chosen)
                    except Exception as e2:
                        logger.warning("acquire_node: Redis INCR failed (%s), falling back to cache", e2)
                        if self._can_write_cache():
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
        # Use Redis INCR for atomic increment (works from any worker)
        try:
            from django_redis import get_redis_connection
            conn = get_redis_connection('default')
            new_val = conn.incr(key)
            logger.info("acquire_node_by_id: incremented %s to %s (addr=%s)", key, new_val, addr)
        except Exception as e:
            logger.warning("acquire_node_by_id: Redis INCR failed (%s), falling back to cache", e)
            # Fallback to cache.set if Redis unavailable
            if self._can_write_cache():
                cache.set(key, cache.get(key, 0) + 1)
        return addr

    def release_node(self, addr: str) -> None:
        key = self._active_count_key(addr)
        # Use Redis DECR for atomic decrement (works from any worker)
        try:
            from django_redis import get_redis_connection
            conn = get_redis_connection('default')
            # DECR can go negative, so check first
            val = conn.get(key)
            if val is not None:
                current = int(val) if isinstance(val, (bytes, str)) else val
                if current > 0:
                    new_val = conn.decr(key)
                    logger.info("release_node: decremented %s to %s (addr=%s)", key, new_val, addr)
                else:
                    logger.debug("release_node: %s already at 0, not decrementing", key)
            else:
                # Key doesn't exist, set to 0
                conn.set(key, 0)
                logger.debug("release_node: %s didn't exist, set to 0", key)
        except Exception as e:
            logger.warning("release_node: Redis DECR failed (%s), falling back to cache", e)
            # Fallback to cache operations if Redis unavailable
            cnt = cache.get(key, 0)
            cnt = max(0, cnt - 1)
            if self._can_write_cache():
                cache.set(key, cnt)

    def start_scheduler(self, interval_seconds: int = 10) -> None:
        if self._scheduler is not None:
            return

        def _sync_job():
            try:
                # run the async health check in a fresh event loop
                import asyncio

                asyncio.run(self.health_check_all())
            except Exception as e:
                logger.debug("scheduler job error: %s", e)

        sched = BackgroundScheduler()
        # Run health check immediately on startup, then every interval_seconds
        import datetime
        sched.add_job(_sync_job, "interval", seconds=interval_seconds, next_run_time=datetime.datetime.now())
        # schedule model refresh every 1 minute
        def _sync_models_job():
            try:
                import asyncio

                asyncio.run(self.refresh_models_all())
            except Exception as e:
                logger.debug("models refresh job error: %s", e)

        sched.add_job(_sync_models_job, "interval", minutes=1)
        # schedule a short-poll job to listen for external refresh requests (set by signals)
        def _sync_refresh_on_request():
            try:
                from django_redis import get_redis_connection
                conn = get_redis_connection('default')
                val = conn.get('ha_refresh_request')
                if val is None:
                    return
                # consume the request and run refreshes
                try:
                    # synchronous DB refresh
                    self.refresh_from_db()
                except Exception:
                    logger.debug("poll-refresh: refresh_from_db failed")
                try:
                    import asyncio

                    asyncio.run(self.refresh_models_all())
                except Exception:
                    logger.debug("poll-refresh: refresh_models_all failed")
                try:
                    import asyncio

                    asyncio.run(self.health_check_all())
                except Exception:
                    logger.debug("poll-refresh: health_check_all failed")
                try:
                    conn.delete('ha_refresh_request')
                except Exception as e:
                    logger.debug("poll-refresh: failed to delete ha_refresh_request: %s", e)
            except Exception:
                # best-effort, ignore polling errors
                return

        sched.add_job(_sync_refresh_on_request, 'interval', seconds=5)
        sched.start()
        self._scheduler = sched
        logger.info("HAProxyManager scheduler started (health check every %d sec)", interval_seconds)

    async def close(self) -> None:
        await self._client.aclose()
        if self._scheduler:
            try:
                self._scheduler.shutdown(wait=False)
            except Exception as e:
                logger.debug("HAProxyManager.close: scheduler.shutdown failed: %s", e)


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
            except Exception as e:
                logger.debug("init_global_manager: attach to AppConfig failed: %s", e)
        except Exception as e:
            logger.debug("init_global_manager: django apps attach failed: %s", e)
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
            logger.debug("refresh_from_db failed during init")
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
                    logger.debug("failed to run coroutine")

        try:
            # perform an initial models refresh so caches/DB `available_models` are populated
            logger.debug("init_global_manager_from_db: scheduling initial model refresh and health check")
            _run_coro(mgr.refresh_models_all())
            # perform an immediate health check to populate active/standby pools
            _run_coro(mgr.health_check_all())
            # start periodic health and model refresh jobs
            # Try to acquire a distributed leader lock so only one worker starts the scheduler.
            # `cache.add` is atomic for shared cache backends (Redis/Memcached). LocMemCache is
            # process-local, so switch to a shared cache for this to work across workers.
            leader_key = "ha_manager_leader"
            # lock timeout in seconds (if process dies, lock expires and another worker can take over)
            leader_lock_timeout = 60 * 30
            # Prefer a raw Redis SET NX to acquire a single-process leader lock.
            # This avoids relying on the Django cache backend semantics (which may
            # be process-local in some environments) and gives us an owner id
            # we can verify across processes.
            got_lock = False
            try:
                from django_redis import get_redis_connection
                import socket, os
                conn = get_redis_connection('default')
                owner = f"{socket.gethostname()}:{os.getpid()}"
                # SET key value NX EX ttl -> atomic acquire
                # redis-py returns True if the key was set
                try:
                    set_ok = conn.set(leader_key, owner, nx=True, ex=leader_lock_timeout)
                except TypeError:
                    # older redis client may not accept nx/ex kwargs on set; fallback
                    try:
                        set_ok = conn.setnx(leader_key, owner)
                        if set_ok:
                            conn.expire(leader_key, leader_lock_timeout)
                    except Exception:
                        set_ok = False
                if set_ok:
                    got_lock = True
                    mgr._leader_owner = owner
                    mgr._is_leader = True
                else:
                    # if not set, someone else holds it; don't assume leadership
                    got_lock = False
            except Exception:
                # If Redis isn't reachable, fall back to Django cache.add as a best-effort
                try:
                    got_lock = cache.add(leader_key, True, leader_lock_timeout)
                    if got_lock:
                        mgr._is_leader = True
                        try:
                            import socket, os
                            mgr._leader_owner = f"{socket.gethostname()}:{os.getpid()}"
                        except Exception as e:
                            logger.debug("init_global_manager_from_db: failed to determine leader owner: %s", e)
                            mgr._leader_owner = None
                except Exception:
                    got_lock = False
                    # ensure leader populates caches now that it owns the lock
                    try:
                        # perform a sync DB refresh so ACTIVE_POOL_KEY/NODE_ID_MAP_KEY are set
                        try:
                            mgr.refresh_from_db()
                        except Exception as e:
                            logger.debug("init_global_manager_from_db: refresh_from_db failed: %s", e)
                        # also trigger async refreshes (models + health) to repopulate caches
                        _run_coro(mgr.refresh_models_all())
                        _run_coro(mgr.health_check_all())
                    except Exception:
                        logger.debug("init_global_manager_from_db: leader post-lock refresh failed")
                    mgr.start_scheduler()
                    logger.info("init_global_manager_from_db: acquired leader lock and started scheduler")
                except Exception as e:
                    logger.exception("init_global_manager_from_db: failed to start scheduler: %s", e)
            else:
                logger.info("init_global_manager_from_db: did not acquire leader lock; scheduler not started in this worker")
            logger.debug("init_global_manager_from_db: scheduled refresh/health and started scheduler")
        except Exception as e:
            logger.exception("init_global_manager_from_db: failed to schedule startup jobs: %s", e)
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
