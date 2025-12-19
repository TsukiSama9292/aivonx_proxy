from rest_framework import serializers
from .models import node

class NodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = node
        fields = [
            'id',
            'name',
            'address',
            'port',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']
