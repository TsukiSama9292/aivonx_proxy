from django.http import JsonResponse, HttpResponse, StreamingHttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.apps import apps
import logging
logger = logging.getLogger('proxy')
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from rest_framework.response import Response
from rest_framework import status
from .serializers import ProxyConfigSerializer
from .models import ProxyConfig
from rest_framework.permissions import IsAuthenticated
import httpx
from django.core.cache import cache

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

def _get_active_count(mgr, addr: str) -> int:
    """Helper to get active request count, handling bytes from Redis."""
    key = mgr._active_count_key(addr)
    # Try to read directly from Redis first for most up-to-date value
    try:
        from django_redis import get_redis_connection
        conn = get_redis_connection('default')
        val = conn.get(key)
        if val is not None:
            if isinstance(val, bytes):
                return int(val.decode())
            return int(val)
        return 0
    except Exception:
        # Fallback to cache
        val = cache.get(key, 0)
        if isinstance(val, bytes):
            try:
                return int(val.decode())
            except Exception:
                return 0
        elif isinstance(val, int):
            return val
        else:
            try:
                return int(val)
            except Exception:
                return 0

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
        active_counts = {a: _get_active_count(mgr, a) for a in list({*active, *standby})}
        models = {a: cache.get(mgr.MODELS_KEY_PREFIX + a, []) for a in list({*active, *standby})}
        # If cache is empty in this process (LocMemCache is process-local), refresh from DB
        if not active and getattr(mgr, 'nodes', None):
            try:
                mgr.refresh_from_db()
                active = cache.get(mgr.ACTIVE_POOL_KEY, [])
                standby = cache.get(mgr.STANDBY_POOL_KEY, [])
                node_map = cache.get(mgr.NODE_ID_MAP_KEY, {})
                latencies = {a: cache.get(mgr.LATENCY_KEY_PREFIX + a) for a in list({*active, *standby})}
                active_counts = {a: _get_active_count(mgr, a) for a in list({*active, *standby})}
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
            except Exception as e:
                logger.debug("health: failed to read cfg_nodes from manager: %s", e)
    except Exception:
        active = []

    if active:
        return HttpResponse("Ollama is running", status=200)
    return JsonResponse({"error": "no healthy nodes available"}, status=404)


@extend_schema(
	tags=['Proxy'],
	request=ProxyConfigSerializer,
	responses={200: ProxyConfigSerializer, 400: {'type': 'object'}}
)
@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def proxy_config(request):
	"""Get or update the global `ProxyConfig`.

	GET returns the latest config (creates default if none exists).
	PUT/PATCH updates fields on the existing config (PATCH = partial).
	"""
	# Get or create a single ProxyConfig row
	cfg = ProxyConfig.objects.order_by('-updated_at').first()
	if cfg is None:
		cfg = ProxyConfig.objects.create()

	if request.method == 'GET':
		serializer = ProxyConfigSerializer(cfg)
		return Response(serializer.data)

	partial = request.method == 'PATCH'
	serializer = ProxyConfigSerializer(cfg, data=request.data, partial=partial)
	if serializer.is_valid():
		serializer.save()
		return Response(serializer.data)
	return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
	tags=['Proxy'],
	responses={
		200: {
			'type': 'object',
			'properties': {
				'nodes': {
					'type': 'array',
					'items': {
						'type': 'object',
						'properties': {
							'id': {'type': 'integer', 'description': 'Node ID'},
							'name': {'type': 'string', 'description': 'Node name'},
							'address': {'type': 'string', 'description': 'Node address'},
							'active_requests': {'type': 'integer', 'description': 'Number of active requests'},
							'status': {'type': 'string', 'enum': ['active', 'standby'], 'description': 'Node status'},
							'latency': {'type': 'number', 'description': 'Last measured latency in seconds'},
							'models': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Available models'},
						}
					}
				},
				'total_active_requests': {'type': 'integer', 'description': 'Total active requests across all nodes'}
			}
		},
		404: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
		503: {'type': 'object', 'properties': {'error': {'type': 'string'}}}
	},
	parameters=[
		OpenApiParameter(
			name='node_id',
			location=OpenApiParameter.QUERY,
			description='Filter by specific node ID (optional)',
			required=False,
			type=OpenApiTypes.INT,
		),
	],
	description='Get active request counts for all nodes or a specific node. Returns detailed information about each node including active requests, status, latency, and available models.'
)
@api_view(['GET'])
@permission_classes([AllowAny])
def active_requests(request):
	"""Get active request counts for all nodes or a specific node by ID."""
	mgr = _get_manager()
	from django.core.cache import cache
	from .models import node as NodeModel

	if mgr is None:
		return JsonResponse({"error": "no proxy manager"}, status=503)

	try:
		# Get filter parameter
		filter_node_id = request.GET.get('node_id')
		if filter_node_id:
			try:
				filter_node_id = int(filter_node_id)
			except ValueError:
				return JsonResponse({
					"error": f"invalid node_id: must be an integer"
				}, status=400)
		
		# Get all nodes from pools
		# Get all nodes from pools
		active_pool = cache.get(mgr.ACTIVE_POOL_KEY, [])
		standby_pool = cache.get(mgr.STANDBY_POOL_KEY, [])
		node_id_map = cache.get(mgr.NODE_ID_MAP_KEY, {})
		# defensive: ensure node_id_map is a dict-like structure
		if not isinstance(node_id_map, dict):
			node_id_map = {}
		# Create reverse mapping: address -> id (guard for unexpected shapes)
		try:
			address_to_id = {addr: int(node_id) for node_id, addr in node_id_map.items()}
		except Exception:
			address_to_id = {}
		
		# Get node details from database
		if filter_node_id:
			# Prefer looking up the node by PK even if the `active` flag in DB
			# might be stale; allow querying any node that exists
			node_obj = NodeModel.objects.filter(pk=filter_node_id).first()
			if not node_obj:
				return JsonResponse({"error": f"node not found: {filter_node_id}"}, status=404)
			# restrict queryset to the single node we found
			nodes_qs = NodeModel.objects.filter(pk=filter_node_id)
		else:
			nodes_qs = NodeModel.objects.filter(active=True)
		
		# Collect data for each node
		nodes_data = []
		total_active = 0
		
		for node in nodes_qs:
			# Construct address to match cache keys
			addr = (node.address or "").strip()
			if node.port and ":" not in addr.split("/")[-1]:
				addr = f"{addr}:{node.port}"
			if addr and not addr.startswith("http"):
				addr = "http://" + addr
			
			# Determine status even if not in pools (might be inactive)
			if addr in active_pool:
				status_str = 'active'
			elif addr in standby_pool:
				status_str = 'standby'
			else:
				status_str = 'inactive'
			
			# Get active count using helper function
			active_count = _get_active_count(mgr, addr)
			latency = cache.get(mgr.LATENCY_KEY_PREFIX + addr)
			models = cache.get(mgr.MODELS_KEY_PREFIX + addr, [])
			# fallback to DB-stored available_models when cache is empty
			if not models:
				try:
					if getattr(node, 'available_models', None):
						models = node.available_models
				except Exception:
					models = []
			
			nodes_data.append({
				'id': node.id,
				'name': node.name,
				'address': addr,
				'active_requests': active_count,
				'status': status_str,
				'latency': latency,
				'models': models
			})
			total_active += active_count
		
		# Sort by active requests (descending)
		nodes_data.sort(key=lambda x: x['active_requests'], reverse=True)
		
		return JsonResponse({
			'nodes': nodes_data,
			'total_active_requests': total_active
		})
		
	except Exception as e:
		logger.exception("failed to get active requests")
		return JsonResponse({
			"error": "failed to get active requests",
			"details": str(e)
		}, status=500)


@extend_schema(
	tags=['Proxy'],
	request={
		'application/json': {
			'type': 'object',
			'properties': {
				'model': {'type': 'string', 'description': 'Name of the model to pull', 'required': True},
				'node_id': {'type': 'integer', 'description': 'Specific node ID to pull on (optional). If not specified, pulls on all active nodes.'},
				'insecure': {'type': 'boolean', 'description': 'Allow insecure connections (optional)'},
				'stream': {'type': 'boolean', 'description': 'Stream response (optional, default false)'},
			},
			'required': ['model']
		}
	},
	responses={
		200: {
			'type': 'object',
			'properties': {
				'results': {
					'type': 'array',
					'items': {
						'type': 'object',
						'properties': {
							'node_id': {'type': 'integer'},
							'node_name': {'type': 'string'},
							'node_address': {'type': 'string'},
							'status': {'type': 'string'},
							'message': {'type': 'string'},
						}
					}
				}
			}
		},
		400: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
		404: {'type': 'object', 'properties': {'error': {'type': 'string'}}},
		503: {'type': 'object', 'properties': {'error': {'type': 'string'}}}
	},
	description='Pull a model to specified node(s). If node_id is provided, pulls only to that node. Otherwise, pulls to all active nodes.'
)
@api_view(['POST'])
@permission_classes([AllowAny])
def pull_model(request):
	"""Pull a model to one or all nodes."""
	mgr = _get_manager()
	from .models import node as NodeModel
	import httpx
	from concurrent.futures import ThreadPoolExecutor, as_completed

	if mgr is None:
		return JsonResponse({"error": "no proxy manager"}, status=503)

	try:
		# Parse request body
		body = request.data if hasattr(request, 'data') else {}
		model_name = body.get('model')
		node_id = body.get('node_id')
		insecure = body.get('insecure', False)
		stream = body.get('stream', False)

		if not model_name:
			return JsonResponse({"error": "model name is required"}, status=400)

		# Get target nodes
		if node_id:
			try:
				node_id = int(node_id)
				nodes_qs = NodeModel.objects.filter(id=node_id, active=True)
				if not nodes_qs.exists():
					return JsonResponse({"error": f"node not found: {node_id}"}, status=404)
			except ValueError:
				return JsonResponse({"error": "invalid node_id: must be an integer"}, status=400)
		else:
			nodes_qs = NodeModel.objects.filter(active=True)

		if not nodes_qs.exists():
			return JsonResponse({"error": "no active nodes available"}, status=404)

		# Function to pull model to a single node
		def pull_to_node(node):
			addr = (node.address or "").strip()
			if node.port and ":" not in addr.split("/")[-1]:
				addr = f"{addr}:{node.port}"
			if addr and not addr.startswith("http"):
				addr = "http://" + addr

			url = addr.rstrip("/") + "/api/pull"
			payload = {"model": model_name, "stream": stream}
			if insecure:
				payload["insecure"] = True

			try:
				with httpx.Client(timeout=300.0) as client:
					response = client.post(url, json=payload)
				
				if response.status_code == 200:
					if stream:
						return {
							"node_id": node.id,
							"node_name": node.name,
							"node_address": addr,
							"status": "success",
							"message": "Model pull initiated"
						}
					else:
						result = response.json()
						return {
							"node_id": node.id,
							"node_name": node.name,
							"node_address": addr,
							"status": result.get("status", "success"),
							"message": "Model pulled successfully"
						}
				else:
					return {
						"node_id": node.id,
						"node_name": node.name,
						"node_address": addr,
						"status": "error",
						"message": f"HTTP {response.status_code}: {response.text[:200]}"
					}
			except Exception as e:
				return {
					"node_id": node.id,
					"node_name": node.name,
					"node_address": addr,
					"status": "error",
					"message": str(e)
				}

		# Execute pulls in parallel using ThreadPoolExecutor
		results = []
		with ThreadPoolExecutor(max_workers=5) as executor:
			future_to_node = {executor.submit(pull_to_node, node): node for node in nodes_qs}
			for future in as_completed(future_to_node):
				try:
					result = future.result()
					results.append(result)
				except Exception as e:
					node = future_to_node[future]
					results.append({
						"node_id": node.id,
						"node_name": node.name,
						"node_address": "unknown",
						"status": "error",
						"message": str(e)
					})

		return JsonResponse({
			"results": results,
			"model": model_name,
			"total_nodes": len(results)
		})

	except Exception as e:
		logger.exception("failed to pull model")
		return JsonResponse({
			"error": "failed to pull model",
			"details": str(e)
		}, status=500)