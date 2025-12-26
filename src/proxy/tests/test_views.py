from django.test import TestCase
from django.core.cache import cache
from rest_framework.test import APIClient
from unittest.mock import MagicMock, patch
import logging
from django.utils.crypto import get_random_string

# Mock manager at module level to prevent _get_manager blocking
import proxy.utils.proxy_manager as pm_module
_mock_manager = MagicMock()
_mock_manager.refresh_from_db = MagicMock()
_mock_manager._is_leader = False
_mock_manager.ACTIVE_POOL_KEY = "ha_active_pool"
_mock_manager.STANDBY_POOL_KEY = "ha_standby_pool"
_mock_manager.NODE_ID_MAP_KEY = "ha_node_id_map"
_mock_manager.LATENCY_KEY_PREFIX = "ha_latency:"
_mock_manager.MODELS_KEY_PREFIX = "ha_models:"
_mock_manager.ACTIVE_COUNT_KEY_PREFIX = "ha_active_count:"
_mock_manager._active_count_key = lambda addr: f"ha_active_count:{addr}"
pm_module._global_manager = _mock_manager

from proxy.models import node as NodeModel, ProxyConfig
from django.contrib.auth import get_user_model

User = get_user_model()


class ProxyViewsTests(TestCase):
    """Tests for proxy views API endpoints."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Clear Redis locks
        try:
            from django_redis import get_redis_connection
            conn = get_redis_connection('default')
            conn.delete('ha_manager_leader')
            conn.delete('ha_refresh_request')
        except Exception as e:
            logging.getLogger('proxy.tests').debug("setUpClass: redis cleanup failed: %s", e)
        cache.clear()

    @classmethod
    def tearDownClass(cls):
        try:
            from django_redis import get_redis_connection
            conn = get_redis_connection('default')
            conn.delete('ha_manager_leader')
            conn.delete('ha_refresh_request')
        except Exception as e:
            logging.getLogger('proxy.tests').debug("tearDownClass: redis cleanup failed: %s", e)
        super().tearDownClass()

    def setUp(self):
        self.client = APIClient()
        cache.clear()
        
        # Ensure CPU node exists (created by migration 0008)
        self.cpu_node, _ = NodeModel.objects.get_or_create(
            name='CPU',
            defaults={
                'address': 'ollama',
                'port': 11434,
                'active': True,
                'available_models': []
            }
        )
        
        # Mock _get_manager to return a working mock without blocking
        self.manager_patcher = patch('proxy.views._get_manager')
        mock_get_mgr = self.manager_patcher.start()
        
        # Create a mock manager with required attributes
        self.mock_mgr = MagicMock()
        self.mock_mgr.ACTIVE_POOL_KEY = "ha_active_pool"
        self.mock_mgr.STANDBY_POOL_KEY = "ha_standby_pool"
        self.mock_mgr.NODE_ID_MAP_KEY = "ha_node_id_map"
        self.mock_mgr.LATENCY_KEY_PREFIX = "ha_latency:"
        self.mock_mgr.MODELS_KEY_PREFIX = "ha_models:"
        self.mock_mgr.ACTIVE_COUNT_KEY_PREFIX = "ha_active_count:"
        self.mock_mgr._active_count_key = lambda addr: f"ha_active_count:{addr}"
        self.mock_mgr.refresh_from_db = MagicMock()
        
        mock_get_mgr.return_value = self.mock_mgr
        
        # Set up cache with CPU node in active pool
        cache.set(self.mock_mgr.ACTIVE_POOL_KEY, ["http://ollama:11434"])
        cache.set(self.mock_mgr.STANDBY_POOL_KEY, [])
        cache.set(self.mock_mgr.NODE_ID_MAP_KEY, {str(self.cpu_node.id): "http://ollama:11434"})

    def tearDown(self):
        self.manager_patcher.stop()
        cache.clear()
        NodeModel.objects.all().delete()

    def test_health_endpoint_with_active_nodes(self):
        """Test /api/proxy health endpoint returns success when nodes are active."""
        cache.set(self.mock_mgr.ACTIVE_POOL_KEY, ["http://ollama:11434"])
        
        response = self.client.get('/api/proxy')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "Ollama is running")

    def test_health_endpoint_without_active_nodes(self):
        """Test /api/proxy health endpoint returns 404 when no active nodes."""
        cache.set(self.mock_mgr.ACTIVE_POOL_KEY, [])
        
        response = self.client.get('/api/proxy')
        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.json())

    def test_state_endpoint_returns_manager_state(self):
        """Test /api/proxy/state returns cache state."""
        # Set up cache state
        cache.set(self.mock_mgr.ACTIVE_POOL_KEY, ["http://ollama:11434"])
        cache.set(self.mock_mgr.STANDBY_POOL_KEY, [])
        cache.set(self.mock_mgr.LATENCY_KEY_PREFIX + "http://ollama:11434", 0.05)
        cache.set(self.mock_mgr.MODELS_KEY_PREFIX + "http://ollama:11434", ["gemma3:270m-it-qat"])
        
        response = self.client.get('/api/proxy/state')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("active", data)
        self.assertIn("standby", data)
        self.assertIn("http://ollama:11434", data["active"])

    def test_active_requests_endpoint(self):
        """Test /api/proxy/active-requests returns node info."""
        cache.set(self.mock_mgr.ACTIVE_POOL_KEY, ["http://ollama:11434"])
        cache.set(self.mock_mgr.NODE_ID_MAP_KEY, {str(self.cpu_node.id): "http://ollama:11434"})
        
        response = self.client.get('/api/proxy/active-requests')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("nodes", data)
        self.assertIn("total_active_requests", data)
        self.assertEqual(len(data["nodes"]), 1)
        self.assertEqual(data["nodes"][0]["name"], "CPU")

    def test_active_requests_filter_by_node_id(self):
        """Test /api/proxy/active-requests?node_id=X filters correctly."""
        response = self.client.get(f'/api/proxy/active-requests?node_id={self.cpu_node.id}')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(len(data["nodes"]), 1)
        self.assertEqual(data["nodes"][0]["id"], self.cpu_node.id)

    def test_proxy_config_get(self):
        """Test GET /api/proxy/config returns config."""
        # Create test user for authentication
        test_pw = get_random_string(12)
        user = User.objects.create_user(username='testuser', password=test_pw)
        self.client.force_authenticate(user=user)
        
        response = self.client.get('/api/proxy/config')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("strategy", data)
        self.assertEqual(data["strategy"], "least_active")

    def test_proxy_config_update(self):
        """Test PUT /api/proxy/config updates strategy."""
        test_pw = get_random_string(12)
        user = User.objects.create_user(username='testuser', password=test_pw)
        self.client.force_authenticate(user=user)
        
        response = self.client.put(
            '/api/proxy/config',
            {'strategy': 'lowest_latency'},
            format='json'
        )
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data["strategy"], "lowest_latency")
        
        # Verify in DB
        cfg = ProxyConfig.objects.first()
        self.assertEqual(cfg.strategy, "lowest_latency")

    def test_pull_model_to_cpu_node_real(self):
        """Test /api/proxy/pull actually pulls gemma3:270m-it-qat to CPU node (REAL HTTP REQUEST)."""
        # This test makes a real HTTP request to ollama container
        # It will take time to download the model
        
        payload = {
            'model': 'gemma3:270m-it-qat',
            'node_id': self.cpu_node.id,
            'stream': False
        }
        
        response = self.client.post('/api/proxy/pull', payload, format='json')
        
        # Should return 200 with results
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("results", data)
        self.assertIn("model", data)
        self.assertEqual(data["model"], "gemma3:270m-it-qat")
        self.assertEqual(len(data["results"]), 1)
        
        # Verify pull was successful
        result = data["results"][0]
        self.assertEqual(result["node_id"], self.cpu_node.id)
        self.assertEqual(result["node_name"], "CPU")
        self.assertEqual(result["status"], "success")

    def test_pull_model_to_all_active_nodes(self):
        """Test /api/proxy/pull without node_id pulls to all active nodes."""
        payload = {
            'model': 'gemma3:270m-it-qat',
            'stream': False
        }
        
        response = self.client.post('/api/proxy/pull', payload, format='json')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("results", data)
        # Should have pulled to CPU node (the only active one)
        self.assertEqual(len(data["results"]), 1)

    def test_pull_embedding_model_to_cpu_node(self):
        """Test /api/proxy/pull actually pulls embeddinggemma:300m-qat-q4_0 to CPU node (REAL HTTP REQUEST)."""
        # This test makes a real HTTP request to ollama container
        # It will take time to download the model
        
        payload = {
            'model': 'embeddinggemma:300m-qat-q4_0',
            'node_id': self.cpu_node.id,
            'stream': False
        }
        
        response = self.client.post('/api/proxy/pull', payload, format='json')
        
        # Should return 200 with results
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("results", data)
        self.assertIn("model", data)
        self.assertEqual(data["model"], "embeddinggemma:300m-qat-q4_0")
        self.assertEqual(len(data["results"]), 1)
        
        # Verify pull was successful
        result = data["results"][0]
        self.assertEqual(result["node_id"], self.cpu_node.id)
        self.assertEqual(result["node_name"], "CPU")
        self.assertEqual(result["status"], "success")

    def test_pull_model_missing_model_name(self):
        """Test /api/proxy/pull returns 400 when model name is missing."""
        response = self.client.post('/api/proxy/pull', {}, format='json')
        self.assertEqual(response.status_code, 400)
        
        data = response.json()
        self.assertIn("error", data)
        self.assertIn("model", data["error"].lower())

    def test_pull_model_invalid_node_id(self):
        """Test /api/proxy/pull returns 404 for invalid node_id."""
        payload = {
            'model': 'gemma3:270m-it-qat',
            'node_id': 99999  # Non-existent node
        }
        
        response = self.client.post('/api/proxy/pull', payload, format='json')
        self.assertEqual(response.status_code, 404)
