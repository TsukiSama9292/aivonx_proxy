from django.urls import path
from .views import LogsAPIView

urlpatterns = [
    path('', LogsAPIView.as_view(), name='logs-list'),
]
