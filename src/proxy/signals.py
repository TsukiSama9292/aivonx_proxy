from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import node as NodeModel
import logging
logger = logging.getLogger('proxy')

from .utils.proxy_manager import get_global_manager
from django_redis import get_redis_connection
import time


@receiver(post_save, sender=NodeModel)
def node_saved(sender, instance, **kwargs):
    """Refresh HA manager when a node is created/updated."""
    try:
        mgr = get_global_manager()
        if mgr is None:
            logger.debug("signals: no global manager available to refresh on node save")
            return
        try:
            # First, notify the leader process to pick up an immediate refresh.
            try:
                conn = get_redis_connection('default')
                conn.set('ha_refresh_request', str(time.time()), ex=30)
            except Exception:
                logger.debug("signals: failed to write ha_refresh_request to redis")

            # If this process happens to be the leader, perform the heavier
            # refresh work locally to reduce latency (models + health).
            try:
                if getattr(mgr, '_is_leader', False):
                    try:
                        # synchronous calls are ok from signal handlers
                        mgr.refresh_from_db()
                    except Exception:
                        logger.debug("signals: local refresh_from_db failed in leader")
                    try:
                        import asyncio
                        asyncio.run(mgr.refresh_models_all())
                    except Exception:
                        logger.debug("signals: local refresh_models_all failed in leader")
                    try:
                        import asyncio
                        asyncio.run(mgr.health_check_all())
                    except Exception:
                        logger.debug("signals: local health_check_all failed in leader")
            except Exception:
                # best-effort; don't block signal handling
                logger.debug("signals: error while attempting leader-local refresh")
            logger.info("signals: notified leader to refresh after node save (id=%s)", getattr(instance, 'id', None))
        except Exception as e:
            logger.exception("signals: failed to refresh HA manager after node save: %s", e)
    except Exception:
        logger.debug("signals: get_global_manager failed during node save handler")


@receiver(post_delete, sender=NodeModel)
def node_deleted(sender, instance, **kwargs):
    """Refresh HA manager when a node is deleted."""
    try:
        mgr = get_global_manager()
        if mgr is None:
            logger.debug("signals: no global manager available to refresh on node delete")
            return
        try:
            # Notify leader first
            try:
                conn = get_redis_connection('default')
                conn.set('ha_refresh_request', str(time.time()), ex=30)
            except Exception:
                logger.debug("signals: failed to write ha_refresh_request to redis")

            # If leader, perform refresh locally for immediate consistency
            try:
                if getattr(mgr, '_is_leader', False):
                    try:
                        mgr.refresh_from_db()
                    except Exception:
                        logger.debug("signals: local refresh_from_db failed in leader")
                    try:
                        import asyncio
                        asyncio.run(mgr.refresh_models_all())
                    except Exception:
                        logger.debug("signals: local refresh_models_all failed in leader")
                    try:
                        import asyncio
                        asyncio.run(mgr.health_check_all())
                    except Exception:
                        logger.debug("signals: local health_check_all failed in leader")
            except Exception:
                logger.debug("signals: error while attempting leader-local refresh")
            logger.info("signals: notified leader to refresh after node delete (id=%s)", getattr(instance, 'id', None))
        except Exception as e:
            logger.exception("signals: failed to refresh HA manager after node delete: %s", e)
    except Exception:
        logger.debug("signals: get_global_manager failed during node delete handler")
