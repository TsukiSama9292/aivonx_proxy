from django.db import models

class node(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=200)
    port = models.IntegerField()
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

class node_group(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    nodes = models.ManyToManyField(node, related_name="groups", blank=True)
    strategy = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)