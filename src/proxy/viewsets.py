from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from .models import node
from .serializers import NodeSerializer

@extend_schema(tags=['Node'])
class NodeViewSet(viewsets.ModelViewSet):
    queryset = node.objects.all()
    serializer_class = NodeSerializer
    
    def get_serializer(self, *args, **kwargs):
        # Support `?fields=field1,field2` to return only those fields
        request = getattr(self, 'request', None)
        if request is not None:
            fields_param = request.query_params.get('fields')
            if fields_param:
                fields = [f.strip() for f in fields_param.split(',') if f.strip()]
                if fields:
                    kwargs['fields'] = fields
        return super().get_serializer(*args, **kwargs)

# NodeGroup API removed