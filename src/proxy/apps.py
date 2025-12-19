from django.apps import AppConfig
from loguru import logger


class ProxyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'proxy'
    ha_manager = None

    def ready(self):
        # Do not access the DB during app ready. HA manager initialization
        # is performed during ASGI lifespan startup in `aivonx.asgi.application`.
        logger.debug("proxy app ready() called; HA initialization deferred to ASGI lifespan")
