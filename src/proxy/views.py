import json
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.apps import apps
from loguru import logger
from drf_spectacular.utils import extend_schema
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


@extend_schema(
	tags=['Proxy'],
	request={
		'application/json': {
			'type': 'object',
			'properties': {
				'model': {'type': 'string'},
				'input': {'type': 'string'},
			},
			'required': ['model', 'input']
		}
	},
	responses={
		200: {
			'type': 'object',
			'properties': {
				'embedding': {'type': 'array', 'items': {'type': 'number'}}
			}
		},
		400: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
		404: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
		502: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
		503: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
	}
)
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



@extend_schema(
	tags=['Proxy'],
	request={
		'application/json': {
			'type': 'object',
			'properties': {
				'model': {'type': 'string'},
				'input': {'type': ['string', 'array']},
			},
			'required': ['model', 'input']
		}
	},
	responses={
		200: {
			'type': 'object',
			'properties': {
				'embeddings': {
					'type': 'array',
					'items': {'type': 'array', 'items': {'type': 'number'}}
				}
			}
		},
		400: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
		404: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
		502: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
		503: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
	}
)
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



@extend_schema(
	tags=['Proxy'],
	request={
		'application/json': {
			'type': 'object',
			'properties': {
				'model': {'type': 'string'},
				'prompt': {'type': 'string'},
				'suffix': {'type': 'string'},
				'images': {'type': 'array', 'items': {'type': 'string'}},
				'format': {'type': 'string'},
				'options': {'type': 'object'},
				'system': {'type': 'string'},
				'template': {'type': 'string'},
				'context': {'type': ['array', 'object']},
				'stream': {'type': 'boolean'},
				'raw': {'type': 'boolean'},
				'keep_alive': {'type': 'string'},
			},
			'required': ['model']
		}
	},
	responses={
		200: {
			'description': 'Streaming series of partial response objects (or single final object when `stream=false`).',
			'type': 'object',
			'properties': {
				'model': {'type': 'string'},
				'created_at': {'type': 'string'},
				'response': {'type': 'string'},
				'done': {'type': 'boolean'},
				'context': {'type': ['array', 'object']},
				'total_duration': {'type': 'integer'},
				'load_duration': {'type': 'integer'},
				'prompt_eval_count': {'type': 'integer'},
				'prompt_eval_duration': {'type': 'integer'},
				'eval_count': {'type': 'integer'},
				'eval_duration': {'type': 'integer'},
				'done_reason': {'type': 'string'},
			}
		},
		400: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
		404: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
		502: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
		503: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
	},
	description=(
		"Generate a completion for a given `model` and `prompt`. This endpoint supports "
		"streaming (default) where a sequence of partial JSON objects are returned, "
		"or non-streaming mode when `stream=false` returning a single final JSON object. "
		"Advanced parameters include `format` (json), `options` (model runtime parameters), "
		"`system`, `template`, `context`, `raw`, `suffix`, `images` and `keep_alive`. "
		"When `format=json` instruct the model to emit valid JSON in responses."
	)
)
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



@extend_schema(
	tags=['Proxy'],
	request={
		'application/json': {
			'type': 'object',
			'properties': {
				'model': {'type': 'string'},
				'messages': {
					'type': 'array',
					'items': {
						'type': 'object',
						'properties': {
							'role': {'type': 'string', 'enum': ['system', 'user', 'assistant', 'tool']},
							'content': {'type': 'string'},
							'images': {'type': 'array', 'items': {'type': 'string'}},
							'tool_calls': {'type': 'array', 'items': {'type': 'object'}},
						},
						'required': ['role', 'content']
					}
				},
				'tools': {'type': 'array', 'items': {'type': 'object'}, 'description': 'Tools/functions the model may call; requires `stream=false`.'},
				'format': {'type': 'string', 'description': "Response format, currently 'json' is supported", 'enum': ['json']},
				'options': {'type': 'object', 'description': 'Model runtime options (temperature, seed, etc.)'},
				'stream': {'type': 'boolean', 'description': 'If false, returns a single final response object instead of a stream.'},
				'keep_alive': {'type': 'integer', 'description': 'Seconds to keep model loaded in memory (0 to unload).'},
			},
			'required': ['model', 'messages']
		}
	},
	responses={
		200: {
			'description': 'Streaming series of partial response objects (or single final object when `stream=false`).',
			'type': 'object',
			'properties': {
				'model': {'type': 'string'},
				'created_at': {'type': 'string'},
				'message': {
					'type': 'object',
					'properties': {
						'role': {'type': 'string'},
						'content': {'type': 'string'},
						'images': {'type': ['array', 'null'], 'items': {'type': 'string'}},
						'tool_calls': {'type': ['array', 'null'], 'items': {'type': 'object'}},
					}
				},
				'done': {'type': 'boolean'},
				'done_reason': {'type': 'string'},
				'total_duration': {'type': 'integer'},
				'load_duration': {'type': 'integer'},
				'prompt_eval_count': {'type': 'integer'},
				'prompt_eval_duration': {'type': 'integer'},
				'eval_count': {'type': 'integer'},
				'eval_duration': {'type': 'integer'},
			}
		},
		400: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
		404: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
		502: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
		503: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
	},
	description=(
		"Generate the next message in a chat using the provided `model`. This endpoint streams partial "
		"responses by default; set `stream=false` to receive a single final JSON object. The `messages` "
		"array holds message objects with `role`, `content`, optional `images` (base64), and optional "
		"`tool_calls`. Providing `tools` requires `stream=false` (tools are executed synchronously). "
		"Advanced parameters: `format` (currently 'json'), `options` (model runtime parameters), "
		"and `keep_alive` (seconds, 0 to unload)."
	)
)
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



@extend_schema(
	tags=['Proxy'],
	responses={
		200: {
			'type': 'object',
			'properties': {
				'models': {
					'type': 'array',
					'items': {
						'type': 'object',
						'properties': {
							'name': {'type': 'string'},
							'modified_at': {'type': 'string'},
							'size': {'type': 'integer'},
							'digest': {'type': 'string'},
							'details': {
								'type': 'object',
								'properties': {
									'format': {'type': 'string'},
									'family': {'type': 'string'},
									'families': {'type': ['array', 'null'], 'items': {'type': 'string'}},
									'parameter_size': {'type': 'string'},
									'quantization_level': {'type': 'string'},
								},
							},
						}
					}
				}
			}
		},
		400: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
		503: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
	}
)
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