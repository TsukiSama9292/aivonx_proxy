import os
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

        def create_root_user(sender, **kwargs):
            try:
                User = get_user_model()
                if not User.objects.filter(username="root").exists():
                    root_password = os.getenv("ROOT_PASSWORD", "changeme")
                    User.objects.create_user(username="root", password=root_password)
            except OperationalError:
                # Database might not be ready yet
                pass

        post_migrate.connect(create_root_user, dispatch_uid="account.create_root_user")
