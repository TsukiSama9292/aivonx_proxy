from django.db import models

class node(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=200)
    port = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)