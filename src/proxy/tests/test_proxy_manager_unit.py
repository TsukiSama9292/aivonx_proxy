from django.test import TestCase
from django.core.cache import cache

import sys
import types

from proxy.utils.proxy_manager import HAProxyManager
from proxy.models import node as NodeModel


class HAProxyManagerUnitTests(TestCase):
    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_refresh_from_db_populates_pools_and_id_map(self):
        # create nodes in DB
        n1 = NodeModel.objects.create(name="n1", address="192.168.0.10", port=11434, active=True)
        n2 = NodeModel.objects.create(name="n2", address="192.168.0.11", port=11434, active=False)

        mgr = HAProxyManager(nodes=[])
        # allow cache writes
        mgr._is_leader = True
        mgr.refresh_from_db()

        active = cache.get(mgr.ACTIVE_POOL_KEY)
        standby = cache.get(mgr.STANDBY_POOL_KEY)
        id_map = cache.get(mgr.NODE_ID_MAP_KEY)

        self.assertIn("http://192.168.0.10:11434", active)
        self.assertIn("http://192.168.0.11:11434", standby)
        self.assertEqual(id_map.get(str(n1.id)), "http://192.168.0.10:11434")
        self.assertEqual(id_map.get(str(n2.id)), "http://192.168.0.11:11434")

    def test_choose_node_lowest_latency_and_least_active(self):
        a = "http://192.168.0.10:11434"
        b = "http://192.168.0.11:11434"
        cache.set(HAProxyManager.ACTIVE_POOL_KEY, [a, b])

        mgr = HAProxyManager(nodes=[a, b])
        mgr._is_leader = True

        # Inject a fake django_redis that operates over Django cache for deterministic behavior
        class FakeConn:
            def get(self, key):
                return cache.get(key)

            def set(self, key, val):
                cache.set(key, int(val))

            def incr(self, key):
                val = cache.get(key, 0) or 0
                val = int(val) + 1
                cache.set(key, val)
                return val

            def decr(self, key):
                val = cache.get(key, 0) or 0
                val = max(0, int(val) - 1)
                cache.set(key, val)
                return val

            def eval(self, script, numkeys, *keys):
                # simple implementation: pick min count key and INCR it
                min_idx = 0
                min_val = None
                for i, k in enumerate(keys):
                    v = cache.get(k, 0) or 0
                    if min_val is None or int(v) < int(min_val):
                        min_val = int(v)
                        min_idx = i
                chosen_key = keys[min_idx]
                new_val = (cache.get(chosen_key, 0) or 0) + 1
                cache.set(chosen_key, int(new_val))
                # return [chosen_index_1based, new_count]
                return [min_idx + 1, int(new_val)]

        fake_mod = types.ModuleType('django_redis')
        fake_mod.get_redis_connection = lambda name='default': FakeConn()
        orig = sys.modules.get('django_redis')
        sys.modules['django_redis'] = fake_mod

        # set latencies
        cache.set(mgr.LATENCY_KEY_PREFIX + a, 0.2)
        cache.set(mgr.LATENCY_KEY_PREFIX + b, 0.05)

        chosen = mgr.choose_node(strategy="lowest_latency")
        self.assertEqual(chosen, b)

        # test least_active fallback using cache counts
        cache.set(mgr._active_count_key(a), 5)
        cache.set(mgr._active_count_key(b), 1)

        chosen2 = mgr.choose_node(strategy="least_active")
        # b has lower count so should be chosen
        self.assertEqual(chosen2, b)
        # ensure count incremented in cache (fallback path increments when leader)
        self.assertEqual(cache.get(mgr._active_count_key(b)), 2)
        # restore module
        if orig is None:
            del sys.modules['django_redis']
        else:
            sys.modules['django_redis'] = orig

    def test_acquire_and_release_node_updates_counts(self):
        a = "http://192.168.0.10:11434"
        cache.set(HAProxyManager.ACTIVE_POOL_KEY, [a])
        mgr = HAProxyManager(nodes=[a])
        mgr._is_leader = True
        # inject fake redis-like connection backed by cache
        class FakeConn2:
            def get(self, key):
                return cache.get(key)

            def incr(self, key):
                val = cache.get(key, 0) or 0
                val = int(val) + 1
                cache.set(key, val)
                return val

            def decr(self, key):
                val = cache.get(key, 0) or 0
                val = max(0, int(val) - 1)
                cache.set(key, val)
                return val

        fake_mod2 = types.ModuleType('django_redis')
        fake_mod2.get_redis_connection = lambda name='default': FakeConn2()
        orig = sys.modules.get('django_redis')
        sys.modules['django_redis'] = fake_mod2

        # ensure starting at 0
        self.assertEqual(cache.get(mgr._active_count_key(a), 0), 0)

        addr = mgr.acquire_node()
        self.assertEqual(addr, a)
        # acquire should increment count
        self.assertEqual(cache.get(mgr._active_count_key(a)), 1)

        # release should decrement but not below 0
        mgr.release_node(a)
        self.assertEqual(cache.get(mgr._active_count_key(a)), 0)
        if orig is None:
            del sys.modules['django_redis']
        else:
            sys.modules['django_redis'] = orig
