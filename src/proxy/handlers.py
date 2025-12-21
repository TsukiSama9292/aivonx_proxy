import json
from typing import Optional

from django.http import JsonResponse, HttpResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.apps import apps
from loguru import logger
from drf_spectacular.utils import extend_schema

from . import streaming as _streaming
import httpx


@extend_schema(
    tags=['Proxy'],
    responses={
        200: {
            'type': 'object',
            'properties': {
                'active': {'type': 'array', 'items': {'type': 'string'}},
                'standby': {'type': 'array', 'items': {'type': 'string'}},
                'node_id_map': {'type': 'object'},
                'latencies': {'type': 'object'},
                'active_counts': {'type': 'object'},
                'models': {'type': 'object'},
            }
        },
        503: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
        500: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
    }
)
@api_view(['GET'])
@permission_classes([AllowAny])
def state(request):
    """Diagnostics: show HA manager and cache state for debugging."""
    mgr = _get_manager()
    from django.core.cache import cache

    if mgr is None:
        return JsonResponse({"error": "no proxy manager"}, status=503)

    try:
        active = cache.get(mgr.ACTIVE_POOL_KEY, [])
        standby = cache.get(mgr.STANDBY_POOL_KEY, [])
        node_map = cache.get(mgr.NODE_ID_MAP_KEY, {})
        latencies = {a: cache.get(mgr.LATENCY_KEY_PREFIX + a) for a in list({*active, *standby})}
        active_counts = {a: cache.get(mgr._active_count_key(a), 0) for a in list({*active, *standby})}
        models = {a: cache.get(mgr.MODELS_KEY_PREFIX + a, []) for a in list({*active, *standby})}
        # If cache is empty in this process (LocMemCache is process-local), refresh from DB
        if not active and getattr(mgr, 'nodes', None):
            try:
                mgr.refresh_from_db()
                active = cache.get(mgr.ACTIVE_POOL_KEY, [])
                standby = cache.get(mgr.STANDBY_POOL_KEY, [])
                node_map = cache.get(mgr.NODE_ID_MAP_KEY, {})
                latencies = {a: cache.get(mgr.LATENCY_KEY_PREFIX + a) for a in list({*active, *standby})}
                active_counts = {a: cache.get(mgr._active_count_key(a), 0) for a in list({*active, *standby})}
                models = {a: cache.get(mgr.MODELS_KEY_PREFIX + a, []) for a in list({*active, *standby})}
            except Exception:
                logger.debug("refresh_from_db failed in state handler")
        return JsonResponse({
            "active": active,
            "standby": standby,
            "node_id_map": node_map,
            "latencies": latencies,
            "active_counts": active_counts,
            "models": models,
        })
    except Exception as e:
        logger.exception("failed to read state")
        return JsonResponse({"error": "failed to read state", "details": str(e)}, status=500)


def _get_manager():
    app_config = apps.get_app_config("proxy")
    mgr = getattr(app_config, "proxy_manager", None)
    if mgr is None:
        from .utils.proxy_manager import get_global_manager, init_global_manager_from_db
        try:
            # try to initialize manager from DB in this process (covers servers without lifespan events)
            logger.debug("_get_manager: calling init_global_manager_from_db() in process")
            mgr = init_global_manager_from_db()
            logger.debug("_get_manager: init_global_manager_from_db returned manager with nodes=%s", getattr(mgr, 'nodes', None))
            try:
                app_config.proxy_manager = mgr
            except Exception:
                logger.debug("_get_manager: failed to attach manager to AppConfig")
        except Exception:
            logger.debug("_get_manager: init_global_manager_from_db failed, falling back to get_global_manager()")
            mgr = get_global_manager()
    return mgr


@extend_schema(
    tags=['Proxy'],
    responses={200: {'type': 'string'}, 503: {'type': 'object', 'properties': {'error': {'type': 'string'}}}}
)
@api_view(['GET'])
@permission_classes([AllowAny])
def health(request):
    mgr = _get_manager()
    if mgr is None:
        return JsonResponse({"error": "no proxy nodes configured"}, status=503)
    active = mgr and [] or []
    try:
        from django.core.cache import cache

        active = cache.get(mgr.ACTIVE_POOL_KEY, [])
        # if active pool cache is empty, fall back to configured nodes list
        if not active:
            try:
                cfg_nodes = getattr(mgr, 'nodes', None)
                if cfg_nodes:
                    active = list(cfg_nodes)
            except Exception:
                pass
    except Exception:
        active = []

    if active:
        return HttpResponse("Ollama is running", status=200)
    return JsonResponse({"error": "no healthy nodes available"}, status=404)


@extend_schema(
    tags=['Proxy'],
    request={'application/json': {'type': 'object'}},
    responses={200: {'type': 'object'}, 400: {'type': 'object'}, 404: {'type': 'object'}, 502: {'type': 'object'}, 503: {'type': 'object'}}
)
@api_view(['POST'])
@permission_classes([AllowAny])
async def proxy_generate(request):
    mgr = _get_manager()
    if mgr is None:
        return JsonResponse({"error": "no proxy nodes configured"}, status=503)

    try:
        body_bytes = request.body or b""
        payload = None
        if body_bytes:
            try:
                payload = json.loads(body_bytes.decode())
            except Exception:
                payload = None
    except Exception:
        body_bytes = await request.body

    if payload and payload.get("node_id") is not None:
        return JsonResponse({"error": "specifying node_id is not allowed"}, status=400)

    model_name = payload.get("model") if payload else None
    node_addr = mgr.choose_node(model_name=model_name)
    if not node_addr:
        return JsonResponse({"error": f"model not available on any node: {model_name}"}, status=404)

    url = node_addr.rstrip("/") + "/api/generate"
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}
    # support streaming when payload contains "stream": true
    stream_flag = payload and payload.get("stream") is True
    if stream_flag:
        async def stream_generator():
            try:
                import httpx
                async with httpx.AsyncClient(timeout=None) as client:
                    async with client.stream("POST", url, headers=headers, content=body_bytes) as resp:
                        content_type = resp.headers.get("content-type", "application/x-ndjson")
                        # yield chunks as they arrive
                        async for chunk in resp.aiter_bytes():
                            if chunk:
                                yield chunk
            finally:
                try:
                    mgr.release_node(node_addr)
                except Exception:
                    pass

        # Do not set Content-Length so response is streamed
        return StreamingHttpResponse(stream_generator(), content_type="application/x-ndjson")

    # non-streaming path (buffered)
    import httpx
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, headers=headers, content=body_bytes)
            return HttpResponse(resp.content, status=resp.status_code, content_type=resp.headers.get("content-type", "application/json"))
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
@api_view(['POST'])
@permission_classes([AllowAny])
async def proxy_chat(request):
    mgr = _get_manager()
    if mgr is None:
        return JsonResponse({"error": "no proxy nodes configured"}, status=503)

    try:
        body_bytes = request.body or b""
        payload = None
        if body_bytes:
            try:
                payload = json.loads(body_bytes.decode())
            except Exception:
                payload = None
    except Exception:
        body_bytes = await request.body

    if payload and payload.get("node_id") is not None:
        return JsonResponse({"error": "specifying node_id is not allowed"}, status=400)

    model_name = payload.get("model") if payload else None
    node_addr = mgr.choose_node(model_name=model_name)
    if not node_addr:
        return JsonResponse({"error": f"model not available on any node: {model_name}"}, status=404)

    url = node_addr.rstrip("/") + "/api/chat"
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}

    # non-streaming
    if payload and payload.get("stream") is False:
        import httpx

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(url, headers=headers, content=body_bytes)
                return HttpResponse(resp.content, status=resp.status_code, content_type=resp.headers.get("content-type", "application/json"))
        except Exception:
            logger.exception("proxy chat request failed")
            return JsonResponse({"error": "upstream request failed"}, status=502)
        finally:
            try:
                mgr.release_node(node_addr)
            except Exception:
                pass

    # streaming path
    async def _stream_and_release():
        try:
            async for chunk in _streaming.stream_post_bytes(url, headers, body_bytes):
                yield chunk
        finally:
            try:
                mgr.release_node(node_addr)
            except Exception:
                pass

    return StreamingHttpResponse(_stream_and_release(), content_type="application/json")


@extend_schema(
    tags=['Proxy'],
    request={'application/json': {'type': 'object'}},
    responses={200: {'type': 'object'}, 400: {'type': 'object'}, 404: {'type': 'object'}, 502: {'type': 'object'}, 503: {'type': 'object'}}
)
@api_view(['POST'])
@permission_classes([AllowAny])
async def proxy_embed(request):
    mgr = _get_manager()
    if mgr is None:
        return JsonResponse({"error": "no proxy nodes configured"}, status=503)

    try:
        body_bytes = request.body or b""
        payload = None
        if body_bytes:
            try:
                payload = json.loads(body_bytes.decode())
            except Exception:
                payload = None
    except Exception:
        body_bytes = await request.body

    if payload and payload.get("node_id") is not None:
        return JsonResponse({"error": "specifying node_id is not allowed"}, status=400)

    model_name = payload.get("model") if payload else None
    node_addr = mgr.choose_node(model_name=model_name)
    if not node_addr:
        return JsonResponse({"error": f"model not available on any node: {model_name}"}, status=404)

    url = node_addr.rstrip("/") + "/api/embed"
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}

    import httpx
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, headers=headers, content=body_bytes)
            return HttpResponse(resp.content, status=resp.status_code, content_type=resp.headers.get("content-type", "application/json"))
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
    request={'application/json': {'type': 'object'}},
    responses={200: {'type': 'object'}, 400: {'type': 'object'}, 404: {'type': 'object'}, 502: {'type': 'object'}, 503: {'type': 'object'}}
)
@api_view(['POST'])
@permission_classes([AllowAny])
async def proxy_embeddings(request):
    mgr = _get_manager()
    if mgr is None:
        return JsonResponse({"error": "no proxy nodes configured"}, status=503)

    try:
        body_bytes = request.body or b""
        payload = None
        if body_bytes:
            try:
                payload = json.loads(body_bytes.decode())
            except Exception:
                payload = None
    except Exception:
        body_bytes = await request.body

    if payload and payload.get("node_id") is not None:
        return JsonResponse({"error": "specifying node_id is not allowed"}, status=400)

    model_name = payload.get("model") if payload else None
    node_addr = mgr.choose_node(model_name=model_name)
    if not node_addr:
        return JsonResponse({"error": f"model not available on any node: {model_name}"}, status=404)

    url = node_addr.rstrip("/") + "/api/embeddings"
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}

    import httpx
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, headers=headers, content=body_bytes)
            return HttpResponse(resp.content, status=resp.status_code, content_type=resp.headers.get("content-type", "application/json"))
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
    responses={200: {'type': 'object'}, 400: {'type': 'object'}, 503: {'type': 'object'}}
)
@api_view(['GET'])
@permission_classes([AllowAny])
async def proxy_tags(request):
    mgr = _get_manager()
    if mgr is None:
        return JsonResponse({"error": "no proxy nodes configured"}, status=503)

    if request.GET.get("node_id") is not None:
        return JsonResponse({"error": "specifying node_id is not allowed"}, status=400)

    node_addr = mgr.choose_node(model_name=None)
    if not node_addr:
        return JsonResponse({"error": "no healthy nodes available"}, status=503)

    url = node_addr.rstrip("/") + "/api/tags"
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}

    import httpx
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=headers)
            return HttpResponse(resp.content, status=resp.status_code, content_type=resp.headers.get("content-type", "application/json"))
    except Exception:
        logger.exception("proxy tags request failed")
        return JsonResponse({"error": "upstream request failed"}, status=502)
    finally:
        try:
            mgr.release_node(node_addr)
        except Exception:
            pass
