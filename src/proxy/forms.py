from django import forms
from .models import node, ProxyConfig


class NodeForm(forms.ModelForm):
    class Meta:
        model = node
        fields = ['name', 'address', 'port']


class ProxyConfigForm(forms.ModelForm):
    class Meta:
        model = ProxyConfig
        fields = ['strategy']
