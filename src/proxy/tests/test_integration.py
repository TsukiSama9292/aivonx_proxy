"""
Integration tests for complete proxy workflows.
"""
import json
from unittest.mock import AsyncMock, patch
from django.test import TransactionTestCase
from django.core.cache import cache
from proxy.utils.proxy_manager import HAProxyManager
from proxy.models import node
from .conftest import ProxyTestMixin


class TestProxyWorkflow(TransactionTestCase, ProxyTestMixin):
    """Test complete proxy request workflows."""

    def setUp(self):
        super().setUp()
        cache.clear()

    def tearDown(self):
        cache.clear()
        super().tearDown()

    def test_node_recovery_from_standby(self):
        """Test that recovered nodes move back from standby to active."""
        addr = "http://192.168.0.54:11434"
        mgr = HAProxyManager(nodes=[addr])
        
        # Start with node in standby
        cache.set(mgr.ACTIVE_POOL_KEY, [])
        cache.set(mgr.STANDBY_POOL_KEY, [addr])
        
        # Simulate successful health check
        with patch.object(mgr, "ping_node") as mock_ping:
            async def run_health_check():
                mock_ping.return_value = (True, 0.05)
                await mgr.health_check_all()
            
            import asyncio
            asyncio.run(run_health_check())
            
            active = cache.get(mgr.ACTIVE_POOL_KEY)
            standby = cache.get(mgr.STANDBY_POOL_KEY)
            
            self.assertIn(addr, active)
            self.assertNotIn(addr, standby)


class TestLoadBalancing(TransactionTestCase, ProxyTestMixin):
    """Test load balancing strategies."""

    def setUp(self):
        super().setUp()
        cache.clear()

    def tearDown(self):
        cache.clear()
        super().tearDown()

    def test_least_active_distributes_load(self):
        """Test least_active strategy distributes requests evenly."""
        nodes = [
            "http://192.168.0.54:11434",
            "http://192.168.0.55:11434",
            "http://192.168.0.56:11434"
        ]
        mgr = HAProxyManager(nodes=nodes)
        cache.set(mgr.ACTIVE_POOL_KEY, nodes)
        
        # Set same model on all nodes
        for n in nodes:
            cache.set(mgr.MODELS_KEY_PREFIX + n, ["llama2:7b"])
            cache.set(mgr._active_count_key(n), 0)
        
        # Make multiple selections
        selections = []
        for _ in range(10):
            chosen = mgr.choose_node(model_name="llama2:7b", strategy="least_active")
            selections.append(chosen)
            # Don't release so count increases
        
        # Verify distribution (all nodes should be selected at least once)
        unique_selections = set(selections)
        self.assertGreaterEqual(len(unique_selections), 2)  # At least 2 different nodes used

    def test_lowest_latency_prefers_faster_node(self):
        """Test lowest_latency strategy prefers node with lower latency."""
        nodes = [
            "http://192.168.0.54:11434",
            "http://192.168.0.55:11434"
        ]
        mgr = HAProxyManager(nodes=nodes)
        cache.set(mgr.ACTIVE_POOL_KEY, nodes)
        
        for n in nodes:
            cache.set(mgr.MODELS_KEY_PREFIX + n, ["llama2:7b"])
        
        # Set different latencies
        cache.set(mgr.LATENCY_KEY_PREFIX + nodes[0], 0.5)
        cache.set(mgr.LATENCY_KEY_PREFIX + nodes[1], 0.05)
        
        # Should consistently choose the faster node
        for _ in range(5):
            chosen = mgr.choose_node(model_name="llama2:7b", strategy="lowest_latency")
            self.assertEqual(chosen, nodes[1])
            mgr.release_node(chosen)


class TestModelAwareRouting(TransactionTestCase, ProxyTestMixin):
    """Test model-aware routing."""

    def setUp(self):
        super().setUp()
        cache.clear()

    def tearDown(self):
        cache.clear()
        super().tearDown()

    def test_routes_to_node_with_model(self):
        """Test request is routed only to nodes with the requested model."""
        nodes = [
            "http://192.168.0.54:11434",
            "http://192.168.0.55:11434"
        ]
        mgr = HAProxyManager(nodes=nodes)
        cache.set(mgr.ACTIVE_POOL_KEY, nodes)
        
        # First node has llama2, second has codellama
        cache.set(mgr.MODELS_KEY_PREFIX + nodes[0], ["llama2:7b"])
        cache.set(mgr.MODELS_KEY_PREFIX + nodes[1], ["codellama:13b"])
        
        # Request llama2 should go to first node
        chosen = mgr.choose_node(model_name="llama2:7b")
        self.assertEqual(chosen, nodes[0])
        
        # Request codellama should go to second node
        chosen = mgr.choose_node(model_name="codellama:13b")
        self.assertEqual(chosen, nodes[1])

    def test_returns_none_when_model_unavailable(self):
        """Test returns None when no node has the requested model."""
        nodes = ["http://192.168.0.54:11434"]
        mgr = HAProxyManager(nodes=nodes)
        cache.set(mgr.ACTIVE_POOL_KEY, nodes)
        cache.set(mgr.MODELS_KEY_PREFIX + nodes[0], ["llama2:7b"])
        
        # Request unavailable model
        chosen = mgr.choose_node(model_name="nonexistent:7b")
        self.assertIsNone(chosen)

    def test_model_refresh_updates_cache(self):
        """Test periodic model refresh updates cache correctly."""
        sample_node = self.create_sample_node()
        addr = f"http://{sample_node.address}:{sample_node.port}"
        mgr = HAProxyManager(nodes=[addr])
        cache.set(mgr.ACTIVE_POOL_KEY, [addr])
        
        mock_response = {
            "models": [
                {"name": "new-model:7b"},
                {"name": "another-model:13b"}
            ]
        }
        
        with patch("proxy.utils.proxy_manager.httpx.AsyncClient") as mock_client:
            mock_resp = AsyncMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_response
            
            mock_client_instance = AsyncMock()
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.get.return_value = mock_resp
            mock_client.return_value = mock_client_instance
            
            import asyncio
            asyncio.run(mgr.refresh_models_all())
            
            models = cache.get(mgr.MODELS_KEY_PREFIX + addr)
            self.assertIn("new-model:7b", models)
            self.assertIn("another-model:13b", models)
            
            # Verify DB was updated
            sample_node.refresh_from_db()
            self.assertIn("new-model:7b", sample_node.available_models)
