from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
import os
from dotenv import load_dotenv

class AccountLoginAPITest(APITestCase):
	def setUp(self):
		User = get_user_model()
		self.username = "root"
		self.password = os.getenv("ROOT_PASSWORD", "changeme")
		# Ensure idempotent user creation for persistent test DBs
		user, created = User.objects.get_or_create(username=self.username)
		user.set_password(self.password)
		user.save()

	def test_missing_credentials(self):
		resp = self.client.post("/api/account/login", {}, format="json")
		self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

	def test_invalid_credentials(self):
		resp = self.client.post(
			"/api/account/login",
			{"username": self.username, "password": "wrong"},
			format="json",
		)
		self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

	def test_successful_login(self):
		resp = self.client.post(
			"/api/account/login",
			{"username": self.username, "password": self.password},
			format="json",
		)
		self.assertEqual(resp.status_code, status.HTTP_200_OK)
		self.assertIn("access", resp.data)
		self.assertIn("refresh", resp.data)

	def test_alternate_field_names(self):
		resp = self.client.post(
			"/api/account/login",
			{"account": self.username, "passwd": self.password},
			format="json",
		)
		self.assertEqual(resp.status_code, status.HTTP_200_OK)
		self.assertIn("access", resp.data)
		self.assertIn("refresh", resp.data)


