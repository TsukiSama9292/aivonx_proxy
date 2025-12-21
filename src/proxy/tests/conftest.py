"""
Base test utilities and mixins for Django tests.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient
from proxy.models import node, ProxyConfig
from asgiref.sync import sync_to_async

User = get_user_model()


class BaseTestCase(TestCase):
    """Base test case with cache cleanup."""

    def setUp(self):
        """Clear cache before each test."""
        super().setUp()
        cache.clear()

    def tearDown(self):
        """Clear cache after each test."""
        cache.clear()
        super().tearDown()


class AuthenticatedTestCase(BaseTestCase):
    """Base test case with authenticated API client."""

    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123"
        )
        self.client.force_authenticate(user=self.user)


class ProxyTestMixin:
    """Mixin providing common test data for proxy tests."""

    def create_sample_node(self):
        """Create a sample node for testing (sync version)."""
        return node.objects.create(
            name="test-node-1",
            address="192.168.0.54",
            port=11434,
            active=True,
            available_models=["llama2:7b", "codellama:13b"]
        )

    async def acreate_sample_node(self):
        """Create a sample node for testing (async version)."""
        return await sync_to_async(node.objects.create)(
            name="test-node-1",
            address="192.168.0.54",
            port=11434,
            active=True,
            available_models=["llama2:7b", "codellama:13b"]
        )

    def create_sample_nodes(self, count=3):
        """Create multiple sample nodes for testing (sync version)."""
        nodes = []
        for i in range(count):
            n = node.objects.create(
                name=f"test-node-{i}",
                address=f"192.168.0.{50+i}",
                port=11434,
                active=True,
                available_models=["llama2:7b", "codellama:13b"]
            )
            nodes.append(n)
        return nodes

    def create_inactive_node(self):
        """Create an inactive node for testing (sync version)."""
        return node.objects.create(
            name="inactive-node",
            address="192.168.0.99",
            port=11434,
            active=False,
            available_models=[]
        )

    # NodeGroup feature removed — no helper provided

    def create_proxy_config(self):
        """Create a ProxyConfig instance."""
        return ProxyConfig.objects.create(
            strategy=ProxyConfig.STRATEGY_LEAST_ACTIVE
        )

    @staticmethod
    def get_mock_ollama_response():
        """Mock Ollama API response for tags."""
        return {
            "models": [
                {
                    "name": "llama2:7b",
                    "modified_at": "2023-12-01T12:00:00Z",
                    "size": 3826793677
                },
                {
                    "name": "codellama:13b",
                    "modified_at": "2023-12-01T12:00:00Z",
                    "size": 7365960935
                }
            ]
        }

    @staticmethod
    def get_mock_chat_request():
        """Mock chat request payload."""
        return {
            "model": "llama2:7b",
            "messages": [
                {
                    "role": "user",
                    "content": "Hello, how are you?"
                }
            ],
            "stream": False
        }

    @staticmethod
    def get_mock_generate_request():
        """Mock generate request payload."""
        return {
            "model": "llama2:7b",
            "prompt": "Once upon a time",
            "stream": False
        }

    @staticmethod
    def get_mock_embed_request():
        """Mock embed request payload."""
        return {
            "model": "llama2:7b",
            "input": "Hello world"
        }

