"""
Tests for proxy health and state endpoints.
"""
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APIClient
from proxy.utils.proxy_manager import HAProxyManager
from .conftest import BaseTestCase, ProxyTestMixin


class TestHealthEndpoint(BaseTestCase, ProxyTestMixin):
    """Test health check endpoint."""

    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def test_health_with_active_nodes(self):
        """Test health check when nodes are available."""
        # Setup: manually populate cache with active nodes
        sample_node = self.create_sample_node()
        mgr = HAProxyManager(nodes=["http://192.168.0.54:11434"])
        cache.set(mgr.ACTIVE_POOL_KEY, ["http://192.168.0.54:11434"])
        
        url = "/api/proxy"
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content.decode(), "Ollama is running")

    def test_health_without_active_nodes(self):
        """Test health check when no nodes are available."""
        # Setup: ensure cache is empty
        mgr = HAProxyManager(nodes=[])
        cache.set(mgr.ACTIVE_POOL_KEY, [])
        
        url = "/api/proxy"
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("error", response.json())

    def test_health_unauthenticated_access(self):
        """Test health check does not require authentication."""
        url = "/api/proxy"
        response = self.client.get(url)
        
        # Should not return 401 Unauthorized
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])


class TestStateEndpoint(BaseTestCase, ProxyTestMixin):
    """Test state diagnostics endpoint."""

    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def test_state_with_populated_cache(self):
        """Test state endpoint with populated cache."""
        # Setup: populate cache
        self.create_sample_nodes()
        mgr = HAProxyManager(nodes=[])
        addresses = [f"http://192.168.0.{50+i}:11434" for i in range(3)]
        cache.set(mgr.ACTIVE_POOL_KEY, addresses)
        cache.set(mgr.STANDBY_POOL_KEY, [])
        cache.set(mgr.NODE_ID_MAP_KEY, {str(i): addr for i, addr in enumerate(addresses)})
        
        for addr in addresses:
            cache.set(mgr.LATENCY_KEY_PREFIX + addr, 0.05)
            cache.set(mgr.MODELS_KEY_PREFIX + addr, ["llama2:7b"])
        
        url = "/api/proxy/state"
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("active", data)
        self.assertIn("standby", data)
        self.assertIn("models", data)
        self.assertIn("latencies", data)
        self.assertIn("active_counts", data)
        self.assertEqual(len(data["active"]), 3)

    def test_state_with_empty_cache(self):
        """Test state endpoint with empty cache triggers DB refresh."""
        self.create_sample_node()
        cache.clear()
        
        url = "/api/proxy/state"
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        # After refresh from DB, should have nodes
        self.assertIn("active", data)

    def test_state_unauthenticated_access(self):
        """Test state endpoint does not require authentication."""
        url = "/api/proxy/state"
        response = self.client.get(url)
        
        # Should not return 401 Unauthorized
        self.assertEqual(response.status_code, status.HTTP_200_OK)
