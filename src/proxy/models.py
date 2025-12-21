from django.db import models

class node(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=200)
    port = models.IntegerField()
    active = models.BooleanField(default=True)
    # list of model names available on this node (updated periodically)
    available_models = models.JSONField(blank=True, default=list)
    created_at = models.DateTimeField(auto_now_add=True)

class node_group(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    nodes = models.ManyToManyField(node, related_name="groups", blank=True)
    strategy = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ProxyConfig(models.Model):
    """Global config for proxy selection strategy.

    Keep a single row to control selection strategy and parameters.
    """
    STRATEGY_LEAST_ACTIVE = "least_active"
    STRATEGY_LOWEST_LATENCY = "lowest_latency"

    STRATEGY_CHOICES = [
        (STRATEGY_LEAST_ACTIVE, "Least active (default)"),
        (STRATEGY_LOWEST_LATENCY, "Lowest latency"),
    ]

    id = models.AutoField(primary_key=True)
    strategy = models.CharField(max_length=32, choices=STRATEGY_CHOICES, default=STRATEGY_LEAST_ACTIVE)
    # weight can be used for tuning least-active calculations in future
    weight = models.FloatField(default=1.0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Proxy Config"
        verbose_name_plural = "Proxy Configs"