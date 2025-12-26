from django.test import TestCase
from django.core.cache import cache
from unittest.mock import patch, MagicMock
import logging

# Patch get_global_manager at module level BEFORE importing models to prevent signal blocking
import proxy.utils.proxy_manager as pm_module
_mock_manager = MagicMock()
_mock_manager.refresh_from_db = MagicMock()
_mock_manager._is_leader = False
pm_module._global_manager = _mock_manager

from proxy.models import node as NodeModel


class NodeCRUDTests(TestCase):
    """Simple DB-level CRUD tests for Node model without REST API overhead."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Clear Redis leader lock to avoid PID competition
        try:
            from django_redis import get_redis_connection
            conn = get_redis_connection('default')
            conn.delete('ha_manager_leader')
            conn.delete('ha_refresh_request')
        except Exception as e:
            logging.getLogger('proxy.tests').debug("setUpClass: redis cleanup failed: %s", e)
        
        # Clear Django cache
        cache.clear()
        # Ensure DB is clean before these CRUD tests
        try:
            NodeModel.objects.all().delete()
        except Exception as e:
            logging.getLogger('proxy.tests').debug("setUpClass: DB cleanup failed: %s", e)
        
        # Create CPU node for testing
        cls.cpu_node = NodeModel.objects.create(
            name="CPU",
            address="ollama",
            port=11434,
            active=True,
            available_models=[]
        )

    @classmethod
    def tearDownClass(cls):
        # Clean up Redis locks
        try:
            from django_redis import get_redis_connection
            conn = get_redis_connection('default')
            conn.delete('ha_manager_leader')
            conn.delete('ha_refresh_request')
        except Exception as e:
            logging.getLogger('proxy.tests').debug("tearDownClass: redis cleanup failed: %s", e)
        
        super().tearDownClass()

    def tearDown(self):
        NodeModel.objects.all().delete()

    def test_create_node_via_model(self):
        """Test creating a node directly via ORM."""
        node = NodeModel.objects.create(
            name="CPU-test",
            address="ollama",
            port=11434,
            active=True,
            available_models=["gemma3:270m-it-qat"]
        )
        self.assertIsNotNone(node.id)
        self.assertEqual(node.name, "CPU-test")
        self.assertEqual(node.address, "ollama")
        self.assertEqual(node.port, 11434)
        self.assertTrue(node.active)

    def test_update_node_via_model(self):
        """Test updating a node directly via ORM."""
        node = NodeModel.objects.create(
            name="to-update",
            address="example",
            port=1234,
            active=False
        )
        node.address = "ollama"
        node.port = 11434
        node.active = True
        node.save()

        node.refresh_from_db()
        self.assertEqual(node.address, "ollama")
        self.assertEqual(node.port, 11434)
        self.assertTrue(node.active)

    def test_delete_node_via_model(self):
        """Test deleting a node directly via ORM."""
        node = NodeModel.objects.create(
            name="to-delete",
            address="x",
            port=1,
            active=True
        )
        node_id = node.id
        node.delete()
        self.assertFalse(NodeModel.objects.filter(pk=node_id).exists())

    def test_query_node_by_active_status(self):
        """Test filtering nodes by active status."""
        NodeModel.objects.create(name="n1", address="a1", port=1, active=True)
        NodeModel.objects.create(name="n2", address="a2", port=2, active=False)
        NodeModel.objects.create(name="n3", address="a3", port=3, active=True)

        active_nodes = NodeModel.objects.filter(active=True)
        self.assertEqual(active_nodes.count(), 3)  # CPU node + n1 + n3
        
        inactive_nodes = NodeModel.objects.filter(active=False)
        self.assertEqual(inactive_nodes.count(), 1)
