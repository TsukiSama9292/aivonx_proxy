from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .serializers import LoginSerializer

@extend_schema(
    tags=['Account'],
    request=LoginSerializer,
    responses={
        200: {
            'type': 'object',
            'properties': {
                'access': {'type': 'string'},
                'refresh': {'type': 'string'}
            }
        }
    }
)
class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get("username") or request.data.get("account")
        password = request.data.get("password") or request.data.get("passwd")

        if not username or not password:
            return Response({"detail": "Missing credentials."}, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(username=username, password=password)
        if user is None:
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(user)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh)
        })