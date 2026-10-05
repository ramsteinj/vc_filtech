from django.urls import path

from .views import SystemStatusView

urlpatterns = [
    path("system/status", SystemStatusView.as_view(), name="system-status"),
]
