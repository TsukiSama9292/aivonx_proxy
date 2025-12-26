# migrations/000x_create_root_user.py
from django.db import migrations
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from django.db import IntegrityError
from dotenv import load_dotenv
import logging
from django.db.utils import OperationalError
import os

def create_root_user(apps, schema_editor):
    load_dotenv()
    logger = logging.getLogger('account')
    try:
        # Prefer the historical model from apps to avoid current-model/runtime differences
        try:
            User = apps.get_model('auth', 'User')
        except Exception:
            # fallback to runtime user model
            User = get_user_model()
    except Exception as e:
        logger.exception("create_root_user: failed to get user model: %s", e)
        return

    try:
        if not User.objects.filter(username="root").exists():
            root_password = os.getenv("ROOT_PASSWORD", "changeme")
            now = timezone.now()
            # Build safe user data and set required date fields to avoid NOT NULL constraint
            user_data = {
                'username': 'root',
                'password': make_password(root_password),
                'is_superuser': True,
                'is_staff': True,
                'is_active': True,
                'date_joined': now,
            }
            # If the model has a last_login field, set it to now to avoid NOT NULL issues
            try:
                field_names = [f.name for f in User._meta.get_fields()]
                if 'last_login' in field_names:
                    user_data['last_login'] = now
            except Exception as e:
                logger.debug("create_root_user: introspection for last_login failed: %s", e)

            # Create directly instead of calling create_superuser to avoid custom manager side-effects
            try:
                User.objects.create(**user_data)
                logger.info("create_root_user: created 'root' user")
            except IntegrityError as ie:
                logger.exception("create_root_user: integrity error creating root user: %s", ie)
            except TypeError:
                # Fallback to create_superuser if create() signature differs
                try:
                    User.objects.create_superuser(username="root", password=root_password, email=os.getenv("ROOT_EMAIL", ""))
                    logger.info("create_root_user: created 'root' superuser (fallback)")
                except Exception as e:
                    logger.exception("create_root_user: fallback create_superuser failed: %s", e)
    except OperationalError as oe:
        # Database might not be ready yet; log and continue so operator can retry/migrate
        logger.warning("create_root_user: DB not ready, skipping root creation: %s", oe)
    except Exception as e:
        logger.exception("create_root_user: unexpected error while creating root user: %s", e)

class Migration(migrations.Migration):
    dependencies = [
        ("account", "0002_delete_user"),
        ("auth", "0005_alter_user_last_login_null"),
    ]

    operations = [
        migrations.RunPython(create_root_user),
    ]
