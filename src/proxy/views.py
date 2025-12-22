from django.http import JsonResponse, HttpResponse, StreamingHttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.apps import apps
import logging
logger = logging.getLogger('proxy')
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework import status
from .serializers import ProxyConfigSerializer
from .models import ProxyConfig
from rest_framework.permissions import IsAuthenticated

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
		{
			'name': 'node_id',
			'in': 'query',
			'description': 'Filter by specific node ID (optional)',
			'required': False,
			'schema': {'type': 'integer'}
		}
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
		active_pool = cache.get(mgr.ACTIVE_POOL_KEY, [])
		standby_pool = cache.get(mgr.STANDBY_POOL_KEY, [])
		node_id_map = cache.get(mgr.NODE_ID_MAP_KEY, {})
		
		# Create reverse mapping: address -> id
		address_to_id = {addr: int(node_id) for node_id, addr in node_id_map.items()}
		
		# Get node details from database
		if filter_node_id:
			nodes_qs = NodeModel.objects.filter(id=filter_node_id, active=True)
			if not nodes_qs.exists():
				return JsonResponse({
					"error": f"node not found: {filter_node_id}"
				}, status=404)
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
			
			# Skip if node address not in pools (not managed)
			if addr not in active_pool and addr not in standby_pool:
				continue
			
			active_count = cache.get(mgr._active_count_key(addr), 0)
			latency = cache.get(mgr.LATENCY_KEY_PREFIX + addr)
			models = cache.get(mgr.MODELS_KEY_PREFIX + addr, [])
			status_str = 'active' if addr in active_pool else 'standby'
			
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