import json
import tempfile
from datetime import datetime, timedelta

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from django.utils.crypto import get_random_string


class LogsAPIViewTests(TestCase):
	def setUp(self):
		User = get_user_model()
		pw = get_random_string(12)
		user = User.objects.create_user(username='logtest', password=pw)
		self.client = APIClient()
		self.client.force_authenticate(user=user)

	def _write_lines(self, lines):
		tf = tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8')
		for obj in lines:
			tf.write(json.dumps(obj, default=str) + "\n")
		tf.flush()
		tf.close()
		return tf.name

	def test_missing_log_path_returns_500(self):
		with self.settings(LOG_JSON_PATH=None):
			resp = self.client.get('/api/logs/')
			self.assertEqual(resp.status_code, 500)
			self.assertIn('LOG_JSON_PATH', resp.json().get('detail', '') )

	def test_file_not_found_returns_404(self):
		with self.settings(LOG_JSON_PATH='/nonexistent/path/to/log.json'):
			resp = self.client.get('/api/logs/')
			self.assertEqual(resp.status_code, 404)

	def test_pagination_and_filters(self):
		# Prepare log lines with timestamps and different levels/messages
		now = datetime.utcnow()
		lines = []
		lines.append({'asctime': (now - timedelta(minutes=3)).isoformat() + 'Z', 'levelname': 'INFO', 'message': 'alpha one', 'name': 'app', 'module': 'm', 'process': 1, 'thread': 10})
		lines.append({'asctime': (now - timedelta(minutes=2)).isoformat() + 'Z', 'levelname': 'ERROR', 'message': 'beta two', 'name': 'app', 'module': 'm', 'process': 1, 'thread': 11})
		lines.append({'asctime': (now - timedelta(minutes=1)).isoformat() + 'Z', 'levelname': 'INFO', 'message': 'alpha beta', 'name': 'app', 'module': 'm', 'process': 1, 'thread': 12})
		lines.append({'asctime': now.isoformat() + 'Z', 'levelname': 'DEBUG', 'message': 'gamma', 'name': 'app', 'module': 'm', 'process': 1, 'thread': 13})

		path = self._write_lines(lines)

		with self.settings(LOG_JSON_PATH=path):
			# Basic request
			resp = self.client.get('/api/logs/')
			self.assertEqual(resp.status_code, 200)
			body = resp.json()
			self.assertEqual(body['count'], 4)

			# limit/offset pagination
			resp2 = self.client.get('/api/logs/?limit=2&offset=1')
			self.assertEqual(resp2.status_code, 200)
			b2 = resp2.json()
			self.assertEqual(b2['offset'], 1)
			self.assertEqual(b2['limit'], 2)
			self.assertEqual(len(b2['results']), 2)

			# query filter
			q = self.client.get('/api/logs/?query=alpha')
			self.assertEqual(q.status_code, 200)
			self.assertEqual(q.json()['count'], 2)

			# level filter
			lvl = self.client.get('/api/logs/?level=ERROR')
			self.assertEqual(lvl.status_code, 200)
			self.assertEqual(lvl.json()['count'], 1)

			# start / end filtering
			start_ts = (now - timedelta(minutes=2, seconds=30)).isoformat() + 'Z'
			r = self.client.get(f'/api/logs/?start={start_ts}')
			self.assertEqual(r.status_code, 200)
			# should include last 3 entries
			self.assertEqual(r.json()['count'], 3)

	def test_source_proxy_uses_proxy_log_path(self):
		# create proxy log file
		now = datetime.utcnow()
		lines = [{'asctime': now.isoformat() + 'Z', 'levelname': 'INFO', 'message': 'proxy msg', 'name': 'proxy', 'module': 'p', 'process': 2, 'thread': 20}]
		path = self._write_lines(lines)

		with self.settings(PROXY_LOG_JSON_PATH=path):
			resp = self.client.get('/api/logs/?source=proxy')
			self.assertEqual(resp.status_code, 200)
			self.assertEqual(resp.json()['count'], 1)
