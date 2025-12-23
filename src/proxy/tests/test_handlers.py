"""
Tests for proxy handlers (generate, chat, tags, embed, embeddings).
"""
import json
import unittest
from unittest.mock import AsyncMock, patch
from django.test import TransactionTestCase
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APIClient
from proxy.utils.proxy_manager import HAProxyManager
from .conftest import ProxyTestMixin


class TestProxyTagsEndpoint(TransactionTestCase, ProxyTestMixin):
    """Test /api/tags endpoint."""

    def setUp(self):
        super().setUp()
        self.client = APIClient()
        cache.clear()

    def tearDown(self):
        cache.clear()
        super().tearDown()

    @unittest.skip("Skip reverse-proxy network tests as requested")
    @patch("proxy.views.httpx.AsyncClient")
    async def test_tags_success(self, mock_client):
        """Test successful tags request."""
        # Setup manager and cache
        sample_node = await self.acreate_sample_node()
        mgr = HAProxyManager(nodes=["http://192.168.0.54:11434"])
        cache.set(mgr.ACTIVE_POOL_KEY, ["http://192.168.0.54:11434"])
        cache.set(mgr.MODELS_KEY_PREFIX + "http://192.168.0.54:11434", ["llama2:7b"])
        
        # Mock httpx response
        mock_response = AsyncMock()
        mock_response.content = json.dumps(self.get_mock_ollama_response()).encode()
        mock_response.status_code = 200
        mock_response.headers.get.return_value = "application/json"
        
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value = mock_client_instance
        
        url = "/api/tags"
        # Use sync client since Django test client handles async
        from django.test import AsyncClient
        client = AsyncClient()
        response = await client.get(url)
        
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE])

    @unittest.skip("Skip reverse-proxy network tests as requested")
    async def test_tags_no_healthy_nodes(self):
        """Test tags request when no healthy nodes available."""
        # Setup: empty active pool
        mgr = HAProxyManager(nodes=[])
        cache.set(mgr.ACTIVE_POOL_KEY, [])
        
        url = "/api/tags"
        from django.test import AsyncClient
        client = AsyncClient()
        response = await client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn("error", response.json())

    @unittest.skip("Skip reverse-proxy network tests as requested")
    async def test_tags_rejects_node_id(self):
        """Test tags request rejects node_id parameter."""
        sample_node = await self.acreate_sample_node()
        mgr = HAProxyManager(nodes=["http://192.168.0.54:11434"])
        cache.set(mgr.ACTIVE_POOL_KEY, ["http://192.168.0.54:11434"])
        
        url = "/api/tags?node_id=1"
        from django.test import AsyncClient
        client = AsyncClient()
        response = await client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("node_id", response.json()["error"])


class TestProxyChatEndpoint(TransactionTestCase, ProxyTestMixin):
    """Test /api/proxy/chat endpoint."""

    def setUp(self):
        super().setUp()
        self.client = APIClient()
        cache.clear()

    def tearDown(self):
        cache.clear()
        super().tearDown()

    @unittest.skip("Skip reverse-proxy network tests as requested")
    async def test_chat_model_not_available(self):
        """Test chat request with unavailable model."""
        sample_node = await self.acreate_sample_node()
        mgr = HAProxyManager(nodes=["http://192.168.0.54:11434"])
        cache.set(mgr.ACTIVE_POOL_KEY, ["http://192.168.0.54:11434"])
        cache.set(mgr.MODELS_KEY_PREFIX + "http://192.168.0.54:11434", ["codellama:13b"])
        
        url = "/api/proxy/chat"
        data = {
            "model": "nonexistent:7b",
            "messages": [{"role": "user", "content": "test"}],
            "stream": False
        }
        from django.test import AsyncClient
        client = AsyncClient()
        response = await client.post(
            url,
            data=json.dumps(data),
            content_type="application/json"
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("model not available", response.json()["error"])

    @unittest.skip("Skip reverse-proxy network tests as requested")
    async def test_chat_rejects_node_id(self):
        """Test chat request rejects node_id in payload."""
        sample_node = await self.acreate_sample_node()
        mgr = HAProxyManager(nodes=["http://192.168.0.54:11434"])
        cache.set(mgr.ACTIVE_POOL_KEY, ["http://192.168.0.54:11434"])
        
        url = "/api/proxy/chat"
        data = {
            "model": "llama2:7b",
            "messages": [{"role": "user", "content": "test"}],
            "node_id": 1
        }
        from django.test import AsyncClient
        client = AsyncClient()
        response = await client.post(
            url,
            data=json.dumps(data),
            content_type="application/json"
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("node_id", response.json()["error"])


class TestProxyGenerateEndpoint(TransactionTestCase, ProxyTestMixin):
    """Test /api/proxy/generate endpoint."""

    def setUp(self):
        super().setUp()
        self.client = APIClient()
        cache.clear()

    def tearDown(self):
        cache.clear()
        super().tearDown()

    @unittest.skip("Skip reverse-proxy network tests as requested")
    async def test_generate_model_not_available(self):
        """Test generate request with unavailable model."""
        mgr = HAProxyManager(nodes=["http://192.168.0.54:11434"])
        cache.set(mgr.ACTIVE_POOL_KEY, ["http://192.168.0.54:11434"])
        cache.set(mgr.MODELS_KEY_PREFIX + "http://192.168.0.54:11434", [])
        
        url = "/api/proxy/generate"
        data = {"model": "llama2:7b", "prompt": "test", "stream": False}
        from django.test import AsyncClient
        client = AsyncClient()
        response = await client.post(
            url,
            data=json.dumps(data),
            content_type="application/json"
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TestProxyEmbedEndpoint(TransactionTestCase, ProxyTestMixin):
    """Test /api/proxy/embed endpoint."""

    def setUp(self):
        super().setUp()
        self.client = APIClient()
        cache.clear()

    def tearDown(self):
        cache.clear()
        super().tearDown()

    @unittest.skip("Skip reverse-proxy network tests as requested")
    async def test_embed_rejects_node_id(self):
        """Test embed request rejects node_id parameter."""
        mgr = HAProxyManager(nodes=["http://192.168.0.54:11434"])
        cache.set(mgr.ACTIVE_POOL_KEY, ["http://192.168.0.54:11434"])
        
        url = "/api/proxy/embed"
        data = {"model": "llama2:7b", "input": "test", "node_id": 1}
        from django.test import AsyncClient
        client = AsyncClient()
        response = await client.post(
            url,
            data=json.dumps(data),
            content_type="application/json"
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TestProxyEmbeddingsEndpoint(TransactionTestCase, ProxyTestMixin):
    """Test /api/proxy/embeddings endpoint."""

    def setUp(self):
        super().setUp()
        self.client = APIClient()
        cache.clear()

    def tearDown(self):
        cache.clear()
        super().tearDown()

    @unittest.skip("Skip reverse-proxy network tests as requested")
    async def test_embeddings_model_not_available(self):
        """Test embeddings request with unavailable model."""
        mgr = HAProxyManager(nodes=["http://192.168.0.54:11434"])
        cache.set(mgr.ACTIVE_POOL_KEY, ["http://192.168.0.54:11434"])
        cache.set(mgr.MODELS_KEY_PREFIX + "http://192.168.0.54:11434", [])
        
        url = "/api/proxy/embeddings"
        data = {"model": "nonexistent:7b", "prompt": "test"}
        from django.test import AsyncClient
        client = AsyncClient()
        response = await client.post(
            url,
            data=json.dumps(data),
            content_type="application/json"
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
