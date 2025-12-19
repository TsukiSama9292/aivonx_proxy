from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewsets import NodeViewSet

router = DefaultRouter()
router.register(r'nodes', NodeViewSet)

urlpatterns = [
    path('', include(router.urls)),
]