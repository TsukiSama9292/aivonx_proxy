"""
Tests for HAProxyManager class.
"""
import asyncio
from unittest.mock import AsyncMock, patch
from django.test import TransactionTestCase
from django.core.cache import cache
from proxy.utils.proxy_manager import HAProxyManager, init_global_manager_from_db
from proxy.models import node, ProxyConfig
from .conftest import ProxyTestMixin


class TestHAProxyManager(TransactionTestCase, ProxyTestMixin):
    """Test HAProxyManager functionality."""

    def setUp(self):
        super().setUp()
        cache.clear()

    def tearDown(self):
        cache.clear()
        super().tearDown()

    def test_manager_initialization(self):
        """Test manager initializes with nodes."""
        nodes = ["http://192.168.0.54:11434", "http://192.168.0.55:11434"]
        mgr = HAProxyManager(nodes=nodes)
        
        self.assertEqual(mgr.nodes, nodes)
        self.assertEqual(cache.get(mgr.ACTIVE_POOL_KEY), nodes)
        self.assertEqual(cache.get(mgr.STANDBY_POOL_KEY), [])

    def test_manager_initialization_empty(self):
        """Test manager initializes with empty nodes."""
        mgr = HAProxyManager(nodes=[])
        
        self.assertEqual(mgr.nodes, [])
        self.assertEqual(cache.get(mgr.ACTIVE_POOL_KEY), [])

    def test_refresh_from_db(self):
        """Test refresh_from_db loads nodes from database."""
        self.create_sample_nodes()
        mgr = HAProxyManager(nodes=[])
        mgr.refresh_from_db()
        
        self.assertEqual(len(mgr.nodes), 3)
        self.assertIsNotNone(cache.get(mgr.ACTIVE_POOL_KEY))
        self.assertEqual(len(cache.get(mgr.ACTIVE_POOL_KEY)), 3)

    def test_refresh_from_db_filters_inactive(self):
        """Test refresh_from_db excludes inactive nodes."""
        self.create_sample_nodes()
        inactive = self.create_inactive_node()
        mgr = HAProxyManager(nodes=[])
        mgr.refresh_from_db()
        
        # Should only have active nodes
        self.assertEqual(len(mgr.nodes), 3)
        # Inactive node should not be in the list
        inactive_addr = f"http://{inactive.address}:{inactive.port}"
        self.assertNotIn(inactive_addr, mgr.nodes)

    def test_choose_node_least_active(self):
        """Test choose_node with least_active strategy."""
        nodes = ["http://192.168.0.54:11434", "http://192.168.0.55:11434"]
        mgr = HAProxyManager(nodes=nodes)
        cache.set(mgr.ACTIVE_POOL_KEY, nodes)
        cache.set(mgr.MODELS_KEY_PREFIX + nodes[0], ["llama2:7b"])
        cache.set(mgr.MODELS_KEY_PREFIX + nodes[1], ["llama2:7b"])
        
        # Set different active counts
        cache.set(mgr._active_count_key(nodes[0]), 5)
        cache.set(mgr._active_count_key(nodes[1]), 2)
        
        chosen = mgr.choose_node(model_name="llama2:7b", strategy="least_active")
        
        # Should choose node with lower active count
        self.assertEqual(chosen, nodes[1])

    def test_choose_node_lowest_latency(self):
        """Test choose_node with lowest_latency strategy."""
        nodes = ["http://192.168.0.54:11434", "http://192.168.0.55:11434"]
        mgr = HAProxyManager(nodes=nodes)
        cache.set(mgr.ACTIVE_POOL_KEY, nodes)
        cache.set(mgr.MODELS_KEY_PREFIX + nodes[0], ["llama2:7b"])
        cache.set(mgr.MODELS_KEY_PREFIX + nodes[1], ["llama2:7b"])
        
        # Set different latencies
        cache.set(mgr.LATENCY_KEY_PREFIX + nodes[0], 0.1)
        cache.set(mgr.LATENCY_KEY_PREFIX + nodes[1], 0.05)
        
        chosen = mgr.choose_node(model_name="llama2:7b", strategy="lowest_latency")
        
        # Should choose node with lower latency
        self.assertEqual(chosen, nodes[1])

    def test_choose_node_filters_by_model(self):
        """Test choose_node only selects nodes with the requested model."""
        nodes = ["http://192.168.0.54:11434", "http://192.168.0.55:11434"]
        mgr = HAProxyManager(nodes=nodes)
        cache.set(mgr.ACTIVE_POOL_KEY, nodes)
        # First node has llama2, second has codellama
        cache.set(mgr.MODELS_KEY_PREFIX + nodes[0], ["llama2:7b"])
        cache.set(mgr.MODELS_KEY_PREFIX + nodes[1], ["codellama:13b"])
        
        chosen = mgr.choose_node(model_name="llama2:7b")
        
        self.assertEqual(chosen, nodes[0])

    def test_choose_node_returns_none_when_model_unavailable(self):
        """Test choose_node returns None when model is not available."""
        nodes = ["http://192.168.0.54:11434"]
        mgr = HAProxyManager(nodes=nodes)
        cache.set(mgr.ACTIVE_POOL_KEY, nodes)
        cache.set(mgr.MODELS_KEY_PREFIX + nodes[0], ["codellama:13b"])
        
        chosen = mgr.choose_node(model_name="nonexistent:7b")
        
        self.assertIsNone(chosen)

    def test_acquire_and_release_node(self):
        """Test acquire_node increments and release_node decrements count."""
        nodes = ["http://192.168.0.54:11434"]
        mgr = HAProxyManager(nodes=nodes)
        cache.set(mgr.ACTIVE_POOL_KEY, nodes)
        
        # Initial count should be 0
        self.assertEqual(cache.get(mgr._active_count_key(nodes[0]), 0), 0)
        
        # Acquire node
        addr = mgr.acquire_node()
        self.assertEqual(addr, nodes[0])
        self.assertEqual(cache.get(mgr._active_count_key(nodes[0])), 1)
        
        # Release node
        mgr.release_node(addr)
        self.assertEqual(cache.get(mgr._active_count_key(nodes[0])), 0)

    def test_release_node_does_not_go_negative(self):
        """Test release_node does not allow negative counts."""
        nodes = ["http://192.168.0.54:11434"]
        mgr = HAProxyManager(nodes=nodes)
        
        # Release without acquire
        mgr.release_node(nodes[0])
        
        self.assertEqual(cache.get(mgr._active_count_key(nodes[0]), 0), 0)

    def test_start_scheduler(self):
        """Test scheduler starts and jobs are added."""
        mgr = HAProxyManager(nodes=[])
        
        mgr.start_scheduler(interval_minutes=1)
        
        self.assertIsNotNone(mgr._scheduler)
        self.assertTrue(mgr._scheduler.running)
        
        # Cleanup
        mgr._scheduler.shutdown(wait=False)

    def test_get_address_for_node_id(self):
        """Test get_address_for_node_id returns correct address."""
        sample_node = self.create_sample_node()
        mgr = HAProxyManager(nodes=[])
        expected_addr = f"http://{sample_node.address}:{sample_node.port}"
        cache.set(mgr.NODE_ID_MAP_KEY, {str(sample_node.pk): expected_addr})
        
        addr = mgr.get_address_for_node_id(sample_node.pk)
        
        self.assertEqual(addr, expected_addr)

    def test_acquire_node_by_id(self):
        """Test acquire_node_by_id with valid node id."""
        sample_node = self.create_sample_node()
        mgr = HAProxyManager(nodes=[])
        expected_addr = f"http://{sample_node.address}:{sample_node.port}"
        cache.set(mgr.NODE_ID_MAP_KEY, {str(sample_node.pk): expected_addr})
        cache.set(mgr.ACTIVE_POOL_KEY, [expected_addr])
        
        addr = mgr.acquire_node_by_id(sample_node.pk)
        
        self.assertEqual(addr, expected_addr)
        self.assertEqual(cache.get(mgr._active_count_key(expected_addr)), 1)


class TestManagerInitialization(TransactionTestCase, ProxyTestMixin):
    """Test manager initialization functions."""

    def setUp(self):
        super().setUp()
        cache.clear()
        # Clear global manager before each test
        import proxy.utils.proxy_manager as pm
        pm._global_manager = None

    def tearDown(self):
        cache.clear()
        super().tearDown()

    def test_init_global_manager_from_db(self):
        """Test init_global_manager_from_db creates manager."""
        self.create_sample_nodes()
        mgr = init_global_manager_from_db()
        
        self.assertIsNotNone(mgr)
        self.assertGreater(len(mgr.nodes), 0)
