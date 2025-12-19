import os
from django.apps import AppConfig
from django.db.utils import OperationalError
from dotenv import load_dotenv

class AccountConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'account'
    
    def ready(self):
        # 先讀取 .env（不會存取資料庫）
        load_dotenv()

        # 延後建立 root 使用者到 migrations 完成後，以避免在應用啟動時存取 DB
        from django.db.models.signals import post_migrate
        from django.contrib.auth import get_user_model

        def create_root_user(sender, **kwargs):
            try:
                User = get_user_model()
                if not User.objects.filter(username="root").exists():
                    root_password = os.getenv("ROOT_PASSWORD", "changeme")
                    User.objects.create_user(username="root", password=root_password)
                    print("User root created.")
            except OperationalError:
                # 如果 DB 尚未準備好，忽略並在下一次 migrations 後再試
                pass

        post_migrate.connect(create_root_user, dispatch_uid="account.create_root_user")
