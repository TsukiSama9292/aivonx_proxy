import os
import logging
import asyncio
from asgiref.sync import sync_to_async
from django.apps import AppConfig
from django.db.utils import OperationalError
from dotenv import load_dotenv


class AccountConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'account'
    
    def ready(self):
        # Load environment variables from .env file
        load_dotenv()

        # Create root user after migrations
        from django.db.models.signals import post_migrate
        from django.contrib.auth import get_user_model

        logger = logging.getLogger('account')

        def create_root_user(sender, **kwargs):
            try:
                User = get_user_model()
            except Exception as e:
                logger.exception("create_root_user: failed to import user model: %s", e)
                return

            try:
                if not User.objects.filter(username="root").exists():
                    root_password = os.getenv("ROOT_PASSWORD", "changeme")
                    # create_superuser to ensure admin privileges
                    try:
                        User.objects.create_superuser(username="root", password=root_password, email=os.getenv("ROOT_EMAIL", ""))
                        logger.info("create_root_user: created 'root' superuser")
                    except TypeError:
                        # Some custom user models may not accept 'email' argument
                        User.objects.create_superuser(username="root", password=root_password)
                        logger.info("create_root_user: created 'root' superuser (no email)")
            except OperationalError as oe:
                # Database might not be ready yet; log and continue so operator can retry/migrate
                logger.warning("create_root_user: DB not ready, skipping root creation: %s", oe)
            except Exception as e:
                logger.exception("create_root_user: unexpected error while creating root user: %s", e)

        post_migrate.connect(create_root_user, dispatch_uid="account.create_root_user")

        # Try to create root immediately if DB is ready (covers processes where migrations
        # have already run and post_migrate won't be called again). If we're running
        # inside an async event loop, schedule the sync DB call via sync_to_async so
        # we don't trigger SynchronousOnlyOperation.
        def _db_has_table(table_name: str) -> bool:
            try:
                from django.db import connection
                tables = connection.introspection.table_names()
                return table_name in tables
            except Exception:
                # DB not ready or introspection failed
                return False

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop -> safe to call synchronously, but only if auth_user table exists
            try:
                if _db_has_table('auth_user'):
                    create_root_user(None)
                else:
                    logger.debug("create_root_user: auth_user table missing on startup, will rely on post_migrate")
            except OperationalError:
                logger.debug("create_root_user: DB not ready on startup, will rely on post_migrate")
            except Exception as e:
                logger.exception("create_root_user: unexpected error on startup attempt: %s", e)
        else:
            # We're in an async loop; schedule a safe wrapper to run in a thread
            async def _safe_create_wrapper():
                try:
                    if _db_has_table('auth_user'):
                        await sync_to_async(create_root_user)(None)
                    else:
                        logger.debug("create_root_user: auth_user table missing (async), will rely on post_migrate")
                except Exception:
                    logger.exception("create_root_user: async startup attempt failed")

            try:
                loop.create_task(_safe_create_wrapper())
            except Exception as e:
                logger.exception("create_root_user: failed to schedule async startup attempt: %s", e)
