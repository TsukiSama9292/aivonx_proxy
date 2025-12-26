# migrations/000x_create_root_user.py
from django.db import migrations
from django.contrib.auth import get_user_model
from dotenv import load_dotenv
import logging
from django.db.utils import OperationalError
import os

def create_root_user(apps, schema_editor):
    load_dotenv()
    logger = logging.getLogger('account')
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

class Migration(migrations.Migration):
    dependencies = [
        ("account", "0002_delete_user"),
        ("auth", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_root_user),
    ]
