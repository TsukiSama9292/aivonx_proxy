from django.apps import AppConfig


class AccountConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'account'
    
    def ready(self):
        from django.db.utils import OperationalError
        from .models import AccountTable

        try:
            if not AccountTable.objects.filter(username="root").exists():
                root = AccountTable(username="root")
                root.set_password("changeme")  # 用你的 set_password
                root.save()
                print("AccountTable root user created.")
        except OperationalError:
            # 資料庫尚未建立，例如第一次 migrate
            pass