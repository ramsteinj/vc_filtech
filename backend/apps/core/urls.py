from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import JobViewSet, SystemStatusView

router = SimpleRouter(trailing_slash=False)
router.register("jobs", JobViewSet, basename="job")

urlpatterns = [
    path("system/status", SystemStatusView.as_view(), name="system-status"),
    *router.urls,
]
