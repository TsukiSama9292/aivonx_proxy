from django.apps import AppConfig
import logging
logger = logging.getLogger('proxy')


class ProxyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'proxy'
    proxy_manager = None

    def ready(self):
        # Do not access the DB during app ready. HA manager initialization
        # is performed during ASGI lifespan startup in `aivonx.asgi.application`.
        logger.debug("proxy app ready() called; HA initialization deferred to ASGI lifespan")
        # Import signal handlers to refresh HA manager when node records change
        try:
            # signals will register post_save/post_delete handlers for `node`
            from . import signals  # noqa: F401
        except Exception:
            logger.debug("proxy.apps: failed to import signals module, node changes may not refresh manager")
