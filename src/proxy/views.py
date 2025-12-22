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