import json
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.apps import apps
from loguru import logger


@csrf_exempt
@require_POST
async def proxy_request(request):
	"""Async reverse-proxy endpoint.

	Expects JSON body. Chooses an Ollama node via HA manager and forwards the
	request payload using `httpx.AsyncClient`, tracking active counts.
	"""
	try:
		payload = json.loads(request.body.decode() or "{}")
	except Exception:
		return JsonResponse({"error": "invalid json body"}, status=400)

	app_config = apps.get_app_config("proxy")
	mgr = getattr(app_config, "ha_manager", None)
	if mgr is None:
		# try to import global manager
		from .utils.ha_manager import get_global_manager

		mgr = get_global_manager()
	if mgr is None:
		return JsonResponse({"error": "no proxy nodes configured"}, status=503)

	# allow selecting a specific node by id (payload: { "node_id": 3 })
	node_id = payload.get("node_id")
	node_addr = None
	if node_id is not None:
		try:
			node_id_int = int(node_id)
		except Exception:
			return JsonResponse({"error": "invalid node_id"}, status=400)
		node_addr = mgr.acquire_node_by_id(node_id_int)
		if not node_addr:
			return JsonResponse({"error": "requested node not available"}, status=404)
	else:
		node_addr = mgr.acquire_node(strategy=payload.get("strategy", "least_active"))
		if not node_addr:
			return JsonResponse({"error": "no healthy nodes available"}, status=503)

	url = node_addr.rstrip("/") + payload.get("path", "/")
	method = payload.get("method", "POST").upper()
	headers = payload.get("headers") or {"content-type": "application/json"}
	body = payload.get("body")

	import httpx

	try:
		async with httpx.AsyncClient(timeout=60.0) as client:
			resp = await client.request(method, url, headers=headers, json=body)
			# forward response content and status
			return HttpResponse(resp.content, status=resp.status_code, content_type=resp.headers.get("content-type", "application/json"))
	except Exception as e:
		logger.exception("proxy request failed")
		return JsonResponse({"error": "upstream request failed"}, status=502)
	finally:
		try:
			mgr.release_node(node_addr)
		except Exception:
			pass
