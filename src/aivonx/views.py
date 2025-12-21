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

