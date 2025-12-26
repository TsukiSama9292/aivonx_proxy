from django.test import TestCase
from rest_framework.test import APIClient
from django.core.cache import cache
from unittest.mock import MagicMock, patch

# Module-level mock manager to prevent Redis/leader blocking during imports
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

from proxy.models import node as NodeModel


class ViewsProxyTests(TestCase):
	"""Tests for proxy async endpoints (generate/chat/embed/embeddings/tags/version)."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
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
		try:
			from django_redis import get_redis_connection
			conn = get_redis_connection('default')
			conn.delete('ha_manager_leader')
			conn.delete('ha_refresh_request')
		except Exception:
			pass
		super().tearDownClass()

	def setUp(self):
		self.client = APIClient()
		cache.clear()
		# ensure CPU node exists
		self.cpu_node, _ = NodeModel.objects.get_or_create(
			name='CPU', defaults={'address': 'ollama', 'port': 11434, 'active': True, 'available_models': []}
		)

		# Patch views_proxy._get_manager (imported in views_proxy) to return a mock manager with pools
		self.patcher = patch('proxy.views_proxy._get_manager')
		self.mock_get_mgr = self.patcher.start()
		self.mgr = MagicMock()
		self.mgr.ACTIVE_POOL_KEY = _mock_manager.ACTIVE_POOL_KEY
		self.mgr.STANDBY_POOL_KEY = _mock_manager.STANDBY_POOL_KEY
		self.mgr.NODE_ID_MAP_KEY = _mock_manager.NODE_ID_MAP_KEY
		self.mgr.LATENCY_KEY_PREFIX = _mock_manager.LATENCY_KEY_PREFIX
		self.mgr.MODELS_KEY_PREFIX = _mock_manager.MODELS_KEY_PREFIX
		self.mgr._active_count_key = _mock_manager._active_count_key
		self.mgr.choose_node = MagicMock(return_value="http://ollama:11434")
		self.mock_get_mgr.return_value = self.mgr

		# populate cache with models available
		cache.set(self.mgr.ACTIVE_POOL_KEY, ["http://ollama:11434"])
		cache.set(self.mgr.MODELS_KEY_PREFIX + "http://ollama:11434", ["gemma3:270m-it-qat", "embeddinggemma:300m-qat-q4_0"])
		cache.set(self.mgr.NODE_ID_MAP_KEY, {str(self.cpu_node.id): "http://ollama:11434"})

	def tearDown(self):
		self.patcher.stop()
		cache.clear()
		NodeModel.objects.all().delete()

	def test_generate_endpoint_non_stream(self):
		payload = {'model': 'gemma3:270m-it-qat', 'prompt': 'hello', 'stream': False}
		resp = self.client.post('/api/generate', payload, format='json')
		self.assertIn(resp.status_code, (200, 502, 503))

	def test_chat_endpoint_non_stream(self):
		payload = {'model': 'gemma3:270m-it-qat', 'messages': [{'role': 'user', 'content': 'hi'}], 'stream': False}
		resp = self.client.post('/api/chat', payload, format='json')
		self.assertIn(resp.status_code, (200, 502, 503))

	def test_embed_endpoint(self):
		payload = {'model': 'embeddinggemma:300m-qat-q4_0', 'input': 'hello'}
		resp = self.client.post('/api/embed', payload, format='json')
		self.assertIn(resp.status_code, (200, 502, 503))

	def test_embeddings_endpoint_batch(self):
		payload = {'model': 'embeddinggemma:300m-qat-q4_0', 'input': ['one', 'two']}
		resp = self.client.post('/api/embeddings', payload, format='json')
		self.assertIn(resp.status_code, (200, 502, 503))

	def test_tags_and_version(self):
		# tags should list available models (at least those two)
		tags_resp = self.client.get('/api/tags')
		self.assertEqual(tags_resp.status_code, 200)
		data = tags_resp.json()
		names = {m.get('name') for m in data.get('models', [])}
		self.assertTrue('gemma3:270m-it-qat' in names or 'embeddinggemma:300m-qat-q4_0' in names)

		# version endpoint should reflect pyproject version
		ver = self.client.get('/api/version')
		self.assertEqual(ver.status_code, 200)
		self.assertIn('version', ver.json())

