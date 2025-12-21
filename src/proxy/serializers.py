from rest_framework import serializers
from .models import node


class DynamicFieldsModelSerializer(serializers.ModelSerializer):
    """A ModelSerializer that takes an additional `fields` argument that
    controls which fields should be displayed.
    Usage: ?fields=id,name,address
    """
    def __init__(self, *args, **kwargs):
        fields = kwargs.pop('fields', None)
        super().__init__(*args, **kwargs)

        if fields is not None:
            allowed = set(fields)
            existing = set(self.fields.keys())
            for field_name in existing - allowed:
                self.fields.pop(field_name, None)


class NodeSerializer(DynamicFieldsModelSerializer):
    class Meta:
        model = node
        fields = [
            'id',
            'name',
            'address',
            'port',
            'active',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


from .models import ProxyConfig


class ProxyConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProxyConfig
        fields = ['id', 'strategy', 'weight', 'updated_at']
        read_only_fields = ['id', 'updated_at']


# Node groups were removed — no serializer needed