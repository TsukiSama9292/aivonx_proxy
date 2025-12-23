from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewsets import (
    NodeViewSet,
)
from .views import (
    state,
    active_requests,
    pull_model,
)

from .views import proxy_config

router = DefaultRouter(trailing_slash='')
router.register(r'nodes', NodeViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('state', state, name='proxy_state'),
    path('active-requests', active_requests, name='active_requests'),
    path('pull', pull_model, name='pull_model'),
    path('config', proxy_config, name='proxy_config'),
]