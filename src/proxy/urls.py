from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewsets import (
    NodeViewSet,
    NodeGroupViewSet
)

router = DefaultRouter()
router.register(r'nodes', NodeViewSet)
router.register(r'node-groups', NodeGroupViewSet)

urlpatterns = [
    path('', include(router.urls)),
]