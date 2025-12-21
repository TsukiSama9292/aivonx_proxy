from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewsets import (
    NodeViewSet,
    NodeGroupViewSet
)
from .handlers import (
    health,
    proxy_generate,
    proxy_chat,
    proxy_tags,
    proxy_embed,
    proxy_embeddings,
    state,
)

router = DefaultRouter(trailing_slash='')
router.register(r'nodes', NodeViewSet)
router.register(r'node-groups', NodeGroupViewSet)

urlpatterns = [
    # Health endpoint at the app root should be checked before the DRF router
    path('', health, name='proxy_health'),
    # Keep CRUD router at the include root but without trailing slashes
    # e.g. /api/proxy/nodes remains valid. Expose proxy call at /api/proxy/call
    path('', include(router.urls)),
    path('generate', proxy_generate, name='proxy_generate'),
    path('chat', proxy_chat, name='proxy_chat'),
    path('tags', proxy_tags, name='proxy_tags'),
    path('state', state, name='proxy_state'),
    # path('show', proxy_show, name='proxy_show'),  # Removed show route
    path('embed', proxy_embed, name='proxy_embed'),
    path('embeddings', proxy_embeddings, name='proxy_embeddings'),
]