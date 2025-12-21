import json
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.apps import apps
from loguru import logger
from django.http import StreamingHttpResponse
from django.core.cache import cache


def _get_strategy_from_config(payload, mgr):
	"""Determine strategy from payload or DB-backed ProxyConfig."""
	if payload and isinstance(payload, dict):
		s = payload.get("strategy")
		if s:
			return s
	try:
		from .models import ProxyConfig

		cfg = ProxyConfig.objects.order_by("-updated_at").first()
		if cfg:
			return cfg.strategy
	except Exception:
		pass
	return "least_active"


def _select_node_for_model(mgr, model_name, strategy=None):
	"""Wrapper to select a node using the manager's choose_node API."""
	try:
		return mgr.choose_node(model_name=model_name, strategy=strategy)
	except Exception:
		return None


@require_POST
async def proxy_embed(request):
	"""Proxy endpoint compatible with Ollama's `/api/embed`.

	Forwards POST body to selected node's `/api/embed` and returns the response.
	"""
	app_config = apps.get_app_config("proxy")
	mgr = getattr(app_config, "proxy_manager", None)
	if mgr is None:
		from .utils.proxy_manager import get_global_manager

		mgr = get_global_manager()
	if mgr is None:
		return JsonResponse({"error": "no proxy nodes configured"}, status=503)

	try:
		body_bytes = request.body or b""
		payload = None
		if body_bytes:
			import json as _json
			try:
				payload = _json.loads(body_bytes.decode())
			except Exception:
				payload = None
	except Exception:
		body_bytes = await request.body

	if payload and payload.get("node_id") is not None:
		return JsonResponse({"error": "specifying node_id is not allowed"}, status=400)

	model_name = payload.get("model") if payload else None
	strategy = _get_strategy_from_config(payload, mgr)
	node_addr = _select_node_for_model(mgr, model_name, strategy)
	if not node_addr:
		return JsonResponse({"error": f"model not available on any node: {model_name}"}, status=404)

	url = node_addr.rstrip("/") + "/api/embed"
	headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}

	import httpx
	try:
		async with httpx.AsyncClient(timeout=60.0) as client:
			resp = await client.post(url, headers=headers, content=body_bytes)
			content_type = resp.headers.get("content-type", "application/json")
			return HttpResponse(resp.content, status=resp.status_code, content_type=content_type)
	except Exception:
		logger.exception("proxy embed request failed")
		return JsonResponse({"error": "upstream request failed"}, status=502)
	finally:
		try:
			mgr.release_node(node_addr)
		except Exception:
			pass



@require_POST
async def proxy_embeddings(request):
	"""Proxy endpoint compatible with Ollama's legacy `/api/embeddings`.

	Forwards POST body to selected node's `/api/embeddings` and returns the response.
	"""
	app_config = apps.get_app_config("proxy")
	mgr = getattr(app_config, "proxy_manager", None)
	if mgr is None:
		from .utils.proxy_manager import get_global_manager

		mgr = get_global_manager()
	if mgr is None:
		return JsonResponse({"error": "no proxy nodes configured"}, status=503)

	try:
		body_bytes = request.body or b""
		payload = None
		if body_bytes:
			import json as _json
			try:
				payload = _json.loads(body_bytes.decode())
			except Exception:
				payload = None
	except Exception:
		body_bytes = await request.body

	if payload and payload.get("node_id") is not None:
		return JsonResponse({"error": "specifying node_id is not allowed"}, status=400)

	model_name = payload.get("model") if payload else None
	strategy = _get_strategy_from_config(payload, mgr)
	node_addr = _select_node_for_model(mgr, model_name, strategy)
	if not node_addr:
		return JsonResponse({"error": f"model not available on any node: {model_name}"}, status=404)

	url = node_addr.rstrip("/") + "/api/embeddings"
	headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}

	import httpx
	try:
		async with httpx.AsyncClient(timeout=60.0) as client:
			resp = await client.post(url, headers=headers, content=body_bytes)
			content_type = resp.headers.get("content-type", "application/json")
			return HttpResponse(resp.content, status=resp.status_code, content_type=content_type)
	except Exception:
		logger.exception("proxy embeddings request failed")
		return JsonResponse({"error": "upstream request failed"}, status=502)
	finally:
		try:
			mgr.release_node(node_addr)
		except Exception:
			pass



@require_POST
async def proxy_generate(request):
	"""Proxy endpoint compatible with Ollama's `/api/generate`.

	This forwards the incoming POST body and headers to a selected Ollama node's
	`/api/generate` path and returns the upstream response.
	"""
	# get manager
	app_config = apps.get_app_config("proxy")
	mgr = getattr(app_config, "proxy_manager", None)
	if mgr is None:
		from .utils.proxy_manager import get_global_manager

		mgr = get_global_manager()
	if mgr is None:
		return JsonResponse({"error": "no proxy nodes configured"}, status=503)

	# choose node (support explicit node_id in JSON body)
	try:
		body_bytes = request.body or b""
		payload = None
		if body_bytes:
			import json
			try:
				payload = json.loads(body_bytes.decode())
			except Exception:
				payload = None
	except Exception:
		body_bytes = await request.body

	if payload and payload.get("node_id") is not None:
		return JsonResponse({"error": "specifying node_id is not allowed"}, status=400)

	model_name = payload.get("model") if payload else None
	strategy = _get_strategy_from_config(payload, mgr)
	node_addr = _select_node_for_model(mgr, model_name, strategy)
	if not node_addr:
		return JsonResponse({"error": f"model not available on any node: {model_name}"}, status=404)

	# prepare upstream request
	url = node_addr.rstrip("/") + "/api/generate"
	# forward most headers except host/content-length
	headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}

	import httpx
	try:
		async with httpx.AsyncClient(timeout=60.0) as client:
			resp = await client.post(url, headers=headers, content=body_bytes)
			content_type = resp.headers.get("content-type", "application/json")
			return HttpResponse(resp.content, status=resp.status_code, content_type=content_type)
	except Exception:
		logger.exception("proxy generate request failed")
		return JsonResponse({"error": "upstream request failed"}, status=502)
	finally:
		try:
			mgr.release_node(node_addr)
		except Exception:
			pass



@require_POST
async def proxy_chat(request):
	"""Proxy endpoint compatible with Ollama's `/api/chat`.

	Supports streaming when the incoming JSON omits `stream: false`.
	For non-streaming (`"stream": false`) the upstream response is returned
	in full. For streaming, the upstream bytes are proxied back using
	`StreamingHttpResponse`.
	"""
	# get manager
	app_config = apps.get_app_config("proxy")
	mgr = getattr(app_config, "proxy_manager", None)
	if mgr is None:
		from .utils.proxy_manager import get_global_manager

		mgr = get_global_manager()
	if mgr is None:
		return JsonResponse({"error": "no proxy nodes configured"}, status=503)

	# read body and try to parse JSON to inspect stream/node_id
	try:
		body_bytes = request.body or b""
		payload = None
		if body_bytes:
			import json as _json

			try:
				payload = _json.loads(body_bytes.decode())
			except Exception:
				payload = None
	except Exception:
		body_bytes = await request.body

	# disallow external node selection
	if payload and payload.get("node_id") is not None:
		return JsonResponse({"error": "specifying node_id is not allowed"}, status=400)

	model_name = payload.get("model") if payload else None
	strategy = _get_strategy_from_config(payload, mgr)
	node_addr = _select_node_for_model(mgr, model_name, strategy)
	if not node_addr:
		return JsonResponse({"error": f"model not available on any node: {model_name}"}, status=404)

	url = node_addr.rstrip("/") + "/api/chat"
	headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}

	import httpx

	try:
		# non-streaming path
		if payload and payload.get("stream") is False:
			async with httpx.AsyncClient(timeout=120.0) as client:
				resp = await client.post(url, headers=headers, content=body_bytes)
				content_type = resp.headers.get("content-type", "application/json")
				return HttpResponse(resp.content, status=resp.status_code, content_type=content_type)

		# streaming path: proxy upstream stream to client
		async def stream_generator():
			async with httpx.AsyncClient(timeout=None) as client:
				async with client.stream("POST", url, headers=headers, content=body_bytes) as resp:
					# yield status line? we rely on HTTP status set on response (default 200)
					async for chunk in resp.aiter_bytes():
						if chunk:
							yield chunk

		return StreamingHttpResponse(stream_generator(), content_type="application/json")
	except Exception:
		logger.exception("proxy chat request failed")
		return JsonResponse({"error": "upstream request failed"}, status=502)
	finally:
		try:
			mgr.release_node(node_addr)
		except Exception:
			pass



@require_GET
async def proxy_tags(request):
	"""List local models by forwarding GET /api/tags to a selected node."""
	app_config = apps.get_app_config("proxy")
	mgr = getattr(app_config, "proxy_manager", None)
	if mgr is None:
		from .utils.proxy_manager import get_global_manager

		mgr = get_global_manager()
	if mgr is None:
		return JsonResponse({"error": "no proxy nodes configured"}, status=503)

	# disallow external node selection via query param
	if request.GET.get("node_id") is not None:
		return JsonResponse({"error": "specifying node_id is not allowed"}, status=400)

	strategy = _get_strategy_from_config(request.GET, mgr) if hasattr(request, 'GET') else _get_strategy_from_config(None, mgr)
	node_addr = _select_node_for_model(mgr, None, strategy)
	if not node_addr:
		return JsonResponse({"error": "no healthy nodes available"}, status=503)

	url = node_addr.rstrip("/") + "/api/tags"
	headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}

	import httpx
	try:
		async with httpx.AsyncClient(timeout=30.0) as client:
			resp = await client.get(url, headers=headers)
			content_type = resp.headers.get("content-type", "application/json")
			return HttpResponse(resp.content, status=resp.status_code, content_type=content_type)
	except Exception:
		logger.exception("proxy tags request failed")
		return JsonResponse({"error": "upstream request failed"}, status=502)
	finally:
		try:
			mgr.release_node(node_addr)
		except Exception:
			pass



@require_POST
async def proxy_show(request):
	"""Forward POST /api/show to a selected node and return result."""
	app_config = apps.get_app_config("proxy")
	mgr = getattr(app_config, "proxy_manager", None)
	if mgr is None:
		from .utils.proxy_manager import get_global_manager

		mgr = get_global_manager()
	if mgr is None:
		return JsonResponse({"error": "no proxy nodes configured"}, status=503)

	try:
		body_bytes = request.body or b""
		payload = None
		if body_bytes:
			import json as _json
			try:
				payload = _json.loads(body_bytes.decode())
			except Exception:
				payload = None
	except Exception:
		body_bytes = await request.body
	# /show endpoint has been removed from proxy; respond 404 for safety
	return JsonResponse({"error": "/show endpoint removed; use /show on node directly"}, status=404)
