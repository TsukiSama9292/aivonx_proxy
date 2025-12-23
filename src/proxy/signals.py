from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import node as NodeModel
import logging
logger = logging.getLogger('proxy')

from .utils.proxy_manager import get_global_manager


@receiver(post_save, sender=NodeModel)
def node_saved(sender, instance, **kwargs):
    """Refresh HA manager when a node is created/updated."""
    try:
        mgr = get_global_manager()
        if mgr is None:
            logger.debug("signals: no global manager available to refresh on node save")
            return
        try:
            mgr.refresh_from_db()
            logger.info("signals: refreshed HA manager from DB after node save (id=%s)", getattr(instance, 'id', None))
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
            mgr.refresh_from_db()
            logger.info("signals: refreshed HA manager from DB after node delete (id=%s)", getattr(instance, 'id', None))
        except Exception as e:
            logger.exception("signals: failed to refresh HA manager after node delete: %s", e)
    except Exception:
        logger.debug("signals: get_global_manager failed during node delete handler")
