from django.urls import re_path
from .views import LoginView

urlpatterns = [
    # Accept both /login and /login/ to be tolerant of client URLs
    re_path("login", LoginView.as_view(), name="root-login"),
]
