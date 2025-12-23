import json
import asyncio

from django.http import JsonResponse, HttpResponse, StreamingHttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
import logging
logger = logging.getLogger('proxy')
from drf_spectacular.utils import extend_schema
from .views import _get_manager
from . import streaming as _streaming
from asgiref.sync import async_to_sync

@extend_schema(
    tags=['Proxy'],
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'model': {'type': 'string', 'description': 'Model name (format: model:tag). Tag is optional; defaults to latest.'},
                'prompt': {'type': 'string', 'description': 'Prompt to generate a response for.'},
                'suffix': {'type': 'string', 'description': 'Text appended after the model response.'},
                'images': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Base64-encoded images for multimodal models.'},
                'format': {'type': 'string', 'enum': ['json'], 'description': "Response format (use 'json' for JSON mode)."},
                'options': {'type': 'object', 'description': 'Model runtime options (temperature, seed, etc.).'},
                'system': {'type': 'string', 'description': 'System message to override the Modelfile definition.'},
                'template': {'type': 'string', 'description': 'Prompt template to use (overrides Modelfile).'},
                'context': {'type': 'array', 'items': {'type': 'integer'}, 'description': 'Context encoding from a previous response for short conversational memory.'},
                'stream': {'type': 'boolean', 'description': 'If false, returns a single final JSON object rather than a stream.'},
                'raw': {'type': 'boolean', 'description': 'If true, bypass templating and send the prompt raw (no context will be returned).'},
                'keep_alive': {'type': 'integer', 'description': 'Seconds to keep the model loaded in memory (0 to unload).'},
            },
            'required': ['model']
        }
    },
    responses={
        200: {
            'type': 'object',
            'properties': {
                'model': {'type': 'string'},
                'created_at': {'type': 'string', 'format': 'date-time'},
                'response': {'type': 'string'},
                'done': {'type': 'boolean'},
                'done_reason': {'type': 'string'},
                'context': {'type': 'array', 'items': {'type': 'integer'}},
                'total_duration': {'type': 'integer', 'description': 'Duration in nanoseconds.'},
                'load_duration': {'type': 'integer', 'description': 'Duration in nanoseconds.'},
                'prompt_eval_count': {'type': 'integer'},
                'prompt_eval_duration': {'type': 'integer', 'description': 'Duration in nanoseconds.'},
                'eval_count': {'type': 'integer'},
                'eval_duration': {'type': 'integer', 'description': 'Duration in nanoseconds.'},
            },
            'description': 'Streaming series of partial response objects (or single final object when `stream=false`). Durations are returned in nanoseconds.'
        },
        400: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
        404: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
        502: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
        503: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
    },
    description=(
        "Generate a response for a given prompt. Model names follow the `model:tag` format (tag optional). "
        "Streaming responses are returned by default; set `stream=false` to receive a single final JSON object. "
        "All durations are returned in nanoseconds."
    )
)
@api_view(['POST'])
@permission_classes([AllowAny])
def proxy_generate(request):
    mgr = _get_manager()
    if mgr is None:
        return JsonResponse({"error": "no proxy nodes configured"}, status=503)

    body_bytes = request.body or b""
    payload = None
    if body_bytes:
        try:
            payload = json.loads(body_bytes.decode())
        except Exception:
            payload = None

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
    
    async def do_request():
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
    
    return async_to_sync(do_request)()


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
def proxy_chat(request):
    mgr = _get_manager()
    if mgr is None:
        return JsonResponse({"error": "no proxy nodes configured"}, status=503)

    body_bytes = request.body or b""
    payload = None
    if body_bytes:
        try:
            payload = json.loads(body_bytes.decode())
        except Exception:
            payload = None

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

        async def do_request():
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
        
        return async_to_sync(do_request)()

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
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'model': {'type': 'string', 'description': 'Name of the model to generate embeddings from.'},
                'input': {
                    'oneOf': [
                        {'type': 'string'},
                        {'type': 'array', 'items': {'type': 'string'}}
                    ],
                    'description': 'Text or list of texts to generate embeddings for.'
                },
                'truncate': {'type': 'boolean', 'description': 'Truncate end of each input to fit context length. Defaults to true.'},
                'options': {'type': 'object', 'description': 'Model runtime options.'},
                'keep_alive': {'type': 'integer', 'description': 'Seconds to keep the model loaded in memory (0 to unload).'},
            },
            'required': ['model', 'input']
        }
    },
    responses={
        200: {
            'type': 'object',
            'properties': {
                'model': {'type': 'string'},
                'embeddings': {'type': 'array', 'items': {'type': 'array', 'items': {'type': 'number'}}},
                'total_duration': {'type': 'integer', 'description': 'Duration in nanoseconds.'},
                'load_duration': {'type': 'integer', 'description': 'Duration in nanoseconds.'},
                'prompt_eval_count': {'type': 'integer'},
            }
        },
        400: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
        404: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
        502: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
        503: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
    },
    description=(
        "Generate embeddings from a model. `input` may be a string or an array of strings. "
        "Advanced parameters: `truncate` (defaults true), `options`, and `keep_alive`. "
        "Durations are returned in nanoseconds."
    )
)
@api_view(['POST'])
@permission_classes([AllowAny])
def proxy_embed(request):
    mgr = _get_manager()
    if mgr is None:
        return JsonResponse({"error": "no proxy nodes configured"}, status=503)

    body_bytes = request.body or b""
    payload = None
    if body_bytes:
        try:
            payload = json.loads(body_bytes.decode())
        except Exception:
            payload = None

    if payload and payload.get("node_id") is not None:
        return JsonResponse({"error": "specifying node_id is not allowed"}, status=400)

    model_name = payload.get("model") if payload else None
    node_addr = mgr.choose_node(model_name=model_name)
    if not node_addr:
        return JsonResponse({"error": f"model not available on any node: {model_name}"}, status=404)

    url = node_addr.rstrip("/") + "/api/embed"
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}

    import httpx
    
    async def do_request():
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
    
    return async_to_sync(do_request)()


@extend_schema(
    tags=['Proxy'],
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'model': {'type': 'string', 'description': 'Name of the model to generate embeddings from.'},
                'prompt': {'type': 'string', 'description': 'Text to generate embeddings for.'},
                'options': {'type': 'object', 'description': 'Model runtime options.'},
                'keep_alive': {'type': 'integer', 'description': 'Seconds to keep the model loaded in memory (0 to unload).'},
            },
            'required': ['model', 'prompt']
        }
    },
    responses={
        200: {
            'type': 'object',
            'properties': {
                'embedding': {'type': 'array', 'items': {'type': 'number'}},
                'model': {'type': 'string'},
                'total_duration': {'type': 'integer', 'description': 'Duration in nanoseconds.'},
                'load_duration': {'type': 'integer', 'description': 'Duration in nanoseconds.'},
                'prompt_eval_count': {'type': 'integer'},
            }
        },
        400: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
        404: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
        502: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
        503: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
    },
    description=(
        "Generate an embedding for the provided prompt. This endpoint has been superseded by /api/embed. "
        "Durations are returned in nanoseconds."
    )
)
@api_view(['POST'])
@permission_classes([AllowAny])
def proxy_embeddings(request):
    mgr = _get_manager()
    if mgr is None:
        return JsonResponse({"error": "no proxy nodes configured"}, status=503)

    body_bytes = request.body or b""
    payload = None
    if body_bytes:
        try:
            payload = json.loads(body_bytes.decode())
        except Exception:
            payload = None

    if payload and payload.get("node_id") is not None:
        return JsonResponse({"error": "specifying node_id is not allowed"}, status=400)

    model_name = payload.get("model") if payload else None
    node_addr = mgr.choose_node(model_name=model_name)
    if not node_addr:
        return JsonResponse({"error": f"model not available on any node: {model_name}"}, status=404)

    url = node_addr.rstrip("/") + "/api/embeddings"
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}

    import httpx
    
    async def do_request():
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
    
    return async_to_sync(do_request)()


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
                            'modified_at': {'type': 'string', 'format': 'date-time'},
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
                                }
                            }
                        }
                    }
                }
            }
        },
        400: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
        503: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
    },
    description=(
        "List models available across all proxy nodes (aggregated). Returns metadata for each unique model including `name`, `modified_at` (RFC3339), "
        "`size` (bytes), `digest`, and a `details` object with format/family/parameter_size/quantization_level. "
        "Models with the same name from different nodes are deduplicated, keeping the most recently modified version."
    )
)
@api_view(['GET'])
@permission_classes([AllowAny])
def proxy_tags(request):
    mgr = _get_manager()
    if mgr is None:
        return JsonResponse({"error": "no proxy nodes configured"}, status=503)

    if request.GET.get("node_id") is not None:
        return JsonResponse({"error": "specifying node_id is not allowed"}, status=400)

    # Get all active and standby nodes
    from django.core.cache import cache
    active = cache.get(mgr.ACTIVE_POOL_KEY, [])
    standby = cache.get(mgr.STANDBY_POOL_KEY, [])
    all_nodes = list({*active, *standby})

    if not all_nodes:
        return JsonResponse({"error": "no nodes available"}, status=503)

    # Query /api/tags from all nodes concurrently
    import httpx

    async def fetch_node_tags(addr):
        url = addr.rstrip("/") + "/api/tags"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("models", []) if isinstance(data, dict) else []
        except Exception as e:
            logger.debug("failed to fetch tags from %s: %s", addr, e)
        return []

    async def fetch_all():
        tasks = [fetch_node_tags(addr) for addr in all_nodes]
        return await asyncio.gather(*tasks, return_exceptions=True)

    # Fetch from all nodes concurrently (use async_to_sync for sync view)
    results = async_to_sync(fetch_all)()

    # Aggregate models: deduplicate by name, keep most recent modified_at
    models_dict = {}
    for result in results:
        if isinstance(result, list):
            for model in result:
                if isinstance(model, dict) and model.get("name"):
                    name = model["name"]
                    # If model name already exists, compare modified_at and keep newer
                    if name in models_dict:
                        existing_modified = models_dict[name].get("modified_at", "")
                        new_modified = model.get("modified_at", "")
                        # Simple string comparison works for RFC3339 timestamps
                        if new_modified > existing_modified:
                            models_dict[name] = model
                    else:
                        models_dict[name] = model

    # Sort by name for consistent ordering
    models_list = sorted(models_dict.values(), key=lambda m: m.get("name", ""))

    return JsonResponse({"models": models_list}, safe=False)


@extend_schema(
    tags=['Proxy'],
    responses={200: {'type': 'object'}},
    description='List running models loaded into memory on all nodes (aggregated).'
)
@api_view(['GET'])
@permission_classes([AllowAny])
def proxy_ps(request):
    mgr = _get_manager()
    if mgr is None:
        return JsonResponse({"error": "no proxy nodes configured"}, status=503)

    from django.core.cache import cache
    active = cache.get(mgr.ACTIVE_POOL_KEY, [])
    standby = cache.get(mgr.STANDBY_POOL_KEY, [])
    all_nodes = list({*active, *standby})

    if not all_nodes:
        return JsonResponse({"error": "no nodes available"}, status=503)

    import httpx
    # fetch runtime ps from nodes
    async def fetch_node_ps(addr):
        url = addr.rstrip('/') + '/api/ps'
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get('models', []) if isinstance(data, dict) else []
        except Exception as e:
            logger.debug('failed to fetch /api/ps from %s: %s', addr, e)
        return []

    async def fetch_all():
        tasks = [fetch_node_ps(addr) for addr in all_nodes]
        return await asyncio.gather(*tasks, return_exceptions=True)

    results = async_to_sync(fetch_all)()

    # Build map of runtime loaded models -> set of node addrs
    running_map: dict[str, list[str]] = {}
    for idx, res in enumerate(results):
        src_addr = all_nodes[idx]
        if isinstance(res, list):
            for m in res:
                if not isinstance(m, dict):
                    continue
                key = m.get('model') or m.get('name')
                if not key:
                    continue
                running_map.setdefault(key, []).append(src_addr)

    # Read DB node.available_models for all nodes in DB
    try:
        from proxy.models import node as NodeModel
        db_nodes = NodeModel.objects.filter(active=True)
    except Exception:
        db_nodes = []

    # Map model -> list of db nodes that report it
    db_map: dict[str, list[str]] = {}
    addr_map: dict[str, str] = {}
    for n in db_nodes:
        addr = (n.address or '').strip()
        if n.port and ':' not in addr.split('/')[-1]:
            addr = f"{addr}:{n.port}"
        if addr and not addr.startswith('http'):
            addr = 'http://' + addr
        addr_map[n.id] = addr
        try:
            for model_name in (n.available_models or []):
                db_map.setdefault(model_name, []).append(addr)
        except Exception:
            pass

    # Aggregate final model list (union of DB-reported models)
    final_models = []
    seen = set()
    for model_name, db_nodes_list in db_map.items():
        if model_name in seen:
            continue
        seen.add(model_name)
        running_on = running_map.get(model_name, [])
        final_models.append({
            'model': model_name,
            'db_nodes': db_nodes_list,
            'running_on': running_on,
        })

    # Also include any runtime-only models (not in DB.available_models)
    for model_name, run_nodes in running_map.items():
        if model_name in seen:
            continue
        seen.add(model_name)
        final_models.append({
            'model': model_name,
            'db_nodes': [],
            'running_on': run_nodes,
        })

    final_models.sort(key=lambda x: x.get('model') or '')
    return JsonResponse({'models': final_models}, safe=False)