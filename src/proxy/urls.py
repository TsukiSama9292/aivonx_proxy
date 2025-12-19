from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewsets import (
    NodeViewSet,
    NodeGroupViewSet
)
from .views import proxy_request

router = DefaultRouter()
router.register(r'nodes', NodeViewSet)
router.register(r'node-groups', NodeGroupViewSet)

# Keep CRUD router at the include root so existing clients continue to work
# e.g. /api/proxy/nodes/ remains valid. Expose proxy call at /api/proxy/call/
urlpatterns = [
    path('', include(router.urls)),
    path('call/', proxy_request, name='proxy_request'),
]