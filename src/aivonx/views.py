from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions

@extend_schema(
    tags=['Health'],
    responses={
        200: {
            'type': 'object',
            'properties': {
                'status': {'type': 'string'}
            }
        }
    }
)
class HealthCheckView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({"status": "ok"})

@extend_schema(
    tags=['Version'],
    responses={
        200: {
            'type': 'object',
            'properties': {
                'version': {'type': 'string'}
            }
        }
    }
)
class VersionView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        # Try to get an installed distribution version first, fall back to
        # `aivonx.__version__` if present, otherwise return a sensible default.
        try:
            from importlib.metadata import version, PackageNotFoundError
            try:
                ver = version('aivonx')
            except PackageNotFoundError:
                import aivonx as _pkg
                ver = getattr(_pkg, '__version__', 'dev')
        except Exception:
            # importlib.metadata may not be available; fallback
            try:
                import aivonx as _pkg
                ver = getattr(_pkg, '__version__', 'dev')
            except Exception:
                ver = 'dev'
        return Response({"version": ver})