from drf_spectacular.utils import extend_schema
from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import node
from .serializers import NodeSerializer
import httpx
import logging
logger = logging.getLogger('proxy')

@extend_schema(tags=['Node'])
class NodeViewSet(viewsets.ModelViewSet):
    queryset = node.objects.all()
    serializer_class = NodeSerializer
    
    def get_serializer(self, *args, **kwargs):
        # Support `?fields=field1,field2` to return only those fields
        request = getattr(self, 'request', None)
        if request is not None:
            fields_param = request.query_params.get('fields')
            if fields_param:
                fields = [f.strip() for f in fields_param.split(',') if f.strip()]
                if fields:
                    kwargs['fields'] = fields
        return super().get_serializer(*args, **kwargs)

    def create(self, request, *args, **kwargs):
        """Override create to perform an upstream health check before saving.

        The incoming payload provides `address` and `port`. We construct the
        candidate base URL, probe its `/api/health` endpoint, set the
        `active` flag based on the probe, save the node, and then trigger
        the global manager to refresh its DB-backed node list so the UI
        will reflect the new node state.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Build an absolute address similar to HAProxyManager.refresh_from_db
        addr = (serializer.validated_data.get('address') or '').strip()
        port = serializer.validated_data.get('port')
        if port and ":" not in addr.split('/')[-1]:
            addr = f"{addr}:{port}"
        if addr and not addr.startswith('http'):
            addr = 'http://' + addr

        health_url = addr.rstrip('/') + '/api/health'
        healthy = False
        try:
            resp = httpx.get(health_url, timeout=3.0)
            healthy = 0 <= getattr(resp, 'status_code', 500) < 500
        except Exception:
            healthy = False

        # Save node with active set according to health check
        instance = serializer.save(active=healthy)

        # Trigger manager refresh so caches/pools include the new node
        try:
            from .utils.proxy_manager import get_global_manager

            mgr = get_global_manager()
            if mgr is not None:
                try:
                    mgr.refresh_from_db()
                except Exception as e:
                    logger.debug("NodeViewSet.create: refresh_from_db failed: %s", e)
        except Exception:
            logger.debug("NodeViewSet.create: failed to trigger manager refresh")

        out_ser = NodeSerializer(instance, context={'request': request})
        headers = self.get_success_headers(out_ser.data)
        return Response(out_ser.data, status=status.HTTP_201_CREATED, headers=headers)

    def _probe_health(self, addr: str) -> bool:
        """Synchronous health probe used by create/update flows.

        Returns True if upstream `/api/health` returns non-5xx.
        """
        try:
            health_url = addr.rstrip('/') + '/api/health'
            resp = httpx.get(health_url, timeout=3.0)
            return 0 <= getattr(resp, 'status_code', 500) < 500
        except Exception:
            return False

    def _perform_update(self, request, partial: bool = False):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        # Determine if address/port changed
        orig_addr = (getattr(instance, 'address', '') or '').strip()
        orig_port = getattr(instance, 'port', None)
        new_addr = (serializer.validated_data.get('address') or orig_addr).strip()
        new_port = serializer.validated_data.get('port', orig_port)
        if new_port and ":" not in new_addr.split('/')[-1]:
            candidate = f"{new_addr}:{new_port}"
        else:
            candidate = new_addr
        if candidate and not candidate.startswith('http'):
            candidate = 'http://' + candidate

        # If client explicitly provided `active` in payload, respect it; otherwise probe when address/port changed
        if 'active' in serializer.validated_data:
            active = bool(serializer.validated_data.get('active'))
        else:
            active = getattr(instance, 'active', False)
            # Probe only if address or port changed
            if (new_addr != orig_addr) or (new_port != orig_port):
                try:
                    active = self._probe_health(candidate)
                except Exception:
                    active = False

        # Save with computed active
        updated = serializer.save(active=active)

        # refresh manager caches
        try:
            from .utils.proxy_manager import get_global_manager

            mgr = get_global_manager()
            if mgr is not None:
                try:
                    mgr.refresh_from_db()
                except Exception as e:
                    logger.debug("NodeViewSet._perform_update: refresh_from_db failed: %s", e)
        except Exception:
            logger.debug("NodeViewSet._perform_update: failed to trigger manager refresh")

        out_ser = NodeSerializer(updated, context={'request': request})
        return Response(out_ser.data)

    def update(self, request, *args, **kwargs):
        return self._perform_update(request, partial=False)

    def partial_update(self, request, *args, **kwargs):
        return self._perform_update(request, partial=True)

# NodeGroup API removed