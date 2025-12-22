from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewsets import (
    NodeViewSet,
)
from .views import (
    health,
    state,
)
from .views_proxy import (
    proxy_generate,
    proxy_chat,
    proxy_tags,
    proxy_embed,
    proxy_embeddings,
)
from .views import proxy_config

router = DefaultRouter(trailing_slash='')
router.register(r'nodes', NodeViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('generate', proxy_generate, name='proxy_generate'),
    path('chat', proxy_chat, name='proxy_chat'),
    path('config', proxy_config, name='proxy_config'),
    path('tags', proxy_tags, name='proxy_tags'),
    path('state', state, name='proxy_state'),
    path('embed', proxy_embed, name='proxy_embed'),
    path('embeddings', proxy_embeddings, name='proxy_embeddings'),
]