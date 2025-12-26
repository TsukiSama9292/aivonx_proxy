from django.test import TestCase
from django.core.cache import cache
from unittest.mock import MagicMock

# Patch manager at module level to prevent signal blocking
import proxy.utils.proxy_manager as pm_module
_mock_manager = MagicMock()
_mock_manager.refresh_from_db = MagicMock()
_mock_manager._is_leader = False
pm_module._global_manager = _mock_manager

from proxy.models import node as NodeModel
from proxy.utils.proxy_manager import HAProxyManager


class ProxyManagerTests(TestCase):
    """Tests for HAProxyManager functionality."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Clear Redis leader lock before tests
        try:
            from django_redis import get_redis_connection
            conn = get_redis_connection('default')
            conn.delete('ha_manager_leader')
            conn.delete('ha_refresh_request')
        except Exception:
            pass
        cache.clear()

    @classmethod
    def tearDownClass(cls):
        # Clean up Redis locks after tests
        try:
            from django_redis import get_redis_connection
            conn = get_redis_connection('default')
            conn.delete('ha_manager_leader')
            conn.delete('ha_refresh_request')
        except Exception:
            pass
        super().tearDownClass()

    def setUp(self):
        cache.clear()

    def tearDown(self):
        NodeModel.objects.all().delete()
        cache.clear()

    def test_manager_init_with_nodes(self):
        """Test manager initialization with node list."""
        nodes = ["http://192.168.0.10:11434", "http://192.168.0.11:11434"]
        mgr = HAProxyManager(nodes=nodes)
        mgr._is_leader = True
        
        self.assertEqual(mgr.nodes, nodes)
        active_pool = cache.get(mgr.ACTIVE_POOL_KEY)
        self.assertEqual(active_pool, nodes)

    def test_refresh_from_db_loads_active_nodes(self):
        """Test refresh_from_db populates active pool from DB."""
        # Create nodes in DB
        n1 = NodeModel.objects.create(name="n1", address="192.168.0.10", port=11434, active=True)
        n2 = NodeModel.objects.create(name="n2", address="192.168.0.11", port=11434, active=False)

        mgr = HAProxyManager(nodes=[])
        mgr._is_leader = True
        mgr.refresh_from_db()

        active = cache.get(mgr.ACTIVE_POOL_KEY)
        standby = cache.get(mgr.STANDBY_POOL_KEY)
        
        self.assertIn("http://192.168.0.10:11434", active)
        self.assertIn("http://192.168.0.11:11434", standby)

    def test_choose_node_with_model_filter(self):
        """Test choose_node filters by model availability."""
        a = "http://192.168.0.10:11434"
        b = "http://192.168.0.11:11434"
        
        mgr = HAProxyManager(nodes=[a, b])
        mgr._is_leader = True
        cache.set(mgr.ACTIVE_POOL_KEY, [a, b])
        cache.set(mgr.MODELS_KEY_PREFIX + a, ["llama2:7b"])
        cache.set(mgr.MODELS_KEY_PREFIX + b, ["gemma3:270m-it-qat"])
        
        # Mock Redis to use cache fallback
        import sys
        import types
        fake_mod = types.ModuleType('django_redis')
        def fake_conn_factory(*args, **kwargs):
            raise Exception("force fallback")
        fake_mod.get_redis_connection = fake_conn_factory
        orig = sys.modules.get('django_redis')
        sys.modules['django_redis'] = fake_mod
        
        try:
            chosen = mgr.choose_node(model_name="gemma3:270m-it-qat", strategy="least_active")
            self.assertEqual(chosen, b)
        finally:
            if orig:
                sys.modules['django_redis'] = orig
            else:
                del sys.modules['django_redis']

    def test_get_address_for_node_id(self):
        """Test get_address_for_node_id retrieves correct address."""
        n = NodeModel.objects.create(name="test", address="ollama", port=11434, active=True)
        
        mgr = HAProxyManager(nodes=[])
        mgr._is_leader = True
        mgr.refresh_from_db()
        
        addr = mgr.get_address_for_node_id(n.id)
        self.assertEqual(addr, "http://ollama:11434")

    def test_acquire_and_release_node(self):
        """Test acquire_node increments count and release_node decrements."""
        a = "http://192.168.0.10:11434"
        cache.set(HAProxyManager.ACTIVE_POOL_KEY, [a])
        
        mgr = HAProxyManager(nodes=[a])
        mgr._is_leader = True
        
        # Mock Redis to use cache fallback
        import sys
        import types
        fake_mod = types.ModuleType('django_redis')
        def fake_conn_factory(*args, **kwargs):
            raise Exception("force fallback")
        fake_mod.get_redis_connection = fake_conn_factory
        orig = sys.modules.get('django_redis')
        sys.modules['django_redis'] = fake_mod
        
        try:
            # Acquire should increment count
            addr = mgr.acquire_node()
            self.assertEqual(addr, a)
            self.assertEqual(cache.get(mgr._active_count_key(a)), 1)
            
            # Release should decrement count
            mgr.release_node(a)
            self.assertEqual(cache.get(mgr._active_count_key(a)), 0)
        finally:
            if orig:
                sys.modules['django_redis'] = orig
            else:
                del sys.modules['django_redis']
