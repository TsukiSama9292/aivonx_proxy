"""
Tests for Node and NodeGroup ViewSets (CRUD operations).
"""
from django.urls import reverse
from rest_framework import status
from proxy.models import node
from .conftest import AuthenticatedTestCase, ProxyTestMixin


class TestNodeViewSet(AuthenticatedTestCase, ProxyTestMixin):
    """Test Node CRUD operations."""

    def test_list_nodes(self):
        """Test listing all nodes."""
        self.create_sample_nodes()
        url = reverse("node-list")
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 3)

    def test_create_node(self):
        """Test creating a new node."""
        url = reverse("node-list")
        data = {
            "name": "new-node",
            "address": "192.168.0.100",
            "port": 11434,
            "active": True
        }
        response = self.client.post(url, data, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "new-node")
        self.assertEqual(response.data["address"], "192.168.0.100")
        self.assertTrue(node.objects.filter(name="new-node").exists())

    def test_retrieve_node(self):
        """Test retrieving a single node."""
        sample_node = self.create_sample_node()
        url = reverse("node-detail", kwargs={"pk": sample_node.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], sample_node.name)
        self.assertEqual(response.data["address"], sample_node.address)

    def test_update_node(self):
        """Test updating a node."""
        sample_node = self.create_sample_node()
        url = reverse("node-detail", kwargs={"pk": sample_node.pk})
        data = {
            "name": "updated-node",
            "address": sample_node.address,
            "port": sample_node.port,
            "active": False
        }
        response = self.client.put(url, data, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "updated-node")
        self.assertFalse(response.data["active"])
        
        sample_node.refresh_from_db()
        self.assertEqual(sample_node.name, "updated-node")
        self.assertFalse(sample_node.active)

    def test_partial_update_node(self):
        """Test partially updating a node."""
        sample_node = self.create_sample_node()
        url = reverse("node-detail", kwargs={"pk": sample_node.pk})
        data = {"active": False}
        response = self.client.patch(url, data, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["active"])
        
        sample_node.refresh_from_db()
        self.assertFalse(sample_node.active)

    def test_delete_node(self):
        """Test deleting a node."""
        sample_node = self.create_sample_node()
        url = reverse("node-detail", kwargs={"pk": sample_node.pk})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(node.objects.filter(pk=sample_node.pk).exists())

    def test_create_node_validation(self):
        """Test node creation validation."""
        url = reverse("node-list")
        # Missing required fields
        data = {"name": "incomplete-node"}
        response = self.client.post(url, data, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# NodeGroup API removed — tests omitted
