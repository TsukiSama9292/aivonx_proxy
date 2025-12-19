from rest_framework import viewsets
from .models import node
from .serializers import (
    NodeSerializer
)

class NodeViewSet(viewsets.ModelViewSet):
    queryset = node.objects.all()
    serializer_class = NodeSerializer